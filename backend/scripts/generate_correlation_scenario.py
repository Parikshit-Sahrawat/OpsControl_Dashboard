"""Generate a deterministic synthetic incident for validating OpsControl correlation.

This script never connects to external systems. It creates only synthetic data in
the configured OpsControl PostgreSQL database.

Scenario:
    ETL failure + high VM CPU + application error log + CRITICAL alert
"""

import argparse
from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.models import (
    AlertRule,
    Application,
    ExecutionStatus,
    ExecutionType,
    JobOrder,
    JobOrderHistory,
    JobStepExecution,
    LogEvent,
    LogSource,
    MetricDefinition,
    MetricSample,
    Organization,
    PentahoInstance,
    VM,
)
from app.services.correlation import correlate_execution
from app.worker.alert_engine import evaluate_metric_sample


def create_scenario(db, scenario_name: str):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    org = Organization(
        name=f"OpsControl Demo - {scenario_name}",
        code=f"DEMO_{scenario_name.upper().replace('-', '_')[:30]}",
    )
    db.add(org)
    db.flush()

    vm = VM(
        organization_id=org.id,
        hostname=f"DEMO-PRDAPP-{now.strftime('%H%M%S')}",
        environment="PROD",
        os="Windows Server 2022",
    )
    db.add(vm)
    db.flush()

    app = Application(
        vm_id=vm.id,
        name="Demo Tomcat",
        app_type="Tomcat",
    )
    db.add(app)

    pentaho = PentahoInstance(
        vm_id=vm.id,
        name="DEMO-PENTAHO",
        base_url="http://demo.invalid/pentaho",
        repository_name="DEMO",
    )
    db.add(pentaho)

    job = JobOrder(
        organization_id=org.id,
        vm_id=vm.id,
        pentaho_instance_id=pentaho.id,
        name="DEMO_Pricing_Daily",
        environment="PROD",
        expected_runtime_seconds=1200,
        sla_seconds=1800,
        schedule={"type": "daily", "time": "08:00"},
        expected_window_start="08:00",
        expected_window_end="08:15",
        no_run_grace_seconds=900,
    )
    db.add(job)
    db.flush()

    # Keep the failure close to "now" so the scenario is easy to inspect.
    failure_at = now
    start_at = failure_at - timedelta(minutes=5)

    history = JobOrderHistory(
        job_order_id=job.id,
        execution_type=ExecutionType.SCHEDULED,
        status=ExecutionStatus.FAILED,
        started_at=start_at,
        ended_at=failure_at,
        detected_at=failure_at,
        expected_runtime_seconds=1200,
        sla_seconds=1800,
        sla_status="ON TRACK",
        failed_step="Update Customer Database",
        source_error_code="DEMO_DB_TIMEOUT",
        source_error_message="Demo database connection timeout",
        source_exception="DemoConnectionTimeout: database did not respond within 30 seconds",
        source_log_location="demo://pentaho/DEMO_Pricing_Daily/execution.log",
        source_result="ERROR",
    )
    db.add(history)
    db.flush()

    db.add_all([
        JobStepExecution(
            history_id=history.id,
            name="Extract Customer Data",
            step_type="Table Input",
            status="SUCCESS",
            started_at=start_at,
            ended_at=start_at + timedelta(minutes=1),
            duration_seconds=60,
        ),
        JobStepExecution(
            history_id=history.id,
            name="Transform Pricing",
            step_type="Transformation",
            status="SUCCESS",
            started_at=start_at + timedelta(minutes=1),
            ended_at=start_at + timedelta(minutes=4),
            duration_seconds=180,
        ),
        JobStepExecution(
            history_id=history.id,
            name="Update Customer Database",
            step_type="Table Output",
            status="FAILED",
            started_at=start_at + timedelta(minutes=4),
            ended_at=failure_at,
            duration_seconds=60,
            error_code="DEMO_DB_TIMEOUT",
            error_message="Demo database connection timeout",
        ),
    ])

    cpu_metric = MetricDefinition(
        organization_id=org.id,
        name="VM CPU Utilization",
        description="Synthetic CPU utilization for correlation testing",
        resource_type="VM",
        resource_id=vm.id,
        metric_type="GAUGE",
        unit="percent",
        collection_interval_seconds=60,
        query_config={"demo": True, "scenario": scenario_name},
    )
    ram_metric = MetricDefinition(
        organization_id=org.id,
        name="VM Memory Utilization",
        description="Synthetic memory utilization for correlation testing",
        resource_type="VM",
        resource_id=vm.id,
        metric_type="GAUGE",
        unit="percent",
        collection_interval_seconds=60,
        query_config={"demo": True, "scenario": scenario_name},
    )
    db.add_all([cpu_metric, ram_metric])
    db.flush()

    # Three consecutive CPU breaches cause the CRITICAL alert to open.
    cpu_samples = []
    for offset, value in [(-180, 91.0), (-120, 96.0), (-60, 98.0)]:
        sample = MetricSample(
            organization_id=org.id,
            metric_definition_id=cpu_metric.id,
            observed_at=failure_at + timedelta(seconds=offset),
            value_numeric=value,
            unit="percent",
            dimensions={"hostname": vm.hostname, "demo": True},
        )
        db.add(sample)
        db.flush()
        evaluate_metric_sample(db, sample)
        cpu_samples.append(sample)

    db.add(MetricSample(
        organization_id=org.id,
        metric_definition_id=ram_metric.id,
        observed_at=failure_at - timedelta(seconds=90),
        value_numeric=87.0,
        unit="percent",
        dimensions={"hostname": vm.hostname, "demo": True},
    ))

    log_source = LogSource(
        organization_id=org.id,
        name="Demo Tomcat Error Log",
        source_type="APPLICATION_LOG",
        resource_type="APPLICATION",
        resource_id=app.id,
        location="demo://tomcat/catalina.log",
        parser_type="RAW",
        start_position="NEW",
        retention_days=30,
    )
    db.add(log_source)
    db.flush()

    db.add_all([
        LogEvent(
            organization_id=org.id,
            log_source_id=log_source.id,
            observed_at=failure_at - timedelta(seconds=45),
            severity="ERROR",
            event_type="APPLICATION_ERROR",
            message="Demo Tomcat: database connection pool exhausted while processing pricing request",
            parser_type="RAW",
            fingerprint="demo-tomcat-db-pool-exhausted",
            attributes={"application": app.name, "demo": True},
        ),
        LogEvent(
            organization_id=org.id,
            log_source_id=log_source.id,
            observed_at=failure_at - timedelta(seconds=20),
            severity="CRITICAL",
            event_type="APPLICATION_ERROR",
            message="Demo Tomcat: request processing failed because downstream database is unavailable",
            parser_type="RAW",
            fingerprint="demo-tomcat-db-unavailable",
            attributes={"application": app.name, "demo": True},
        ),
    ])

    db.flush()

    alert_rule = AlertRule(
        organization_id=org.id,
        metric_definition_id=cpu_metric.id,
        name=f"DEMO High CPU - {scenario_name}",
        severity="CRITICAL",
        operator="GTE",
        threshold_value="90",
        evaluation_window_seconds=300,
        consecutive_breaches=3,
        enabled=True,
        notification_channels=[],
    )
    db.add(alert_rule)
    db.flush()

    # Re-evaluate after the rule exists so the three persisted samples open the alert.
    for sample in cpu_samples:
        evaluate_metric_sample(db, sample)

    db.commit()

    correlation = correlate_execution(db, history.id)
    db.commit()
    db.refresh(correlation)

    return {
        "organization_id": str(org.id),
        "vm_id": str(vm.id),
        "application_id": str(app.id),
        "job_order_id": str(job.id),
        "history_id": str(history.id),
        "cpu_metric_id": str(cpu_metric.id),
        "log_source_id": str(log_source.id),
        "alert_rule_id": str(alert_rule.id),
        "correlation_id": str(correlation.id),
        "primary_category": correlation.primary_category,
        "confidence": correlation.confidence,
        "evidence_count": correlation.evidence_count,
        "summary": correlation.summary,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate an OpsControl correlation demo scenario.")
    parser.add_argument(
        "--scenario",
        default="correlation-lab",
        help="Synthetic scenario identifier. A new isolated dataset is created each run.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = create_scenario(db, args.scenario)
        print("\nOpsControl demo correlation scenario created.\n")
        for key, value in result.items():
            print(f"{key}: {value}")
        print("\nUse the history_id with:")
        print(f"POST /api/v1/etl/executions/{result['history_id']}/correlation")
        print(f"GET  /api/v1/etl/executions/{result['history_id']}/correlation")
    finally:
        db.close()


if __name__ == "__main__":
    main()

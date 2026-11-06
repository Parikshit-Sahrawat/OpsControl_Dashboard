"""Data-preserving preflight for ETL downgrades; historical revisions unchanged."""

from alembic.script import ScriptDirectory
from alembic.script.revision import RangeNotAncestorError
from sqlalchemy import inspect, text

# A whole-table check is deliberately conservative for old shared projections.
# A column check permits legacy rows only when the removed field is NULL.
PROTECTED = {
    "0041_etl_authority_writer": [
        ("etl_native_bindings", None),
        ("etl_native_attestations", None),
        ("etl_authority_revocations", None),
        ("etl_binding_qualifications", None),
    ],
    "0040_etl_native_bindings": [
        ("etl_native_bindings", None),
        ("etl_binding_receipts", None),
    ],
    "0039_etl_workflow_foundation": [
        ("etl_workflows", None),
        ("etl_workflow_dependencies", None),
        ("job_orders", "workflow_id"),
    ],
    "0036_native_recovery": [
        ("native_incident_failures", None),
        ("native_recovery_assessments", None),
    ],
    "0035_pentaho_history": [
        ("pentaho_historical_notices", None),
        ("expected_execution_windows", "pentaho_authority"),
        ("in_app_notifications", "historical_notice_id"),
    ],
    "0034_pentaho_review": [
        ("pentaho_evidence_reviews", None),
        ("pentaho_evidence_decisions", None),
    ],
    "0033_pentaho_attempts": [
        ("job_order_histories", None),
        ("pentaho_execution_attempts", None),
        ("pentaho_native_aliases", None),
        ("pentaho_attempt_revisions", None),
        ("pentaho_recovery_links", None),
        ("pentaho_recovery_decisions", None),
    ],
    "0032_pipeline_ownership": [
        ("pipeline_integrations", None),
        ("pipeline_connections", None),
        ("pipeline_capabilities", None),
        ("pipeline_sources", None),
        ("pipeline_methods", None),
        ("pipeline_jobs", None),
        ("pipeline_associations", None),
        ("pipeline_holds", None),
        ("pipeline_evidence", None),
        ("pipeline_operations", None),
    ],
    "0031_in_app_notifications": [("in_app_notifications", None)],
    "0030_native_incidents_v15": [
        ("native_incident_details", None),
        ("native_incident_alerts", None),
    ],
    "0027_unified_monitoring": [
        ("monitoring_resources", None),
        ("normalized_telemetry_events", None),
        ("job_order_histories", None),
        ("job_step_executions", None),
    ],
    "0021_operational_incidents": [
        ("operational_incidents", None),
        ("incident_activities", None),
    ],
    "0020_etl_monitoring_evidence": [
        ("job_order_histories", "source_evidence"),
        ("job_orders", "host_data_source_id"),
    ],
    "0018_pentaho_execution_identity": [
        ("job_order_histories", "provider_execution_id")
    ],
    "0008_correlation_engine": [
        ("correlation_records", None),
        ("correlation_evidence", None),
    ],
    "0001_initial": [
        (name, None)
        for name in (
            "job_orders",
            "job_order_histories",
            "job_step_executions",
            "pentaho_instances",
            "investigations",
            "investigation_transitions",
            "operator_notes",
            "alert_incident_events",
        )
    ],
}


def downgrade_plan(config, current, target):
    """Only explicit single-head destinations are supported for rollback."""
    script = ScriptDirectory.from_config(config)
    if isinstance(target, tuple):
        if len(target) != 1:
            raise RuntimeError(
                "ETL rollback preflight requires one explicit revision, not multiple heads"
            )
        target = target[0]
    if target and (target.startswith(("+", "-")) or ":" in target or "@" in target):
        raise RuntimeError(
            "Use an explicit Alembic revision for data-preserving migration preflight; relative/range targets are unsupported"
        )
    if current is None or current == target:
        return []
    try:
        return list(script.iterate_revisions(current, target))
    except RangeNotAncestorError:
        # A verified forward path is not a downgrade. Invalid/divergent paths
        # fail closed instead of silently bypassing the preflight.
        list(script.iterate_revisions(target, current))
        return []


def protect_downgrade(connection, config, current_heads, target):
    if len(current_heads) > 1:
        raise RuntimeError(
            "ETL rollback preflight requires a single-head schema; resolve branch ancestry separately"
        )
    plan = downgrade_plan(config, current_heads[0] if current_heads else None, target)
    checks = sorted(
        {item for revision in plan for item in PROTECTED.get(revision.revision, [])},
        key=lambda x: (x[0], x[1] or ""),
    )
    tables = set(inspect(connection).get_table_names())
    selected = sorted({table for table, column in checks if table in tables})
    if not selected:
        return
    connection.execute(text("SET LOCAL lock_timeout = '5s'"))
    # Locks persist through Alembic's outer transaction and DDL. Writers cannot
    # insert protected records after the empty-state check and before a drop.
    for table in selected:
        connection.execute(text(f'LOCK TABLE "{table}" IN ACCESS EXCLUSIVE MODE'))
    inspector = inspect(connection)
    populated = []
    for table, column in checks:
        if table not in tables:
            continue
        if column and column not in {c["name"] for c in inspector.get_columns(table)}:
            continue
        where = f' WHERE "{column}" IS NOT NULL' if column else ""
        if connection.scalar(text(f'SELECT EXISTS(SELECT 1 FROM "{table}"{where})')):
            populated.append(table + ("." + column if column else ""))
    if populated:
        raise RuntimeError(
            "Unsafe populated ETL downgrade blocked before DDL: "
            + ", ".join(populated)
            + ". Retain the current schema; take a verified full backup and rehearse isolated restoration. No automatic deletion or force override is supported."
        )

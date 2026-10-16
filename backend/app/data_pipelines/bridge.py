"""Read-only adapter bridge: bind native identity before legacy jobchain normalization."""

import json
import uuid
from copy import deepcopy
from app.data_pipelines.service import PipelineError, digest
from app.pipeline_adapters import PLATFORM_ADAPTERS

# These fields identify jobs, never executions. Names are deliberately absent.
NATIVE_FIELDS = {
    "AIRFLOW": "dag_id",
    "IICS": "taskId",
    "NIFI": "componentId",
    "ADF": "pipelineId",
    "AWS_GLUE": "JobArn",
    "SSIS": "package_id",
    "TALEND": "taskId",
    "PENTAHO": "native_job_id",
    "CUSTOM": "native_job_id",
}
SCOPED_SELECTORS = {"AIRFLOW": "dag_id", "IICS": "task_id", "AWS_GLUE": "job_name"}


def native_identity(platform, fact, requested=None):
    record = (fact.get("evidence") or {}).get("raw_record", {})
    if "redacted_json" in record:
        try:
            record = json.loads(record["redacted_json"])
        except (ValueError, TypeError):
            return None
    field = NATIVE_FIELDS[platform]
    explicit = fact.get("native_job_id") or record.get(field)
    if explicit is not None:
        if requested is not None and str(explicit) != str(requested):
            return None
        return str(explicit)
    # Only APIs which address one stable native job directly may inherit the
    # authenticated request identity. Collection from a list/log never may.
    if platform in {"AIRFLOW", "IICS", "AWS_GLUE"} and requested is not None:
        return str(requested)
    return None


def adf_native_id(configuration, record):
    from urllib.parse import quote

    name = record.get("pipelineName")
    if (
        not isinstance(name, str)
        or not name
        or not all(
            configuration.get(k)
            for k in ("subscription_id", "resource_group", "factory_name")
        )
    ):
        return None
    return (
        "/subscriptions/"
        + quote(configuration["subscription_id"], safe="")
        + "/resourceGroups/"
        + quote(configuration["resource_group"], safe="")
        + "/providers/Microsoft.DataFactory/factories/"
        + quote(configuration["factory_name"], safe="")
        + "/pipelines/"
        + quote(name, safe="")
    )


def collect_method(
    integration, method, connection, jobs, checkpoint, source_identity=None
):
    base = {
        **connection.configuration,
        **method.configuration.get("adapter_overrides", {}),
    }
    platform = integration.platform
    cursor = deepcopy(checkpoint)
    cursor.setdefault("jobs", {})
    events = []
    complete = True
    if method.configuration["method_type"] == "DATABASE" and platform == "SSIS":
        return collect_ssis(base, jobs, cursor)
    if method.configuration["method_type"] != "PLATFORM_API":
        raise PipelineError("AGENT_OR_METHOD_TRANSPORT_REQUIRED")
    if platform == "AWS_GLUE":
        import boto3
        from app.pipeline_adapters.core import AdapterError

        from botocore.config import Config

        expected_profile = (
            "opsc-pipeline-"
            + str(integration.organization_id).replace("-", "").lower()
            + "-"
        )
        if not str(base.get("profile_name", "")).startswith(expected_profile):
            raise AdapterError("CONFIGURATION", "Customer-bound AWS profile required")
        session = boto3.Session(
            profile_name=base["profile_name"], region_name=base["region"]
        )
        account = session.client(
            "sts",
            config=Config(
                connect_timeout=5, read_timeout=15, retries={"max_attempts": 1}
            ),
        ).get_caller_identity()["Account"]
        partition = session.get_partition_for_region(base["region"])
        prefix = (
            "arn:" + partition + ":glue:" + base["region"] + ":" + account + ":job/"
        )
        if (
            source_identity
            and source_identity.get("account") != account
            or any(not job.native_id.startswith(prefix) for job in jobs)
        ):
            raise AdapterError(
                "AUTHENTICATION",
                "Glue workload identity or native job authority differs from canonical source",
            )
    selector = SCOPED_SELECTORS.get(platform)
    # Broad-list adapters run once. Scoped adapters retain a cursor per native job.
    targets = [None]
    if selector:
        ordered = sorted(jobs, key=lambda item: item.native_id)
        position = int(cursor.get("_next_job", 0)) % max(len(ordered), 1)
        targets = ordered[position : position + 1]
        cursor["_next_job"] = (position + len(targets)) % max(len(ordered), 1)
        cursor["_covered_native_ids"] = [job.native_id for job in targets]
    else:
        cursor.pop("_covered_native_ids", None)
    for job in targets:
        cfg = deepcopy(base)
        if selector:
            native = job.native_id
            if platform == "AWS_GLUE":
                if not native.startswith(prefix) or ":job/" not in native:
                    raise PipelineError("GLUE_NATIVE_ARN_REQUIRED")
                cfg[selector] = native.split(":job/", 1)[1]
            else:
                cfg[selector] = native
        key = job.native_id if job else "__inventory__"
        adapter = PLATFORM_ADAPTERS[platform](cfg)
        batch = adapter.collect_with_retry(cursor["jobs"].get(key, {}))
        if len(batch.events) > 10000:
            raise PipelineError("PROVIDER_BATCH_LIMIT")
        parent_identities = {}
        for fact in batch.events:
            identity = native_identity(
                platform,
                fact,
                job.native_id if job else None,
            )
            if platform == "ADF" and identity is None:
                raw = fact.get("evidence", {}).get("raw_record", {})
                try:
                    record = (
                        json.loads(raw["redacted_json"])
                        if "redacted_json" in raw
                        else raw
                    )
                    identity = adf_native_id(base, record)
                except (TypeError, ValueError):
                    identity = None
            execution = (fact.get("event") or {}).get("execution_id")
            if not str(fact.get("event", {}).get("event_type", "")).startswith("STEP"):
                if (
                    execution in parent_identities
                    and parent_identities[execution] != identity
                ):
                    parent_identities[execution] = None
                else:
                    parent_identities[execution] = identity
            events.append({**fact, "native_job_id": identity})
        for fact in events:
            if str(fact.get("event", {}).get("event_type", "")).startswith(
                "STEP"
            ) and not fact.get("native_job_id"):
                fact["native_job_id"] = parent_identities.get(
                    fact["event"].get("execution_id")
                )
        cursor["jobs"][key] = batch.checkpoint
        complete = complete and batch.complete
    return events, cursor, complete


def collect_ssis(cfg, jobs, cursor):
    """Resolve immutable catalogue IDs before existing SSIS normalization.

    Unmatched historical deployment versions are not guessed by package name.
    """
    from app.pipeline_adapters.native import SSIS
    from app.pipeline_adapters.core import secret, AdapterError, provider_error

    try:
        import pyodbc
    except ImportError:
        raise AdapterError(
            "DEPENDENCY_UNAVAILABLE", "Supported ODBC driver/runtime required"
        ) from None
    if len(jobs) > 100:
        raise PipelineError("SSIS_SELECTED_JOB_QUERY_LIMIT")
    adapter = SSIS(cfg)
    state = deepcopy(cursor.get("jobs", {}).get("__inventory__", {}))
    last = int(state.get("last_execution_id", 0))
    active = [int(x) for x in state.get("active_execution_ids", [])][:100]
    clauses = []
    parameters = []
    for job in jobs[:100]:
        try:
            project, guid = job.native_id.split(":", 1)
            project = int(project)
            uuid.UUID(guid)
        except (ValueError, AttributeError):
            raise PipelineError(
                "SSIS_NATIVE_PROJECT_AND_PACKAGE_GUID_REQUIRED"
            ) from None
        clauses.append("(p.project_id=? AND p.package_guid=?)")
        parameters.extend([project, guid])
    if not clauses:
        return [], cursor, True
    query = (
        """SELECT TOP (1000) e.execution_id,e.folder_name,e.project_name,e.package_name,e.status,e.start_time,e.end_time,
        p.project_id,p.package_guid FROM catalog.executions e
        JOIN catalog.folders f ON f.name=e.folder_name
        JOIN catalog.projects pr ON pr.folder_id=f.folder_id AND pr.name=e.project_name AND pr.object_version_lsn=e.project_lsn
        JOIN catalog.packages p ON p.project_id=pr.project_id AND p.name=e.package_name
        WHERE ("""
        + " OR ".join(clauses)
        + ") AND (e.execution_id>?"
        + (
            " OR e.execution_id IN (" + ",".join("?" for _ in active) + ")"
            if active
            else ""
        )
        + ") ORDER BY e.execution_id"
    )
    parameters.extend([last, *active])
    try:
        with pyodbc.connect(secret(cfg["connection_ref"]), timeout=15) as db:
            stream = db.cursor()
            stream.execute(query, *parameters)
            columns = [x[0] for x in stream.description]
            rows = [dict(zip(columns, row)) for row in stream.fetchall()]
    except Exception as error:
        raise provider_error(error) from None
    batch = adapter.batch(rows, {}, complete=len(rows) < 1000)
    for fact in batch.events:
        record = json.loads(fact["evidence"]["raw_record"]["redacted_json"])
        fact["native_job_id"] = (
            str(record["project_id"]) + ":" + str(record["package_guid"])
        )
    next_state = {
        "last_execution_id": max([last, *[int(r["execution_id"]) for r in rows]]),
        "active_execution_ids": [
            int(r["execution_id"]) for r in rows if int(r["status"]) in {1, 2, 5}
        ],
    }
    cursor["jobs"]["__inventory__"] = next_state
    return batch.events, cursor, batch.complete


def create_job_resource(db, integration, job):
    """New V1.6 job identity projects onto the unchanged V1.5 resource contract."""
    from app.models import JobOrder, DataSource, Collector
    from app.unified.models import MonitoringResource, ResourceDependency

    db.info["unified_manual_binding"] = True
    parent = (
        db.get(MonitoringResource, integration.vm_resource_id)
        if integration.vm_resource_id
        else None
    )
    if parent and (
        parent.domain != "VM"
        or parent.organization_id != integration.organization_id
        or parent.environment != integration.environment
    ):
        raise PipelineError("INHERITANCE_SCOPE_CHANGED")
    name = "pipeline:" + digest([str(integration.id), job.native_id])[:40]
    order = JobOrder(
        organization_id=integration.organization_id,
        vm_id=parent.vm_id if parent else None,
        host_data_source_id=parent.data_source_id if parent else None,
        name=name,
        environment=integration.environment,
        monitoring_enabled=False,
    )
    source = DataSource(
        organization_id=integration.organization_id,
        name=job.name + " evidence",
        source_type=integration.platform,
        enabled=True,
        connection_config={"opscontrol": {"environment": integration.environment}},
    )
    db.add_all([order, source])
    db.flush()
    collector = Collector(
        data_source_id=source.id,
        name=job.name + " V1.6 evidence",
        collector_type="PIPELINE_V16_PROXY",
        enabled=True,
        interval_seconds=60,
        configuration={
            "integration_id": str(integration.id),
            "native_job_id": job.native_id,
        },
    )
    db.add(collector)
    db.flush()
    resource = MonitoringResource(
        id=order.id,
        organization_id=integration.organization_id,
        domain="ETL",
        name=job.name,
        environment=integration.environment,
        job_order_id=order.id,
        linked_vm_id=parent.vm_id if parent else None,
        data_source_id=source.id,
        primary_collector_id=collector.id,
        configuration={
            "platform": integration.platform,
            "jobchain": name,
            "pipeline_integration_id": str(integration.id),
            "native_job_id": job.native_id,
            "log_paths": [],
        },
        active=True,
        activation_status="CONFIGURED",
    )
    db.add(resource)
    db.flush()
    if parent:
        db.add(
            ResourceDependency(
                organization_id=integration.organization_id,
                resource_id=resource.id,
                depends_on_id=parent.id,
                relationship_type="HOSTED_ON",
            )
        )
    return resource


def discover(integration, connection):
    """Global-cadence inventory, with completeness tied to actual pagination."""
    from app.pipeline_adapters.core import http_request, AdapterError, secret

    cfg = connection.configuration
    platform = integration.platform
    rows = []
    if platform == "AIRFLOW":
        offset = 0
        for _ in range(100):
            page = http_request(
                cfg["base_url"].rstrip("/")
                + "/api/v1/dags?limit=100&offset="
                + str(offset),
                cfg,
            )
            items = page.get("dags", [])
            rows.extend({"native_id": x["dag_id"], "name": x["dag_id"]} for x in items)
            offset += len(items)
            if offset >= page.get("total_entries", offset + 1):
                return rows, True
            if not items:
                return rows, False
        return rows, False
    if platform == "AWS_GLUE":
        import boto3

        client = boto3.Session(
            profile_name=cfg.get("profile_name"), region_name=cfg["region"]
        ).client("glue")
        identity = (
            boto3.Session(
                profile_name=cfg.get("profile_name"), region_name=cfg["region"]
            )
            .client("sts")
            .get_caller_identity()
        )
        token = None
        for _ in range(100):
            page = client.get_jobs(
                **({"NextToken": token} if token else {}), MaxResults=100
            )
            rows.extend(
                {
                    "native_id": "arn:aws:glue:"
                    + cfg["region"]
                    + ":"
                    + identity["Account"]
                    + ":job/"
                    + x["Name"],
                    "name": x["Name"],
                }
                for x in page.get("Jobs", [])
            )
            token = page.get("NextToken")
            if not token:
                return rows, True
        return rows, False
    if platform == "ADF":
        from urllib.parse import quote

        root = cfg["base_url"].rstrip("/")
        path = (
            "/subscriptions/"
            + quote(cfg["subscription_id"], safe="")
            + "/resourceGroups/"
            + quote(cfg["resource_group"], safe="")
            + "/providers/Microsoft.DataFactory/factories/"
            + quote(cfg["factory_name"], safe="")
            + "/pipelines?api-version=2018-06-01"
        )
        url = root + path
        for _ in range(100):
            page = http_request(url, cfg)
            rows.extend(
                {"native_id": x["id"], "name": x["name"]} for x in page.get("value", [])
            )
            url = page.get("nextLink")
            if not url:
                return rows, True
            if not url.startswith(root + "/subscriptions/"):
                raise AdapterError(
                    "CONFIGURATION", "Pagination left approved factory scope"
                )
        return rows, False
    if platform == "IICS":
        page = http_request(cfg["base_url"].rstrip("/") + "/api/v2/task", cfg)
        if not isinstance(page, list):
            raise AdapterError("SCHEMA", "Expected documented task inventory")
        return [{"native_id": str(x["id"]), "name": x["name"]} for x in page], True
    if platform == "NIFI":
        from urllib.parse import quote

        page = http_request(
            cfg["base_url"].rstrip("/")
            + "/nifi-api/flow/process-groups/"
            + quote(cfg["process_group_id"], safe=""),
            cfg,
        )
        processors = page["processGroupFlow"]["flow"]["processors"]
        return [
            {"native_id": x["id"], "name": x["component"]["name"]} for x in processors
        ], True
    if platform == "TALEND":
        offset = 0
        for _ in range(100):
            page = http_request(
                cfg["base_url"].rstrip("/")
                + "/processing/executables/tasks?limit=100&offset="
                + str(offset),
                cfg,
            )
            items = page.get("items", [])
            rows.extend({"native_id": str(x["id"]), "name": x["name"]} for x in items)
            offset += len(items)
            if offset >= page.get("total", offset + 1):
                return rows, True
            if not items:
                return rows, False
        return rows, False
    if platform == "SSIS":
        import pyodbc

        with pyodbc.connect(secret(cfg["connection_ref"]), timeout=15) as db:
            cursor = db.cursor()
            cursor.execute(
                "SELECT TOP (10001) project_id,package_guid,name FROM catalog.packages ORDER BY project_id,package_guid"
            )
            result = cursor.fetchall()
        return [
            {"native_id": str(x[0]) + ":" + str(x[1]), "name": x[2]}
            for x in result[:10000]
        ], len(result) <= 10000
    # Carte inventories expose running executions, not a complete persistent job
    # catalogue. Custom/Shell has no authoritative global inventory. Manual native
    # identity registration is required; absence is never reconciled from these.
    raise PipelineError(
        "AUTHORITATIVE_DISCOVERY_UNAVAILABLE_MANUAL_REGISTRATION_REQUIRED"
    )

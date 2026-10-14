"""Official read APIs; statuses retain platform semantics and unknown states remain UNKNOWN."""

from urllib.parse import quote
from datetime import datetime, timezone
from .core import Adapter, AdapterError, execution, Batch, step_event


def state(raw, mapping):
    return mapping.get(str(raw).upper(), "UNKNOWN")


class Airflow(Adapter):
    platform = "AIRFLOW"
    required = ("base_url", "dag_id")
    fields = Adapter.fields + (
        "api_version",
        "include_steps",
        "step_call_budget",
        "step_page_size",
    )
    capabilities = ("executions", "task_instances", "pagination", "manual_runs")
    step_semantics = "OPTIONAL_BOUNDED_AUTO_TASK_INSTANCES"

    def validate(self):
        super().validate()
        if type(self.config.get("include_steps", False)) is not bool:
            raise AdapterError("CONFIGURATION", "include_steps must be boolean")
        for key, maximum in [("step_call_budget", 4), ("step_page_size", 1000)]:
            if (
                type(self.config.get(key, 1 if key == "step_call_budget" else 100))
                is not int
                or not 1
                <= self.config.get(key, 1 if key == "step_call_budget" else 100)
                <= maximum
            ):
                raise AdapterError(
                    "CONFIGURATION", "Invalid step request budget/page size"
                )
        return self.config

    def _step_pages(self, checkpoint):
        cp = dict(checkpoint)
        queue = [dict(x) for x in cp.get("step_queue", [])]
        if len(queue) > 1000:
            raise AdapterError("SCHEMA", "Step queue exceeds bound")
        events = []
        size = self.config.get("step_page_size", 100)
        for _ in range(self.config.get("step_call_budget", 1)):
            if not queue:
                break
            item = queue[0]
            offset = int(item.get("offset", 0))
            version = self.config.get("api_version", "v1")
            body = self.get(
                f'/api/{version}/dags/{quote(self.config["dag_id"],safe="")}/dagRuns/{quote(item["run_id"],safe="")}/taskInstances',
                {"limit": size, "offset": offset},
            )
            rows = body["task_instances"]
            if not isinstance(rows, list) or len(rows) > size:
                raise AdapterError("SCHEMA", "Invalid task inventory size")
            parent = {
                "event": {
                    "execution_id": item["run_id"],
                    "jobchain": self.config["dag_id"],
                    "execution_type": item.get("execution_type", "SCHEDULED"),
                }
            }
            for row in rows:
                task = row["task_id"]
                index = row.get("map_index", -1)
                status = state(
                    row.get("state"),
                    {
                        "SUCCESS": "SUCCESS",
                        "FAILED": "FAILED",
                        "UPSTREAM_FAILED": "FAILED",
                        "RUNNING": "RUNNING",
                        "UP_FOR_RETRY": "UNKNOWN",
                        "SKIPPED": "UNKNOWN",
                    },
                )
                events.append(
                    step_event(
                        self.platform,
                        parent,
                        row,
                        f"{task}:{index}",
                        task,
                        status,
                        row.get("start_date"),
                        row.get("end_date"),
                        max(1, int(row.get("try_number", 1))),
                        row.get("updated_at"),
                    )
                )
            total = body.get("total_entries")
            more = (
                offset + len(rows) < total if total is not None else len(rows) == size
            )
            if more:
                item["offset"] = offset + len(rows)
            else:
                queue.pop(0)
        cp["step_queue"] = queue
        return Batch(
            events,
            {"platform": self.platform, "step_requests_bounded": True},
            cp,
            not queue and cp.get("inventory_complete", True),
        )

    def collect(self, checkpoint=None):
        cp = checkpoint or {}
        if cp.get("step_queue"):
            return self._step_pages(cp)
        limit = self.config.get("page_size", 100)
        offset = cp.get("offset", 0)
        version = self.config.get("api_version", "v1")
        if version not in {"v1", "v2"}:
            raise AdapterError("CONFIGURATION", "Airflow API version must be v1 or v2")
        body = self.get(
            f'/api/{version}/dags/{quote(self.config["dag_id"],safe="")}/dagRuns',
            {"limit": limit, "offset": offset, "order_by": "-start_date"},
        )
        records = body["dag_runs"]
        total = body.get("total_entries", len(records))
        batch = self.batch(
            records,
            {"offset": offset + len(records) if offset + len(records) < total else 0},
            offset + len(records) >= total,
        )
        if self.config.get("include_steps"):
            batch.checkpoint.update(
                step_queue=[
                    {
                        "run_id": r["dag_run_id"],
                        "offset": 0,
                        "execution_type": (
                            "MANUAL" if r.get("run_type") == "manual" else "SCHEDULED"
                        ),
                    }
                    for r in records
                ],
                inventory_complete=batch.complete,
            )
            batch.complete = False if records else batch.complete
        return batch

    def normalize(self, r):
        if r.get("dag_id", self.config["dag_id"]) != self.config["dag_id"]:
            return None
        return execution(
            self.platform,
            self.config["dag_id"],
            r["dag_run_id"],
            state(
                r.get("state"),
                {
                    "SUCCESS": "SUCCESS",
                    "FAILED": "FAILED",
                    "RUNNING": "RUNNING",
                    "QUEUED": "UNKNOWN",
                },
            ),
            r.get("start_date"),
            r.get("end_date"),
            r.get("logical_date") or r.get("execution_date"),
            {"run_id": r["dag_run_id"], "provider_state": r.get("state")},
            "MANUAL" if r.get("run_type") == "manual" else "SCHEDULED",
        )

    def collect_steps(self, run_id):
        version = self.config.get("api_version", "v1")
        return self.get(
            f'/api/{version}/dags/{quote(self.config["dag_id"],safe="")}/dagRuns/{quote(run_id,safe="")}/taskInstances'
        )["task_instances"]


class IICS(Adapter):
    platform = "IICS"
    required = ("base_url", "task_id")
    fields = Adapter.fields + ("credential_header",)
    capabilities = ("executions", "activity_log", "pagination")

    step_semantics = "EMBEDDED_ACTIVITY_DETAILS_ONLY"

    def normalize_steps(self, record, parent):
        rows = record.get("details", [])
        if not isinstance(rows, list) or len(rows) > 1000:
            raise AdapterError("SCHEMA", "Invalid IICS activity details")
        events = []
        for row in rows:
            name = row.get("name") or row.get("taskName")
            identity = row.get("id") or row.get("taskId")
            if not name or not identity:
                continue
            status = state(
                row.get("state"),
                {
                    "1": "SUCCESS",
                    "2": "SUCCESS",
                    "3": "FAILED",
                    "4": "RUNNING",
                    "SUCCESS": "SUCCESS",
                    "FAILED": "FAILED",
                    "RUNNING": "RUNNING",
                },
            )
            events.append(
                step_event(
                    self.platform,
                    parent,
                    row,
                    identity,
                    name,
                    status,
                    row.get("startTime"),
                    row.get("endTime"),
                    max(1, int(row.get("attempt", 1))),
                )
            )
        return events

    def validate(self):
        self.config.setdefault("credential_header", "INFA-SESSION-ID")
        return super().validate()

    def collect(self, checkpoint=None):
        cp = checkpoint or {}
        size = self.config.get("page_size", 100)
        offset = cp.get("offset", 0)
        body = self.get(
            "/api/v2/activity/activityLog",
            {"taskId": self.config["task_id"], "rowLimit": size, "offset": offset},
        )
        records = (
            body
            if isinstance(body, list)
            else body.get("entries", body.get("activityLog", []))
        )
        return self.batch(
            records,
            {"offset": offset + len(records) if len(records) == size else 0},
            len(records) < size,
        )

    def normalize(self, r):
        if str(r.get("taskId", self.config["task_id"])) != str(self.config["task_id"]):
            return None
        status = state(
            r.get("state"),
            {
                "1": "SUCCESS",
                "2": "SUCCESS",
                "3": "FAILED",
                "4": "RUNNING",
                "SUCCESS": "SUCCESS",
                "FAILED": "FAILED",
                "RUNNING": "RUNNING",
            },
        )
        # IICS state 2 is completed with warnings, not failed; preserve original evidence.
        return execution(
            self.platform,
            str(r.get("taskName") or self.config["task_id"]),
            r["runId"],
            status,
            r.get("startTime"),
            r.get("endTime"),
            evidence={
                "run_id": r["runId"],
                "provider_state": r.get("state"),
                "warning": str(r.get("state")) == "2",
            },
        )


class NiFi(Adapter):
    platform = "NIFI"
    required = ("base_url", "process_group_id", "component_ids")
    fields = Adapter.fields + ("component_ids", "after")
    capabilities = (
        "flow_events",
        "provenance_pagination",
        "processor_status",
        "not_jobchain_runs",
    )

    def validate(self):
        super().validate()
        components = self.config["component_ids"]
        if (
            not isinstance(components, list)
            or not components
            or len(components) > 1000
            or not all(isinstance(x, str) and x for x in components)
        ):
            raise AdapterError(
                "CONFIGURATION",
                "NiFi requires explicit component IDs to scope flow evidence",
            )
        return self.config

    def collect(self, checkpoint=None):
        # NiFi provenance queries are asynchronous read-only searches. Persist the
        # query ID across polls; an unfinished search is not an empty healthy flow.
        cp = checkpoint or {}
        size = self.config.get("page_size", 100)
        query_id = cp.get("query_id")
        if not query_id:
            body = self.get(
                "/nifi-api/provenance",
                method="POST",
                body={
                    "provenance": {
                        "request": {
                            "maxResults": size,
                            "searchTerms": {},
                            "startDate": cp.get("after") or self.config.get("after"),
                        }
                    }
                },
            )
            query_id = body["provenance"]["id"]
        body = self.get("/nifi-api/provenance/" + quote(str(query_id), safe=""))
        result = body["provenance"]
        results = result.get("results", {})
        if not result.get("finished", False):
            return self.batch(
                [], {"query_id": query_id, "after": cp.get("after")}, False
            )
        records = results.get("provenanceEvents", [])
        # Query state is temporary server-side search state, not a flow mutation.
        self.get(
            "/nifi-api/provenance/" + quote(str(query_id), safe=""), method="DELETE"
        )
        times = [r["eventTime"] for r in records]
        return self.batch(
            records,
            {"after": max(times) if times else cp.get("after")},
            len(records) < size,
        )

    def normalize(self, r):
        allowed = set(self.config.get("component_ids", []))
        if allowed and r.get("componentId") not in allowed:
            return None
        raw = str(r.get("eventType", "")).upper()
        status = (
            "FAILED"
            if raw == "DROP" and r.get("details", "").lower().find("fail") >= 0
            else "UNKNOWN"
        )
        return execution(
            self.platform,
            str(
                r.get("componentName")
                or r.get("componentId")
                or self.config["process_group_id"]
            ),
            f'{r.get("flowFileUuid", "flow")}:event:{r["eventId"]}',
            status,
            observed=r["eventTime"],
            evidence={
                "flowfile_uuid": r.get("flowFileUuid"),
                "provenance_event_id": r["eventId"],
                "event_type": raw,
                "semantics": "FLOW_EVENT",
            },
        )

    def flow_status(self):
        return self.get(
            f'/nifi-api/flow/process-groups/{quote(self.config["process_group_id"],safe="")}/status'
        )


class AzureDataFactory(Adapter):
    platform = "ADF"
    required = ("base_url", "subscription_id", "resource_group", "factory_name")
    fields = Adapter.fields + ("after", "before", "api_version")
    capabilities = ("executions", "activity_runs", "continuation_token")

    step_semantics = "EMBEDDED_ACTIVITY_RUNS_AND_ON_DEMAND_API"

    def normalize_steps(self, record, parent):
        rows = record.get("activityRuns", [])
        if not isinstance(rows, list) or len(rows) > 1000:
            raise AdapterError("SCHEMA", "Invalid ADF activity inventory")
        events = []
        for row in rows:
            name = row["activityName"]
            identity = row["activityRunId"]
            status = state(
                row.get("status"),
                {
                    "SUCCEEDED": "SUCCESS",
                    "FAILED": "FAILED",
                    "CANCELLED": "FAILED",
                    "INPROGRESS": "RUNNING",
                },
            )
            events.append(
                step_event(
                    self.platform,
                    parent,
                    row,
                    identity,
                    name,
                    status,
                    row.get("activityRunStart"),
                    row.get("activityRunEnd"),
                    max(1, int(row.get("retryAttempt", 0)) + 1),
                )
            )
        return events

    def prefix(self):
        c = self.config
        return (
            "/subscriptions/"
            + quote(c["subscription_id"], safe="")
            + "/resourceGroups/"
            + quote(c["resource_group"], safe="")
            + "/providers/Microsoft.DataFactory/factories/"
            + quote(c["factory_name"], safe="")
        )

    def collect(self, checkpoint=None):
        cp = checkpoint or {}
        after = cp.get("after") or self.config.get("after")
        before = (
            cp.get("before")
            or self.config.get("before")
            or datetime.now(timezone.utc).isoformat()
        )
        if not after:
            raise AdapterError(
                "CONFIGURATION",
                "ADF requires an explicit initial lastUpdatedAfter boundary",
            )
        payload = {"lastUpdatedAfter": after, "lastUpdatedBefore": before}
        if cp.get("continuation_token"):
            payload["continuationToken"] = cp["continuation_token"]
        body = self.get(
            self.prefix() + "/queryPipelineRuns",
            {"api-version": self.config.get("api_version", "2018-06-01")},
            "POST",
            payload,
        )
        token = body.get("continuationToken")
        return self.batch(
            body.get("value", []),
            {
                "after": after if token else before,
                "before": before if token else None,
                "continuation_token": token,
            },
            not token,
        )

    def normalize(self, r):
        return execution(
            self.platform,
            r["pipelineName"],
            r["runId"],
            state(
                r.get("status"),
                {
                    "SUCCEEDED": "SUCCESS",
                    "FAILED": "FAILED",
                    "CANCELLED": "FAILED",
                    "INPROGRESS": "RUNNING",
                    "QUEUED": "UNKNOWN",
                    "CANCELING": "RUNNING",
                },
            ),
            r.get("runStart"),
            r.get("runEnd"),
            r.get("lastUpdated"),
            {"provider_state": r.get("status"), "run_id": r["runId"]},
        )

    def collect_steps(self, run_id, after, before, continuation_token=None):
        return self.get(
            self.prefix()
            + "/pipelineruns/"
            + quote(run_id, safe="")
            + "/queryActivityruns",
            {"api-version": self.config.get("api_version", "2018-06-01")},
            "POST",
            {
                "lastUpdatedAfter": after,
                "lastUpdatedBefore": before,
                **(
                    {"continuationToken": continuation_token}
                    if continuation_token
                    else {}
                ),
            },
        )


class Talend(Adapter):
    platform = "TALEND"
    required = ("base_url",)
    fields = Adapter.fields + ("task_id",)
    capabilities = ("executions", "pagination", "cloud_management_api")

    def collect(self, checkpoint=None):
        cp = checkpoint or {}
        limit = self.config.get("page_size", 100)
        offset = cp.get("offset", 0)
        query = {"limit": limit, "offset": offset}
        if self.config.get("task_id"):
            query["taskId"] = self.config["task_id"]
        body = self.get("/processing/executions", query)
        records = body if isinstance(body, list) else body.get("items", [])
        return self.batch(
            records,
            {"offset": offset + len(records) if len(records) == limit else 0},
            len(records) < limit,
        )

    def normalize(self, r):
        if self.config.get("task_id") and r.get("taskId") != self.config["task_id"]:
            return None
        return execution(
            self.platform,
            r.get("taskName") or r["taskId"],
            r.get("executionId") or r.get("id"),
            state(
                r.get("status"),
                {
                    "EXECUTION_SUCCESSFUL": "SUCCESS",
                    "SUCCESS": "SUCCESS",
                    "EXECUTION_FAILED": "FAILED",
                    "FAILED": "FAILED",
                    "EXECUTION_REJECTED": "FAILED",
                    "RUNNING": "RUNNING",
                    "EXECUTION_RUNNING": "RUNNING",
                    "EXECUTION_TERMINATED": "FAILED",
                },
            ),
            r.get("startTimestamp") or r.get("startTime"),
            r.get("finishTimestamp") or r.get("endTime"),
            r.get("lastUpdated"),
            {"provider_state": r.get("status"), "task_id": r.get("taskId")},
        )

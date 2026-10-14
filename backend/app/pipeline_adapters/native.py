"""Supported read-only SDK, database, Carte and local JSONL adapters."""

import json
import hashlib
import os
from pathlib import Path
from datetime import timezone
from .core import Adapter, AdapterError, Batch, execution, provider_error, step_event


class Pentaho(Adapter):
    platform = "PENTAHO"
    required = ("url", "job_name", "allowed_hosts", "allowed_cidrs")
    fields = Adapter.fields + ("execution_id", "collect_logs", "job_order_id")
    capabilities = ("carte_job_status", "step_results", "logs", "explicit_execution_id")

    step_semantics = "EMBEDDED_CARTE_JOB_ENTRY_RESULTS"

    def validate(self):
        super().validate()
        if type(self.config.get("collect_logs", False)) is not bool:
            raise AdapterError("CONFIGURATION", "collect_logs must be boolean")
        for key in ("allowed_hosts", "allowed_cidrs"):
            if (
                not isinstance(self.config[key], list)
                or not self.config[key]
                or len(self.config[key]) > 32
                or not all(isinstance(x, str) and x for x in self.config[key])
            ):
                raise AdapterError("CONFIGURATION", "Invalid " + key)
        return self.config

    def collect(self, checkpoint=None):
        from app.worker.pentaho_status import get_job_status

        cfg = {
            k: v
            for k, v in self.config.items()
            if k not in {"timeout_seconds", "page_size", "auth_type"}
        }
        result = (
            self.transport(cfg)
            if getattr(self.transport, "__name__", "") != "http_request"
            else get_job_status(cfg)
        )
        event = execution(
            self.platform,
            self.config["job_name"],
            result["execution_id"],
            result["execution_status"],
            result.get("started_at"),
            result.get("ended_at"),
            evidence={
                "steps": result.get("steps", []),
                "nr_errors": result.get("nr_errors", 0),
            },
        )
        rows = result.get("steps", [])
        if not isinstance(rows, list) or len(rows) > 1000:
            raise AdapterError("SCHEMA", "Invalid Carte step inventory")
        events = [event]
        for index, row in enumerate(rows):
            name = row["name"]
            identity = row.get("id") or name + ":" + str(index)
            status = row.get("status", "UNKNOWN")
            events.append(
                step_event(
                    self.platform,
                    event,
                    row,
                    identity,
                    name,
                    status,
                    row.get("started_at"),
                    row.get("ended_at"),
                    max(1, int(row.get("attempt", 1))),
                )
            )
        return Batch(
            events,
            {"platform": self.platform, "read_only": True},
            {"execution_id": result["execution_id"]},
        )


class AWSGlue(Adapter):
    platform = "AWS_GLUE"
    required = ("region", "job_name")
    fields = Adapter.fields + ("profile_name",)
    capabilities = (
        "executions",
        "job_errors",
        "continuation_token",
        "aws_workload_identity",
    )

    def __init__(self, configuration, transport=None, client=None):
        super().__init__(configuration, transport)
        self.client = client

    def collect(self, checkpoint=None):
        if self.client is None:
            try:
                import boto3
            except ImportError as exc:
                raise AdapterError(
                    "DEPENDENCY_UNAVAILABLE", "AWS Glue requires optional boto3 SDK"
                ) from exc
            session = boto3.Session(
                profile_name=self.config.get("profile_name"),
                region_name=self.config["region"],
            )
            self.client = session.client("glue")
        kwargs = {
            "JobName": self.config["job_name"],
            "MaxResults": min(self.config.get("page_size", 100), 200),
        }
        if (checkpoint or {}).get("next_token"):
            kwargs["NextToken"] = checkpoint["next_token"]
        try:
            body = self.client.get_job_runs(**kwargs)
        except Exception as exc:
            raise provider_error(exc) from exc
        token = body.get("NextToken")
        return self.batch(body.get("JobRuns", []), {"next_token": token}, not token)

    def normalize(self, r):
        mapping = {
            "STARTING": "RUNNING",
            "RUNNING": "RUNNING",
            "STOPPING": "RUNNING",
            "SUCCEEDED": "SUCCESS",
            "FAILED": "FAILED",
            "STOPPED": "FAILED",
            "TIMEOUT": "FAILED",
            "ERROR": "FAILED",
            "WAITING": "UNKNOWN",
            "EXPIRED": "FAILED",
        }
        return execution(
            self.platform,
            self.config["job_name"],
            r["Id"],
            mapping.get(r.get("JobRunState"), "UNKNOWN"),
            r.get("StartedOn"),
            r.get("CompletedOn"),
            r.get("LastModifiedOn"),
            {
                "provider_state": r.get("JobRunState"),
                "attempt": r.get("Attempt"),
                "previous_run_id": r.get("PreviousRunId"),
            },
        )


class SSIS(Adapter):
    platform = "SSIS"
    required = ("connection_ref",)
    fields = Adapter.fields + ("folder_name", "project_name", "package_name")
    capabilities = (
        "ssisdb_executions",
        "incremental_execution_id",
        "windows_sqlserver_odbc",
    )

    def validate(self):
        from app.telemetry.configuration import env_reference

        super().validate()
        env_reference(self.config["connection_ref"])
        return self.config

    def __init__(self, configuration, transport=None, connect=None):
        super().__init__(configuration, transport)
        self.connect = connect

    def collect(self, checkpoint=None):
        from app.telemetry.delivery import secret

        connect = self.connect
        if connect is None:
            try:
                import pyodbc
            except ImportError as exc:
                raise AdapterError(
                    "DEPENDENCY_UNAVAILABLE",
                    "SSIS requires optional pyodbc and Microsoft SQL Server ODBC driver",
                ) from exc
            connect = pyodbc.connect
        # Fixed parameterized read only; service identity must have SSISDB catalog SELECT rights only.
        cp = checkpoint or {}
        active = [int(x) for x in cp.get("active_ids", [])][:1000]
        filters = [
            "(execution_id > ?"
            + (
                " OR execution_id IN (" + ",".join("?" for _ in active) + ")"
                if active
                else ""
            )
            + ")"
        ]
        values = [int(cp.get("execution_id", 0)), *active]
        for column in ("folder_name", "project_name", "package_name"):
            if self.config.get(column):
                filters.append(column + " = ?")
                values.append(self.config[column])
        limit = self.config.get("page_size", 100)
        sql = (
            f"SELECT TOP ({limit}) execution_id,folder_name,project_name,package_name,status,start_time,end_time FROM SSISDB.catalog.executions WHERE "
            + " AND ".join(filters)
            + " ORDER BY execution_id"
        )
        conn = connect(secret(self.config["connection_ref"]), timeout=15)
        try:
            cursor = conn.cursor()
            cursor.execute(sql, *values)
            rows = [
                dict(zip([d[0] for d in cursor.description], row))
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()
        return self.batch(
            rows,
            {
                "execution_id": max([values[0], *[r["execution_id"] for r in rows]]),
                "active_ids": [
                    r["execution_id"] for r in rows if int(r["status"]) in {1, 2, 5}
                ],
            },
            len(rows) < limit,
        )

    def normalize(self, r):
        mapping = {
            1: "UNKNOWN",
            2: "RUNNING",
            3: "FAILED",
            4: "FAILED",
            5: "UNKNOWN",
            6: "FAILED",
            7: "SUCCESS",
            8: "FAILED",
            9: "SUCCESS",
        }
        return execution(
            self.platform,
            "/".join(
                str(r[k]) for k in ("folder_name", "project_name", "package_name")
            ),
            r["execution_id"],
            mapping.get(int(r["status"]), "UNKNOWN"),
            r.get("start_time"),
            r.get("end_time"),
            evidence={"ssis_status": r["status"]},
        )


class CustomShell(Adapter):
    platform = "CUSTOM"
    required = ("path", "jobchain")
    fields = Adapter.fields + ("max_bytes",)
    capabilities = (
        "jsonl_execution_events",
        "rotation",
        "byte_checkpoint",
        "no_command_execution",
    )

    def validate(self):
        super().validate()
        if not Path(self.config["path"]).is_absolute():
            raise AdapterError("CONFIGURATION", "Local source path must be absolute")
        if (
            type(self.config.get("max_bytes", 1048576)) is not int
            or not 1 <= self.config.get("max_bytes", 1048576) <= 1048576
        ):
            raise AdapterError("CONFIGURATION", "max_bytes must be 1..1048576")
        return self.config

    def collect(self, checkpoint=None):
        # Only operator-approved read roots; configured shell commands are never executed.
        path = Path(self.config["path"]).resolve(strict=True)
        roots = [
            Path(x).resolve()
            for x in os.getenv("OPSCONTROL_PIPELINE_LOG_ROOTS", "").split(os.pathsep)
            if x
        ]
        if not any(path.is_relative_to(root) for root in roots):
            raise AdapterError(
                "CONFIGURATION", "Local log path is outside operator-approved roots"
            )
        cp = checkpoint or {}
        size = min(int(self.config.get("max_bytes", 1048576)), 1048576)
        with path.open("rb") as stream:
            stat = os.fstat(stream.fileno())
            identity = f"{stat.st_dev}:{stat.st_ino}"
            prefix_length = int(cp.get("prefix_length", 0))
            prior_prefix = (
                hashlib.sha256(stream.read(prefix_length)).hexdigest()
                if prefix_length
                else None
            )
            offset = (
                int(cp.get("offset", 0))
                if cp.get("identity") == identity
                and stat.st_size >= int(cp.get("offset", 0))
                and (not prefix_length or prior_prefix == cp.get("prefix_sha256"))
                else 0
            )
            stream.seek(offset)
            data = stream.read(size + 1)
            if len(data) > size:
                data = data[:size]
            end = data.rfind(b"\n")
            if end < 0 and len(data) >= size:
                raise AdapterError("SCHEMA", "JSONL record exceeds bounded read size")
            data = data[: end + 1] if end >= 0 else b""
        lines = data.splitlines(keepends=True)[:1000]
        consumed = sum(len(line) for line in lines)
        records = []
        cursor_offset = offset
        for line in lines:
            if line.strip():
                record = json.loads(line)
                # Source coordinates preserve distinct equal-content raw records.
                record["_source_identity"] = identity
                record["_source_offset"] = cursor_offset
                records.append(record)
            cursor_offset += len(line)
        prefix_length = min(256, offset + consumed)
        with path.open("rb") as prefix_stream:
            prefix = hashlib.sha256(prefix_stream.read(prefix_length)).hexdigest()
        batch = self.batch(
            records,
            {
                "identity": identity,
                "offset": offset + consumed,
                "prefix_length": prefix_length,
                "prefix_sha256": prefix,
            },
            offset + consumed >= stat.st_size,
        )
        return batch

    step_semantics = "JSONL_EXPLICIT_STEP_EVENTS"

    def normalize(self, r):
        status = r.get("status", "UNKNOWN")
        if status not in {"RUNNING", "SUCCESS", "FAILED", "UNKNOWN"}:
            raise AdapterError("SCHEMA", "Custom execution status is not supported")
        if str(r.get("event_type", "")).startswith("STEP_"):
            kind = r["event_type"]
            if kind not in {"STEP_START", "STEP_END", "STEP_FAILED", "STEP_STATUS"}:
                raise AdapterError("SCHEMA", "Unsupported custom step event type")
            name = r.get("step_name") or r.get("step")
            identity = r.get("step_id") or name
            parent = {
                "event": {
                    "execution_id": str(r["execution_id"]),
                    "jobchain": self.config["jobchain"],
                    "execution_type": r.get("execution_type", "SCHEDULED"),
                }
            }
            fact = step_event(
                self.platform,
                parent,
                r,
                identity,
                name,
                status,
                r.get("started_at")
                or (r.get("timestamp") if kind == "STEP_START" else None),
                r.get("ended_at")
                or (
                    r.get("timestamp") if kind in {"STEP_END", "STEP_FAILED"} else None
                ),
                int(r.get("attempt", 1)),
                r.get("timestamp"),
            )
            fact["event"]["event_type"] = kind
            return fact
        return execution(
            self.platform,
            self.config["jobchain"],
            r["execution_id"],
            status,
            r.get("started_at"),
            r.get("ended_at"),
            r.get("timestamp"),
            {
                "source_record_id": r.get("record_id"),
                "source_identity": r.get("_source_identity"),
                "source_offset": r.get("_source_offset"),
                "step": r.get("step"),
                "attempt": r.get("attempt"),
            },
            r.get("execution_type", "SCHEDULED"),
        )

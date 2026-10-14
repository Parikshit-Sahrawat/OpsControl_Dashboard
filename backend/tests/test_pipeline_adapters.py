import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch


def raises(exception):
    return unittest.TestCase().assertRaises(exception)


class Environment:

    def __init__(self, case):
        self.case = case

    def setenv(self, key, value):
        handle = patch.dict("os.environ", {key: value})
        handle.start()
        self.case.addCleanup(handle.stop)


"Contract fixtures model official provider responses; they are not live acceptance."
import json
from datetime import datetime, timezone
from app.pipeline_adapters import PLATFORM_ADAPTERS, ADAPTER_DEFINITIONS, AdapterError
from app.pipeline_adapters.core import http_request, execution
from app.pipeline_adapters.http import Airflow, IICS, NiFi, AzureDataFactory, Talend
from app.pipeline_adapters.native import AWSGlue, SSIS, CustomShell, Pentaho

START = "2026-01-01T00:00:00Z"
END = "2026-01-01T00:01:00Z"


def transport(response, calls=None):

    def read(url, cfg, method="GET", body=None):
        if calls is not None:
            calls.append((url, method, body))
        return response

    return read


NORMALIZATION_CASES = [
    (
        Airflow,
        {"base_url": "https://airflow.test", "dag_id": "dag"},
        {"dag_run_id": "run", "state": "success", "start_date": START, "end_date": END},
    ),
    (
        IICS,
        {"base_url": "https://iics.test", "task_id": "task"},
        {
            "runId": "run",
            "taskName": "task",
            "state": 1,
            "startTime": START,
            "endTime": END,
        },
    ),
    (
        AzureDataFactory,
        {
            "base_url": "https://management.azure.com",
            "subscription_id": "s",
            "resource_group": "g",
            "factory_name": "f",
        },
        {
            "pipelineName": "pipe",
            "runId": "run",
            "status": "Succeeded",
            "runStart": START,
            "runEnd": END,
        },
    ),
    (
        Talend,
        {"base_url": "https://talend.test"},
        {
            "taskId": "task",
            "executionId": "run",
            "status": "EXECUTION_SUCCESSFUL",
            "startTimestamp": START,
            "finishTimestamp": END,
        },
    ),
    (
        AWSGlue,
        {"region": "ap-south-1", "job_name": "job"},
        {
            "Id": "run",
            "JobRunState": "SUCCEEDED",
            "StartedOn": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "CompletedOn": datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc),
        },
    ),
    (
        SSIS,
        {"connection_ref": "env:TEST_SQL"},
        {
            "execution_id": 12,
            "folder_name": "f",
            "project_name": "p",
            "package_name": "x",
            "status": 7,
            "start_time": START,
            "end_time": END,
        },
    ),
    (
        CustomShell,
        {"path": "/unused", "jobchain": "job"},
        {
            "execution_id": "run",
            "status": "SUCCESS",
            "started_at": START,
            "ended_at": END,
        },
    ),
]


def check_platform_normalization(cls, cfg, record):
    adapter = cls(cfg)
    first = adapter.normalize(record)
    assert first["event"]["status"] == "SUCCESS"
    assert adapter.normalize(record)["key"] == first["key"]
    assert first["event"]["started_at"] < first["event"]["ended_at"]
    assert adapter.discover_capabilities()["live_verified"] is False
    assert adapter.health(adapter.batch([record], {}))["status"] == "CONNECTED"


class PipelineAdapterTests(unittest.TestCase):

    def test_platform_normalization(self):
        for cls, cfg, record in NORMALIZATION_CASES:
            with self.subTest(platform=cls.platform):
                check_platform_normalization(cls, cfg, record)

    def test_registry_all_nine_and_closed_configs(self):
        assert set(PLATFORM_ADAPTERS) == {
            "PENTAHO",
            "IICS",
            "AIRFLOW",
            "NIFI",
            "ADF",
            "AWS_GLUE",
            "SSIS",
            "TALEND",
            "CUSTOM",
        }
        assert all((value["read_only"] for value in ADAPTER_DEFINITIONS.values()))
        with raises(AdapterError):
            Airflow({"base_url": "https://x", "dag_id": "dag", "password": "plaintext"})
        with raises(ValueError):
            Airflow(
                {
                    "base_url": "https://x",
                    "dag_id": "dag",
                    "credential_ref": "plaintext",
                }
            )

    def test_airflow_pagination_and_steps(self):
        calls = []
        adapter = Airflow(
            {"base_url": "https://x", "dag_id": "dag", "page_size": 1},
            transport(
                {
                    "dag_runs": [
                        {"dag_run_id": "a", "state": "running", "start_date": START}
                    ],
                    "total_entries": 2,
                },
                calls,
            ),
        )
        first = adapter.collect()
        assert not first.complete and first.checkpoint == {"offset": 1}
        adapter.collect(first.checkpoint)
        assert "offset=1" in calls[-1][0]
        assert first.events[0]["event"]["status"] == "RUNNING"

    def test_iics_warnings_unknown_and_paging(self):
        cfg = {"base_url": "https://x", "task_id": "task", "page_size": 1}
        record = {"runId": "r", "state": 2, "startTime": START, "endTime": END}
        adapter = IICS(cfg, transport([record]))
        batch = adapter.collect()
        assert not batch.complete and batch.events[0]["evidence"]["warning"]
        assert (
            adapter.normalize({**record, "state": 888})["event"]["status"] == "UNKNOWN"
        )

    def test_adf_body_window_continuation_and_failure(self):
        calls = []
        record = {
            "pipelineName": "p",
            "runId": "r",
            "status": "Failed",
            "runStart": START,
            "runEnd": END,
        }
        adapter = AzureDataFactory(
            {
                "base_url": "https://management.azure.com",
                "subscription_id": "s",
                "resource_group": "g",
                "factory_name": "f",
                "after": START,
                "before": END,
            },
            transport({"value": [record], "continuationToken": "next"}, calls),
        )
        batch = adapter.collect()
        adapter.collect(batch.checkpoint)
        assert calls[0][1] == "POST" and calls[1][2]["continuationToken"] == "next"
        assert batch.events[0]["event"]["status"] == "FAILED"

    def test_nifi_async_flow_semantics(self):
        responses = iter(
            [
                {"provenance": {"id": "q"}},
                {"provenance": {"finished": False}},
                {
                    "provenance": {
                        "finished": True,
                        "results": {
                            "provenanceEvents": [
                                {
                                    "eventId": 1,
                                    "flowFileUuid": "flow",
                                    "eventTime": START,
                                    "eventType": "SEND",
                                    "componentId": "c",
                                }
                            ]
                        },
                    }
                },
                {},
            ]
        )
        adapter = NiFi(
            {"base_url": "https://x", "process_group_id": "g", "component_ids": ["c"]},
            lambda *args: next(responses),
        )
        pending = adapter.collect()
        assert not pending.complete and (not pending.events)
        batch = adapter.collect(pending.checkpoint)
        assert batch.events[0]["event"]["status"] == "UNKNOWN"
        assert batch.events[0]["evidence"]["semantics"] == "FLOW_EVENT"

    def test_glue_sdk_read_only_checkpoint(self):

        class Client:

            def get_job_runs(self, **kw):
                assert kw["JobName"] == "j"
                return {
                    "JobRuns": [
                        {
                            "Id": "r",
                            "JobRunState": "FAILED",
                            "StartedOn": START,
                            "CompletedOn": END,
                        }
                    ],
                    "NextToken": "next",
                }

        adapter = AWSGlue({"region": "ap-south-1", "job_name": "j"}, client=Client())
        batch = adapter.collect()
        assert not batch.complete and batch.checkpoint["next_token"] == "next"
        assert batch.events[0]["event"]["status"] == "FAILED"

    def test_ssis_active_runs_revisited(self):
        monkeypatch = Environment(self)
        monkeypatch.setenv("TEST_SQL", "Driver=fixture")

        class Cursor:
            description = [
                (x,)
                for x in [
                    "execution_id",
                    "folder_name",
                    "project_name",
                    "package_name",
                    "status",
                    "start_time",
                    "end_time",
                ]
            ]

            def execute(self, sql, *args):
                assert " OR execution_id IN (?)" in sql and args == (20, 12)

            def fetchall(self):
                return [(12, "f", "p", "x", 7, START, END)]

        class Connection:

            def cursor(self):
                return Cursor()

            def close(self):
                pass

        adapter = SSIS(
            {"connection_ref": "env:TEST_SQL"}, connect=lambda *a, **kw: Connection()
        )
        result = adapter.collect({"execution_id": 20, "active_ids": [12]})
        assert (
            result.checkpoint["active_ids"] == []
            and result.events[0]["event"]["status"] == "SUCCESS"
        )

    def test_pentaho_preserves_carte_step_evidence(self):
        adapter = Pentaho(
            {
                "url": "https://x/kettle/jobStatus",
                "job_name": "j",
                "allowed_hosts": ["x"],
                "allowed_cidrs": ["10.0.0.0/8"],
            },
            lambda cfg: {
                "execution_id": "r",
                "execution_status": "FAILED",
                "started_at": START,
                "ended_at": END,
                "nr_errors": 1,
                "steps": [{"name": "load", "status": "FAILED"}],
            },
        )
        batch = adapter.collect()
        assert batch.events[0]["event"]["status"] == "FAILED"
        assert batch.events[0]["evidence"]["steps"][0]["name"] == "load"

    def test_custom_checkpoint_partial_rotation_and_distinct_raw(self):
        monkeypatch = Environment(self)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        tmp_path = Path(temporary.name)
        monkeypatch.setenv("OPSCONTROL_PIPELINE_LOG_ROOTS", str(tmp_path))
        path = tmp_path / "jobs.jsonl"
        record = {
            "execution_id": "a",
            "timestamp": START,
            "status": "RUNNING",
            "record_id": "1",
        }
        path.write_text(
            json.dumps(record) + "\n" + json.dumps({**record, "record_id": "2"})
        )
        adapter = CustomShell({"path": str(path), "jobchain": "j"})
        first = adapter.collect()
        assert len(first.events) == 1
        with path.open("a") as stream:
            stream.write("\n")
        second = adapter.collect(first.checkpoint)
        assert len(second.events) == 1
        assert first.events[0]["key"] != second.events[0]["key"]
        path.rename(tmp_path / "old")
        path.write_text(json.dumps({**record, "execution_id": "b"}) + "\n")
        assert (
            adapter.collect(second.checkpoint).events[0]["event"]["execution_id"] == "b"
        )

    def test_tls_egress_fails_closed(self):
        monkeypatch = Environment(self)
        monkeypatch.setenv("OPSCONTROL_NATIVE_ALLOWED_HOSTS", "allowed.test")
        for url in [
            "http://allowed.test/a",
            "https://evil.test/a",
            "https://user:pass@allowed.test/a",
        ]:
            with raises(ValueError):
                http_request(url, {})

    def test_invalid_time_rejected_and_distinct_sources_preserved(self):
        with raises(AdapterError):
            execution("x", "j", "r", "SUCCESS", "2026-01-01T00:00:00", END)
        first = execution(
            "x", "j", "r", "SUCCESS", START, END, evidence={"source_record_id": 1}
        )
        second = execution(
            "x", "j", "r", "SUCCESS", START, END, evidence={"source_record_id": 2}
        )
        assert first["key"] != second["key"]

    def test_retries_preserve_checkpoint_and_auth_is_not_retried(self):
        for cls, cfg, _ in NORMALIZATION_CASES:
            with self.subTest(platform=cls.platform):
                adapter = cls(cfg)
                calls = []
                checkpoint = {"cursor": "durable"}

                def collect(cp):
                    calls.append(cp)
                    if len(calls) < 3:
                        raise AdapterError("THROTTLED", "rate limit")
                    from app.pipeline_adapters import Batch

                    return Batch(checkpoint=cp)

                adapter.collect = collect
                sleeps = []
                self.assertEqual(
                    adapter.collect_with_retry(
                        checkpoint, sleep=sleeps.append
                    ).checkpoint,
                    checkpoint,
                )
                self.assertEqual(calls, [checkpoint] * 3)
                self.assertEqual(sleeps, [1, 2])

                def unauthorized(cp):
                    raise AdapterError("AUTHENTICATION", "credentials rejected")

                adapter.collect = unauthorized
                with self.assertRaises(AdapterError):
                    adapter.collect_with_retry(
                        checkpoint,
                        sleep=lambda delay: self.fail("Authentication must not retry"),
                    )

    def test_http_auth_rate_limit_schema_and_redirection(self):
        from app.pipeline_adapters import core
        from unittest.mock import patch

        class Response:
            status = 200

            def read(self, bound):
                return b'{"records":[]}'

        class Connection:
            def __init__(self, *args):
                pass

            def request(self, *args, **kwargs):
                pass

            def getresponse(self):
                return response

            def close(self):
                pass

        with patch.dict(
            "os.environ",
            {
                "OPSCONTROL_NATIVE_ALLOWED_HOSTS": "provider.test",
                "OPSCONTROL_NATIVE_ALLOWED_PORTS": "443",
                "OPSCONTROL_NATIVE_ALLOWED_CIDRS": "203.0.113.0/24",
            },
        ), patch.object(
            core, "resolve_target", return_value="203.0.113.1"
        ), patch.object(
            core, "PinnedHTTPS", Connection
        ):
            response = Response()
            self.assertEqual(
                core.http_request("https://provider.test/api", {}), {"records": []}
            )
            for status, kind in [
                (401, "AUTHENTICATION"),
                (403, "AUTHENTICATION"),
                (429, "THROTTLED"),
                (302, "PROVIDER"),
                (503, "PROVIDER"),
            ]:
                response.status = status
                with self.assertRaises(AdapterError) as raised:
                    core.http_request("https://provider.test/api", {})
                self.assertEqual(raised.exception.kind, kind)
            response.status = 200
            response.read = lambda bound: b"not json"
            with self.assertRaises(AdapterError) as raised:
                core.http_request("https://provider.test/api", {})
            self.assertEqual(raised.exception.kind, "SCHEMA")

    def test_custom_identical_records_remain_distinct_and_resume(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "events.jsonl"
        record = {"execution_id": "r", "timestamp": START, "status": "RUNNING"}
        path.write_text(json.dumps(record) + "\n" + json.dumps(record) + "\n")
        with patch.dict(
            "os.environ", {"OPSCONTROL_PIPELINE_LOG_ROOTS": temporary.name}
        ):
            adapter = CustomShell({"path": str(path), "jobchain": "j"})
            batch = adapter.collect()
            self.assertEqual(len(batch.events), 2)
            self.assertNotEqual(batch.events[0]["key"], batch.events[1]["key"])
            self.assertFalse(adapter.collect(batch.checkpoint).events)
            path.write_text(json.dumps({**record, "execution_id": "s"}) + "\n")
            self.assertEqual(
                adapter.collect(batch.checkpoint).events[0]["event"]["execution_id"],
                "s",
            )

    def test_terminal_snapshot_does_not_invent_execution_end(self):
        from app.pipeline_adapters.core import execution

        fact = execution("IICS", "j", "r", "FAILED", START)
        self.assertTrue(fact["event"]["terminal_status_observed"])
        self.assertIsNone(fact["event"]["ended_at"])
        first = execution("IICS", "j", "r", "SUCCESS")
        second = execution("IICS", "j", "r", "SUCCESS")
        self.assertIsNone(first["event"]["started_at"])
        self.assertIsNone(first["event"]["ended_at"])
        self.assertEqual(first["event"]["timestamp_provenance"], "RECEIVED_OBSERVATION")
        self.assertEqual(first["key"], second["key"])

    def test_airflow_steps_bounded_paginated_resume_and_attempt(self):
        requests = []
        responses = iter(
            [
                {
                    "dag_runs": [
                        {
                            "dag_run_id": "r",
                            "state": "success",
                            "start_date": START,
                            "end_date": END,
                        }
                    ],
                    "total_entries": 1,
                },
                {
                    "task_instances": [
                        {
                            "task_id": "extract",
                            "map_index": 0,
                            "state": "success",
                            "try_number": 2,
                            "start_date": START,
                            "end_date": END,
                        }
                    ],
                    "total_entries": 2,
                },
                {
                    "task_instances": [
                        {
                            "task_id": "load",
                            "map_index": 1,
                            "state": "failed",
                            "try_number": 1,
                            "start_date": START,
                        }
                    ],
                    "total_entries": 2,
                },
            ]
        )

        def read(*args):
            requests.append(args)
            return next(responses)

        adapter = Airflow(
            {
                "base_url": "https://airflow.test",
                "dag_id": "d",
                "include_steps": True,
                "step_call_budget": 1,
                "step_page_size": 1,
            },
            read,
        )
        first = adapter.collect()
        self.assertEqual(len(requests), 1)
        self.assertEqual(first.checkpoint["step_queue"][0]["run_id"], "r")
        second = adapter.collect(first.checkpoint)
        self.assertEqual(len(requests), 2)
        step = second.events[0]["event"]
        self.assertEqual(step["event_type"], "STEP_END")
        self.assertEqual(step["step_id"], "extract:0")
        self.assertEqual(step["attempt"], 2)
        self.assertEqual(second.checkpoint["step_queue"][0]["offset"], 1)
        third = adapter.collect(second.checkpoint)
        self.assertEqual(len(requests), 3)
        self.assertTrue(third.complete)
        self.assertFalse(third.checkpoint["step_queue"])
        self.assertEqual(third.events[0]["event"]["event_type"], "STEP_FAILED")
        self.assertIsNone(third.events[0]["event"]["ended_at"])
        self.assertTrue(third.events[0]["event"]["terminal_status_observed"])
        self.assertIn("offset=1", requests[-1][0])

    def test_pentaho_untimed_step_failure_preserved_without_fake_duration(self):
        adapter = Pentaho(
            {
                "url": "https://carte.test/kettle/jobStatus",
                "job_name": "j",
                "allowed_hosts": ["carte.test"],
                "allowed_cidrs": ["10.0.0.0/8"],
            },
            lambda cfg: {
                "execution_id": "r",
                "execution_status": "FAILED",
                "started_at": START,
                "nr_errors": 1,
                "steps": [{"name": "load", "status": "FAILED"}],
            },
        )
        batch = adapter.collect()
        self.assertEqual(len(batch.events), 2)
        step = batch.events[1]["event"]
        self.assertEqual(step["event_type"], "STEP_FAILED")
        self.assertIsNone(step["started_at"])
        self.assertIsNone(step["ended_at"])
        self.assertEqual(step["timestamp_provenance"], "RECEIVED_OBSERVATION")
        self.assertTrue(step["terminal_status_observed"])

    def test_iics_embedded_activity_detail_and_invalid_inventory(self):
        record = {
            "runId": "r",
            "taskName": "task",
            "state": 1,
            "startTime": START,
            "endTime": END,
            "details": [
                {
                    "id": "s",
                    "name": "extract",
                    "state": 1,
                    "startTime": START,
                    "endTime": END,
                }
            ],
        }
        adapter = IICS(
            {"base_url": "https://iics.test", "task_id": "task"}, transport([record])
        )
        batch = adapter.collect()
        self.assertEqual(len(batch.events), 2)
        self.assertEqual(batch.events[1]["event"]["step_name"], "extract")
        self.assertEqual(batch.events[1]["event"]["event_type"], "STEP_END")
        with self.assertRaises(AdapterError):
            adapter.batch([{**record, "details": "invalid"}], {})

    def test_adf_embedded_activity_and_on_demand_continuation(self):
        calls = []
        record = {
            "pipelineName": "p",
            "runId": "r",
            "status": "Succeeded",
            "runStart": START,
            "runEnd": END,
            "activityRuns": [
                {
                    "activityName": "copy",
                    "activityRunId": "step",
                    "status": "Succeeded",
                    "activityRunStart": START,
                    "activityRunEnd": END,
                    "retryAttempt": 1,
                }
            ],
        }
        adapter = AzureDataFactory(
            {
                "base_url": "https://management.azure.com",
                "subscription_id": "s",
                "resource_group": "g",
                "factory_name": "f",
                "after": START,
                "before": END,
            },
            transport({"value": [record]}, calls),
        )
        batch = adapter.collect()
        self.assertEqual(len(batch.events), 2)
        self.assertEqual(batch.events[1]["event"]["attempt"], 2)
        adapter.collect_steps("r", START, END, "continuation")
        self.assertEqual(calls[-1][2]["continuationToken"], "continuation")
        self.assertIn("/queryActivityruns", calls[-1][0])

    def test_configuration_registry_helpers_types_and_closed_properties(self):
        from app.pipeline_adapters import (
            describe_platform,
            validate_platform_configuration,
        )

        description = describe_platform("PENTAHO")
        attribute = next(
            a
            for a in description["configuration_schema"]["attributes"]
            if a["key"] == "collect_logs"
        )
        self.assertEqual(attribute["type"], "boolean")
        self.assertFalse(description["live_verified"])
        self.assertEqual(
            describe_platform("AWS_GLUE")["step_collection"], "NOT_AVAILABLE"
        )
        with self.assertRaises(AdapterError):
            validate_platform_configuration(
                "AIRFLOW",
                {"base_url": "https://x", "dag_id": "d", "include_steps": "true"},
            )
        with self.assertRaises(AdapterError):
            validate_platform_configuration(
                "AIRFLOW",
                {
                    "base_url": "https://x",
                    "dag_id": "d",
                    "include_steps": True,
                    "step_call_budget": 5,
                },
            )
        with self.assertRaises(AdapterError):
            describe_platform("PLACEHOLDER")

    def test_custom_explicit_step_record_does_not_end_parent_execution(self):
        adapter = CustomShell({"path": "/approved/jobs.jsonl", "jobchain": "j"})
        fact = adapter.normalize(
            {
                "execution_id": "r",
                "event_type": "STEP_FAILED",
                "step_id": "load",
                "step_name": "load",
                "status": "FAILED",
                "timestamp": END,
                "started_at": START,
                "attempt": 2,
            }
        )
        self.assertEqual(fact["event"]["event_type"], "STEP_FAILED")
        self.assertEqual(fact["event"]["attempt"], 2)
        self.assertEqual(fact["event"]["step_id"], "load")
        self.assertEqual(fact["event"]["ended_at"], "2026-01-01T00:01:00+00:00")

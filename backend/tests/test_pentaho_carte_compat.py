"""Synthetic Carte edge cases; these are not installed-build acceptance fixtures."""

import base64
import gzip
import json
import os
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.pipeline_adapters.core import AdapterError
from app.pipeline_adapters.native import Pentaho
from app.pipeline_adapters.pentaho_carte import collect, parse_status
from app.pipeline_adapters.pentaho_observations import normalize_observation
from app.services.etl_monitoring import ingest_snapshot
from app.models import DataSource, JobOrder, JobOrderHistory, JobStepExecution
from app.worker.pentaho_status import (
    PentahoStatusError,
    get_job_status,
    parse_carte_status,
)
from tests.test_pentaho_r1 import END, scope

NATIVE = Path(__file__).resolve().parents[2] / "tests/fixtures/pentaho/native-evidence"


def job(state="Finished", result="Y", errors="0", exit_status="0", extra=""):
    fields = "".join(
        f"<{key}>{value}</{key}>"
        for key, value in (
            ("result", result),
            ("nr_errors", errors),
            ("exit_status", exit_status),
        )
        if value is not None
    )
    return (
        f"<jobstatus><id>run-1</id><status_desc>{state}</status_desc>"
        f"<result>{fields}</result>{extra}</jobstatus>"
    ).encode()


class CarteCompatTests(unittest.TestCase):
    def test_native_inventory_extracts_job_despite_empty_transformations(self):
        inventory = (NATIVE / "RT-LAB-012A-native-inventory.xml").read_bytes()
        detail = (NATIVE / "RT-LAB-010O-final-job-status.xml").read_bytes()
        native = "cf20aa45-7332-4f3a-a41e-282367d146e5"
        config = {
            "url": "https://carte.test/kettle",
            "job_name": "OC_TEST_JOB",
            "allowed_hosts": ["carte.test"],
            "allowed_cidrs": ["192.0.2.0/24"],
        }
        paths = []

        def transport(host, ip, path, authorization):
            paths.append(path)
            return 200, inventory if path.startswith("/kettle/status/") else detail

        with patch.dict(
            os.environ,
            {
                "OPSCONTROL_LOCAL_ALLOWED_HOSTS": "carte.test",
                "OPSCONTROL_LOCAL_ALLOWED_CIDRS": "192.0.2.0/24",
            },
        ), patch(
            "app.worker.pentaho_status.check_target",
            return_value=(SimpleNamespace(hostname="carte.test", path="/kettle"), []),
        ), patch(
            "app.worker.pentaho_status.resolve_target", return_value="192.0.2.1"
        ):
            result = get_job_status(config, transport=transport)
            self.assertEqual(
                [row["execution_id"] for row in result["executions"]], [native]
            )
            self.assertEqual(result["executions"][0]["native_status_desc"], "Finished")
            self.assertFalse(result["inventory_complete"])
            self.assertEqual(len(paths), 2)

        scoped = scope("CARTE", exact_build="9.4.0.0-343", native_job_id="OC_TEST_JOB")
        configuration = {**config, "monitoring_context": scoped}
        get = Mock(
            side_effect=lambda path, query: (
                inventory if path == "/kettle/status/" else detail
            )
        )
        with patch(
            "app.pipeline_adapters.pentaho_carte.reader", return_value=(get, ())
        ):
            batch = collect(configuration, None, "customer-a")
            repeat = collect(configuration, batch.checkpoint, "customer-a")
        self.assertEqual(len(batch.events), 1)
        self.assertEqual(batch.events[0]["evidence"]["native_execution_id"], native)
        self.assertEqual(
            batch.events[0]["evidence"]["native_observation"]["provider_status"],
            "Finished",
        )
        self.assertFalse(batch.complete)
        self.assertFalse(batch.evidence["inventory_complete"])
        self.assertEqual(repeat.events, [])
        self.assertNotIn("inventory_status_desc", batch.events[0]["evidence"])

        trans_cfg = {
            **configuration,
            "job_name": "OC_TEST_TRANSFORMATION",
            "monitoring_context": scope(
                "CARTE",
                exact_build="9.4.0.0-343",
                workload_kind="TRANSFORMATION",
                native_job_id="OC_TEST_TRANSFORMATION",
            ),
        }
        trans_get = Mock(return_value=inventory)
        with patch(
            "app.pipeline_adapters.pentaho_carte.reader", return_value=(trans_get, ())
        ):
            empty = collect(trans_cfg, None, "customer-a")
        self.assertEqual(empty.events, [])
        self.assertFalse(empty.complete)
        trans_get.assert_called_once_with("/kettle/status/", "xml=Y")

    def test_native_transformation_outcomes_and_step_metrics(self):
        fixtures = (
            (
                "RT-LAB-005B-execution-status.xml",
                "a5a594c6-8ad7-4b3f-b518-22157f0eba68",
                "SUCCESS",
                0,
                "Finished",
            ),
            (
                "RT-LAB-007-before-execution.xml",
                "d9f9df50-8d8c-491a-a7fd-ef15118f54f1",
                "RUNNING",
                None,
                "Waiting",
            ),
            (
                "RT-LAB-007-after-execution.xml",
                "d9f9df50-8d8c-491a-a7fd-ef15118f54f1",
                "FAILED",
                1,
                "Finished (with errors)",
            ),
            (
                "RT-LAB-008-before-execution.xml",
                "075bbc01-b896-4304-98a4-63fa70d4f752",
                "RUNNING",
                None,
                "Waiting",
            ),
            (
                "RT-LAB-008-after-start-error.xml",
                "075bbc01-b896-4304-98a4-63fa70d4f752",
                "FAILED",
                1,
                "Finished (with errors)",
            ),
        )
        cfg = scope("CARTE", exact_build="9.4.0.0-343", workload_kind="TRANSFORMATION")
        for filename, native, outcome, errors, status in fixtures:
            body = (NATIVE / filename).read_bytes()
            with self.subTest(filename=filename):
                legacy = parse_carte_status(body, workload_kind="TRANSFORMATION")
                r1 = parse_status(body, cfg, native, END)
                self.assertEqual(legacy["execution_id"], native)
                self.assertEqual(legacy["execution_status"], outcome)
                self.assertEqual(r1["status"], outcome)
                self.assertEqual(r1["provider_status"], status)
                self.assertEqual(r1["nr_errors"], errors)
                self.assertEqual(r1["native_result"], None if errors is None else "Y")
                self.assertEqual(legacy["steps"], r1["native_steps"])
                if outcome == "FAILED":
                    self.assertIn(
                        "NATIVE_RESULT_Y_WITH_ERRORS", r1["evidence_warnings"]
                    )
                    self.assertEqual(r1["native_exit_status"], 0)
                    self.assertTrue(
                        any(row["nr_errors"] == 1 for row in r1["native_steps"])
                    )
                if errors is None:
                    self.assertEqual(r1["native_steps"], [])

        failed = (NATIVE / "RT-LAB-007-after-execution.xml").read_bytes()
        record = parse_status(failed, cfg, "d9f9df50-8d8c-491a-a7fd-ef15118f54f1", END)
        self.assertEqual(
            [s["name"] for s in record["native_steps"]],
            ["Generate synthetic rows", "Controlled runtime abort"],
        )
        self.assertEqual([s["copy"] for s in record["native_steps"]], ["0", "0"])
        self.assertEqual(
            record["native_steps"][1]["metrics"],
            {
                "errors": 1,
                "linesWritten": 1,
                "linesRead": 1,
                "linesInput": 0,
                "linesOutput": 0,
            },
        )
        self.assertEqual(record["native_steps"][1]["statusDescription"], "Stopped")
        self.assertEqual(record["native_steps"][1]["status"], "FAILED")

        configuration = {
            "job_name": cfg["native_job_id"],
            "execution_id": "d9f9df50-8d8c-491a-a7fd-ef15118f54f1",
            "monitoring_context": cfg,
        }
        with patch(
            "app.pipeline_adapters.pentaho_carte.reader",
            return_value=(Mock(return_value=failed), ()),
        ):
            batch = collect(configuration, None, "customer-a")
        self.assertEqual(len(batch.events), 3)
        self.assertEqual(batch.events[0]["event"]["status"], "FAILED")
        self.assertEqual(batch.events[2]["event"]["event_type"], "STEP_FAILED")
        self.assertEqual(
            json.loads(batch.events[2]["evidence"]["raw_record"]["redacted_json"])[
                "metrics"
            ]["errors"],
            1,
        )

    def test_transformation_missing_counters_and_conflicts_remain_unknown(self):
        cfg = scope("CARTE", workload_kind="TRANSFORMATION")
        body = (NATIVE / "RT-LAB-005B-execution-status.xml").read_bytes()
        # Synthetic omissions/conflicts only; native fixture bytes remain untouched.
        missing = body.replace(b"<linesRead>0</linesRead>", b"")
        native = "a5a594c6-8ad7-4b3f-b518-22157f0eba68"
        parsed = parse_status(missing, cfg, native, END)
        self.assertIsNone(parsed["native_steps"][0]["metrics"]["linesRead"])
        conflicted = body.replace(b"<errors>0</errors>", b"<errors>1</errors>")
        parsed = parse_status(conflicted, cfg, native, END)
        self.assertEqual(parsed["status"], "UNKNOWN")
        # Parent zero and step one are contradictory, so a terminal success must be withheld.
        self.assertEqual(parsed["native_steps"][0]["status"], "FAILED")

    def test_supplied_pdi_94_native_job_status_fixtures(self):
        """Read supplied lab bytes; this is not a live OpsControl RT acceptance."""
        contract = json.loads(
            (NATIVE / "RT-LAB-010T-monitoring-contract.json").read_text()
        )
        self.assertEqual(
            contract["validation_environment"]["pdi_version"], "9.4.0.0-343"
        )
        cfg = scope("CARTE", exact_build="9.4.0.0-343", native_job_id="OC_TEST_JOB")
        for expected in contract["executions"]:
            fixture = {
                "RT-LAB-010D": "RT-LAB-010D-job-status.xml",
                "RT-LAB-010H": "RT-LAB-010H-final-job-status.xml",
                "RT-LAB-010O": "RT-LAB-010O-final-job-status.xml",
            }[expected["test_id"]]
            body = (NATIVE / fixture).read_bytes()
            with self.subTest(fixture=fixture):
                legacy = parse_carte_status(body, collect_logs=True)
                r1 = parse_status(
                    body,
                    cfg,
                    expected["native_execution_id"],
                    contract["generated_at_utc"],
                    collect_logs=True,
                )
                fact = normalize_observation(r1, cfg, "synthetic-customer")
                for result in (legacy, r1):
                    self.assertEqual(
                        result.get("execution_status", result.get("status")),
                        expected["normalized_outcome"],
                    )
                    self.assertEqual(
                        result["nr_errors"], expected["native_result_error_count"]
                    )
                    self.assertEqual(
                        result["native_exit_status"], expected["native_exit_status"]
                    )
                    self.assertEqual(
                        result["native_result"],
                        "Y" if expected["native_result_success"] else "N",
                    )
                    self.assertEqual(
                        result["native_log_channel_id"],
                        expected["native_log_channel_id"] or None,
                    )
                    self.assertEqual(result["log_evidence_status"], "AVAILABLE")
                    self.assertIn("OC_TEST_SUCCESS", result["logs"])
                    self.assertFalse(result["evidence_warnings"])
                    self.assertIsNotNone(result["native_log_date_raw"])
                self.assertEqual(
                    fact["event"]["status"], expected["normalized_outcome"]
                )
                self.assertEqual(fact["event"]["workload_kind"], "JOB")
                self.assertFalse(fact["evidence"]["runtime_certified"])
                self.assertEqual(
                    fact["evidence"]["native_observation"]["native_log_channel_id"],
                    expected["native_log_channel_id"] or None,
                )

    def test_native_fixture_scoped_read_only_poll_and_idempotent_checkpoint(self):
        contract = json.loads(
            (NATIVE / "RT-LAB-010T-monitoring-contract.json").read_text()
        )
        expected = next(
            x for x in contract["executions"] if x["test_id"] == "RT-LAB-010O"
        )
        body = (NATIVE / "RT-LAB-010O-final-job-status.xml").read_bytes()
        configuration = {
            "url": "https://carte.test/kettle",
            "job_name": expected["job_name"],
            "execution_id": expected["native_execution_id"],
            "allowed_hosts": ["carte.test"],
            "allowed_cidrs": ["192.0.2.0/24"],
            "monitoring_context": scope(
                "CARTE", exact_build="9.4.0.0-343", native_job_id=expected["job_name"]
            ),
            "collect_logs": True,
        }
        get = Mock(return_value=body)
        with patch(
            "app.pipeline_adapters.pentaho_carte.reader", return_value=(get, ())
        ):
            a = Pentaho(configuration, customer_id="customer-a").collect()
            repeat = Pentaho(configuration, customer_id="customer-a").collect(
                a.checkpoint
            )
            b = Pentaho(configuration, customer_id="customer-b").collect()
        self.assertEqual(a.events[0]["event"]["status"], "SUCCESS")
        self.assertFalse(a.evidence["runtime_verified"])
        self.assertEqual(repeat.events, [])
        self.assertNotEqual(
            a.events[0]["event"]["execution_id"], b.events[0]["event"]["execution_id"]
        )
        self.assertTrue(
            all(call.args[0] == "/kettle/jobStatus/" for call in get.call_args_list)
        )
        self.assertTrue(
            all(call.args[1].endswith("&xml=Y") for call in get.call_args_list)
        )

    def test_native_result_requires_consistent_evidence(self):
        for body, expected in (
            (job(), "SUCCESS"),
            (job("Finished (with errors)", "N", "1", "0"), "FAILED"),
            (job(errors=None), "UNKNOWN"),
            (job(result="N", errors="0"), "UNKNOWN"),
            (job(result=None, errors="0"), "UNKNOWN"),
            (job(exit_status="1"), "UNKNOWN"),
            (job("Running", None, None, None), "RUNNING"),
        ):
            with self.subTest(body=body):
                legacy = parse_carte_status(body)
                r1 = parse_status(body, scope("CARTE"), "run-1", END)
                self.assertEqual(legacy["execution_status"], expected)
                self.assertEqual(r1["status"], expected)
        failed = parse_carte_status(job("Finished (with errors)", "N", "1", "0"))
        self.assertEqual(failed["native_exit_status"], 0)
        self.assertEqual(failed["native_result"], "N")
        self.assertEqual(failed["nr_errors"], 1)

    def test_legacy_adapter_preserves_step_copy_identity_on_reorder(self):
        steps = [
            {"name": "same", "copy": "0", "status": "UNKNOWN"},
            {"name": "same", "copy": "1", "status": "UNKNOWN"},
        ]
        payload = {
            "execution_id": "observed-parent",
            "execution_status": "UNKNOWN",
            "steps": steps,
        }
        adapter = Pentaho(
            {
                "url": "https://carte.test/kettle",
                "job_name": "controlled",
                "allowed_hosts": ["carte.test"],
                "allowed_cidrs": ["192.0.2.0/24"],
            },
            lambda _: payload,
        )
        before = {
            row["evidence"]["raw_record"]["redacted_json"]: row["event"]["step_id"]
            for row in adapter.collect().events[1:]
        }
        payload["steps"] = list(reversed(steps))
        after = {
            row["evidence"]["raw_record"]["redacted_json"]: row["event"]["step_id"]
            for row in adapter.collect().events[1:]
        }
        self.assertEqual(before, after)
        self.assertEqual(len(set(after.values())), 2)

    def test_native_step_observation_shape_fails_closed(self):
        from app.pipeline_adapters.pentaho_observations import validate_native_steps

        for rows in (
            None,
            {},
            [{}],
            [{"name": "x", "status": "SUCCESS", "metrics": {"linesRead": True}}],
            [{"name": "x", "status": "SUCCESS", "copy": "-1"}],
            [{"name": "x", "status": "SUCCESS", "metrics": {"unsupported": 1}}],
        ):
            with self.subTest(rows=rows), self.assertRaises(AdapterError):
                validate_native_steps(rows)
        validate_native_steps(
            [
                {
                    "name": "x",
                    "status": "UNKNOWN",
                    "copy": "0",
                    "metrics": {"linesRead": None, "linesWritten": 0},
                }
            ]
        )

    def test_missing_zero_and_malformed_numbers_stay_distinct(self):
        self.assertIsNone(parse_carte_status(job(errors=None))["nr_errors"])
        self.assertEqual(parse_carte_status(job(errors="0"))["nr_errors"], 0)
        for value in ("x", "-1", "99999999", "١"):
            with self.subTest(value=value), self.assertRaises(PentahoStatusError):
                parse_carte_status(job(errors=value))

    def test_base64_gzip_cdata_whitespace_and_redaction(self):
        raw = b"password=controlled-secret\nfinished"
        encoded = base64.b64encode(gzip.compress(raw)).decode()
        body = job(
            extra=f"<logging_string><![CDATA[ {encoded[:12]}\n {encoded[12:]} ]]></logging_string>"
        )
        record = parse_carte_status(body, collect_logs=True)
        self.assertEqual(record["log_evidence_status"], "AVAILABLE")
        self.assertIn("[REDACTED]", record["logs"])
        self.assertNotIn("controlled-secret", record["logs"])
        for encoded in (
            "not-base64!",
            base64.b64encode(gzip.compress(b"a" * 16385)).decode(),
        ):
            record = parse_carte_status(
                job(extra=f"<logging_string>{encoded}</logging_string>"),
                collect_logs=True,
            )
            self.assertEqual(record["log_evidence_status"], "DECODE_FAILED")
            self.assertIsNone(record["logs"])
            self.assertEqual(record["execution_status"], "SUCCESS")

    def test_inventory_empty_multiple_and_explicit_only_use_get(self):
        config = {
            "url": "https://carte.test/kettle",
            "job_name": "safe",
            "allowed_hosts": ["carte.test"],
            "allowed_cidrs": ["192.0.2.0/24"],
        }
        paths = []

        def transport(host, ip, path, authorization):
            paths.append(path)
            if path == "/kettle/status/?xml=Y":
                return (
                    200,
                    b"<serverstatus><job_status><jobname>safe</jobname><id>run-1</id></job_status><job_status><jobname>safe</jobname><id>run-2</id></job_status></serverstatus>",
                )
            identity = "run-1" if "id=run-1" in path else "run-2"
            return 200, job().replace(b"run-1", identity.encode())

        with patch.dict(
            os.environ,
            {
                "OPSCONTROL_LOCAL_ALLOWED_HOSTS": "carte.test",
                "OPSCONTROL_LOCAL_ALLOWED_CIDRS": "192.0.2.0/24",
            },
        ), patch(
            "app.worker.pentaho_status.check_target",
            return_value=(SimpleNamespace(hostname="carte.test", path="/kettle"), []),
        ), patch(
            "app.worker.pentaho_status.resolve_target", return_value="192.0.2.1"
        ):
            inventory = get_job_status(config, transport=transport)
            self.assertEqual(len(inventory["executions"]), 2)
            self.assertFalse(inventory["inventory_complete"])
            self.assertTrue(
                all(
                    path.startswith(("/kettle/status/", "/kettle/jobStatus/"))
                    for path in paths
                )
            )
            self.assertEqual(
                Pentaho(config, lambda _: inventory)
                .collect()
                .events[0]["event"]["status"],
                "SUCCESS",
            )
            self.assertEqual(
                len(Pentaho(config, lambda _: inventory).collect().events), 2
            )
            self.assertFalse(Pentaho(config, lambda _: inventory).collect().complete)
            paths.clear()
            explicit = get_job_status(
                {**config, "execution_id": "run-1"}, transport=transport
            )
            self.assertEqual(explicit["execution_id"], "run-1")
            self.assertEqual(len(paths), 1)
            self.assertEqual(paths[0].split("?")[0], "/kettle/jobStatus/")
            empty = Pentaho(
                config, lambda _: {"inventory_complete": False, "executions": []}
            ).collect()
            self.assertEqual(empty.events, [])

    def test_partial_inventory_ingests_observed_runs_without_claiming_no_run(self):
        customer = uuid.uuid4()
        order = uuid.uuid4()
        source = uuid.uuid4()
        job = SimpleNamespace(
            id=order,
            organization_id=customer,
            active=True,
            monitoring_enabled=True,
            expected_runtime_seconds=None,
            sla_seconds=None,
            expected_window_start=None,
            expected_window_end=None,
            no_run_grace_seconds=0,
            schedule={},
        )
        added = []

        class Rows(list):
            def all(self):
                return self

        class FakeDB:
            def get(self, model, identity):
                return (
                    job
                    if model is JobOrder
                    else (
                        SimpleNamespace(organization_id=customer)
                        if model is DataSource
                        else None
                    )
                )

            def execute(self, statement):
                return None

            def scalar(self, statement):
                return None

            def scalars(self, statement):
                return Rows()

            def add(self, row):
                added.append(row)

            def flush(self):
                return None

        collector = SimpleNamespace(
            id=uuid.uuid4(),
            collector_type="PENTAHO",
            data_source_id=source,
            configuration={"job_order_id": str(order)},
        )
        payload = {
            "provider": "PENTAHO",
            "outcome": "SUCCESS",
            "inventory_complete": False,
            "executions": [
                {
                    "execution_id": "failed",
                    "execution_status": "FAILED",
                    "nr_errors": 1,
                    "steps": [
                        {
                            "name": "same",
                            "status": "FAILED",
                            "nr_errors": 1,
                            "copy": "0",
                            "statusDescription": "Stopped",
                            "metrics": {
                                "linesRead": 1,
                                "linesWritten": 2,
                                "linesInput": None,
                                "linesOutput": 0,
                                "errors": 1,
                            },
                        },
                        {"name": "same", "status": "UNKNOWN", "nr_errors": None},
                    ],
                },
                {
                    "execution_id": "unknown",
                    "execution_status": "UNKNOWN",
                    "nr_errors": None,
                    "steps": [],
                },
            ],
        }
        with patch("app.services.etl_monitoring._alert"):
            ingest_snapshot(
                collector,
                SimpleNamespace(payload=payload),
                datetime.now(timezone.utc),
                FakeDB(),
            )
        histories = [row for row in added if isinstance(row, JobOrderHistory)]
        steps = [row for row in added if isinstance(row, JobStepExecution)]
        self.assertEqual(
            {row.provider_execution_id for row in histories}, {"failed", "unknown"}
        )
        self.assertIsNone(
            next(
                row for row in histories if row.provider_execution_id == "unknown"
            ).source_evidence["nr_errors"]
        )
        self.assertEqual(
            [row.source_evidence["observed_entry_position"] for row in steps], [0, 1]
        )
        self.assertEqual((steps[0].records_read, steps[0].records_written), (1, 2))
        self.assertEqual(steps[0].source_evidence["native_copy"], "0")
        self.assertEqual(
            steps[0].source_evidence["native_status_description"], "Stopped"
        )
        self.assertIsNone(steps[0].source_evidence["native_metrics"]["linesInput"])
        self.assertIsNone(steps[1].records_read)
        self.assertFalse(
            any(
                row.provider_execution_id.startswith("opscontrol:no-run:")
                for row in histories
            )
        )

    def test_monitoring_transport_failure_is_not_execution_failure(self):
        config = {
            "url": "https://carte.test/kettle",
            "job_name": "safe",
            "execution_id": "run-1",
            "allowed_hosts": ["carte.test"],
            "allowed_cidrs": ["192.0.2.0/24"],
        }
        with patch.dict(
            os.environ,
            {
                "OPSCONTROL_LOCAL_ALLOWED_HOSTS": "carte.test",
                "OPSCONTROL_LOCAL_ALLOWED_CIDRS": "192.0.2.0/24",
            },
        ), patch(
            "app.worker.pentaho_status.check_target",
            return_value=(SimpleNamespace(hostname="carte.test", path="/kettle"), []),
        ), patch(
            "app.worker.pentaho_status.resolve_target", return_value="192.0.2.1"
        ):
            with self.assertRaises(PentahoStatusError):
                get_job_status(config, transport=lambda *args: (500, b""))
            with self.assertRaises(PentahoStatusError):
                get_job_status(config, transport=lambda *args: (401, b""))
            with self.assertRaises(PentahoStatusError):
                get_job_status(config, transport=lambda *args: (200, b"<broken>"))
            failed = get_job_status(
                config,
                transport=lambda *args: (200, job("Finished (with errors)", "N", "1")),
            )
            self.assertEqual(failed["outcome"], "SUCCESS")
            self.assertEqual(failed["execution_status"], "FAILED")

    def test_repeated_child_names_do_not_merge_or_invent_native_uuid(self):
        entries = (
            "<jobentry_result><name>transform</name><result><nr_errors>1</nr_errors></result></jobentry_result>"
            "<jobentry_result><name>transform</name></jobentry_result>"
        )
        parsed = parse_carte_status(job(extra=entries))
        self.assertEqual([row["nr_errors"] for row in parsed["steps"]], [1, None])
        self.assertEqual(
            [row["status"] for row in parsed["steps"]], ["FAILED", "UNKNOWN"]
        )
        self.assertTrue(
            all("native_execution_id" not in row for row in parsed["steps"])
        )
        config = {
            "url": "https://carte.test/kettle",
            "job_name": "safe",
            "allowed_hosts": ["carte.test"],
            "allowed_cidrs": ["192.0.2.0/24"],
        }
        batch = Pentaho(config, lambda _: parsed).collect()
        self.assertEqual(len(batch.events), 3)
        self.assertEqual(batch.events[1]["event"]["step_id"], "transform:0")
        self.assertEqual(batch.events[2]["event"]["step_id"], "transform:1")
        self.assertEqual(
            batch.events[0]["key"],
            Pentaho(config, lambda _: parsed).collect().events[0]["key"],
        )

    def test_r1_rejects_wrong_status_root(self):
        with self.assertRaises(AdapterError):
            parse_status(
                job().replace(b"jobstatus", b"serverstatus"),
                scope("CARTE"),
                "run-1",
                END,
            )


if __name__ == "__main__":
    unittest.main()

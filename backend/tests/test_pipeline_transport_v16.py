"""Real local file reads with a controlled lease/acknowledgement transport."""

import json, tempfile, unittest, uuid
from pathlib import Path
from unittest.mock import Mock
from app.data_pipelines.transport import PipelineTransport
from app.data_pipelines.bridge import native_identity, adf_native_id
from app.data_pipelines.service import (
    canonical,
    PipelineError,
    validate_checkpoint,
    is_sample_evidence,
)
from types import SimpleNamespace


class TransportTests(unittest.TestCase):
    def client(self, path, checkpoint=None):
        client = PipelineTransport.__new__(PipelineTransport)
        ticket = {
            "source_id": str(uuid.uuid4()),
            "generation": str(uuid.uuid4()),
            "owner_id": str(uuid.uuid4()),
            "fence": 41,
            "checkpoint": checkpoint or {},
        }
        response = {
            "ticket": ticket,
            "identity": {"path": str(path)},
            "configuration": {},
        }
        client.request = Mock(side_effect=[response, {"accepted": 1}])
        return client, ticket

    def line(self):
        return (
            json.dumps(
                {
                    "native_job_id": "native-guid",
                    "evidence_origin": "CONTROLLED_FIXTURE",
                    "event": {
                        "timestamp": "2026-10-14T00:00:00+00:00",
                        "execution_id": "run-1",
                        "jobchain": "display-name",
                        "event_type": "START",
                        "status": "RUNNING",
                    },
                }
            )
            + "\n"
        )

    def test_equal_message_timestamp_records_have_distinct_source_offsets(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "jobs.jsonl"
            path.write_text(self.line() * 2)
            client, ticket = self.client(path)
            client.collect(ticket["source_id"])
            payload = client.request.call_args_list[1].args[1]
            self.assertEqual(len(payload["records"]), 2)
            self.assertNotEqual(
                payload["records"][0]["key"], payload["records"][1]["key"]
            )
            self.assertEqual(
                payload["checkpoint"]["sources"][str(path)]["offset"],
                path.stat().st_size,
            )
            self.assertEqual(
                payload["records"][0]["evidence_origin"], "CONTROLLED_FIXTURE"
            )

    def test_failed_backend_ack_never_advances_local_checkpoint(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "jobs.jsonl"
            path.write_text(self.line())
            client, ticket = self.client(path)
            first = client.request.side_effect
            claim = {
                "ticket": ticket,
                "identity": {"path": str(path)},
                "configuration": {},
            }
            client.request.side_effect = [claim, OSError("controlled interruption")]
            with self.assertRaises(OSError):
                client.collect(ticket["source_id"])
            self.assertEqual(ticket["checkpoint"], {})

    def test_partial_line_keeps_offset_and_reports_incomplete_coverage(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "jobs.jsonl"
            path.write_text(self.line().rstrip("\n"))
            client, ticket = self.client(path)
            client.collect(ticket["source_id"])
            payload = client.request.call_args_list[1].args[1]
            self.assertEqual(payload["records"], [])
            self.assertEqual(payload["checkpoint"]["sources"][str(path)]["offset"], 0)
            self.assertFalse(payload["complete"])

    def test_truncation_fails_closed_before_acceptance(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "jobs.jsonl"
            path.write_text(self.line())
            stat = path.stat()
            cp = {
                "sources": {
                    str(path): {
                        "device": stat.st_dev,
                        "inode": stat.st_ino,
                        "offset": stat.st_size + 1,
                    }
                }
            }
            client, ticket = self.client(path, cp)
            with self.assertRaises(RuntimeError):
                client.collect(ticket["source_id"])
            self.assertEqual(client.request.call_count, 1)

    def test_recovery_claim_uses_recovery_operation_identity(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "jobs.jsonl"
            path.write_text(self.line())
            client, ticket = self.client(path)
            operation = str(uuid.uuid4())
            client.collect(ticket["source_id"], recovery_operation_id=operation)
            self.assertEqual(
                client.request.call_args_list[0].args[1]["recovery_operation_id"],
                operation,
            )
            self.assertEqual(
                client.request.call_args_list[1].args[1]["recovery_operation_id"],
                operation,
            )

    def test_adf_native_authority_is_qualified_not_display_name(self):
        cfg = {
            "subscription_id": "sub-1",
            "resource_group": "group",
            "factory_name": "factory",
        }
        self.assertEqual(
            adf_native_id(cfg, {"pipelineName": "job"}),
            "/subscriptions/sub-1/resourceGroups/group/providers/Microsoft.DataFactory/factories/factory/pipelines/job",
        )
        self.assertIsNone(adf_native_id(cfg, {"displayName": "job"}))
        self.assertIsNone(adf_native_id({}, {"pipelineName": "job"}))

    def test_nested_fixture_labels_cannot_certify_runtime(self):
        from app.data_pipelines.service import is_sample_evidence

        self.assertTrue(
            is_sample_evidence(
                {
                    "evidence": {
                        "raw_record": {
                            "redacted_json": json.dumps(
                                {"evidence_origin": "CONTROLLED_FIXTURE"}
                            )
                        }
                    }
                }
            )
        )
        self.assertTrue(
            is_sample_evidence({"fixture_state": "HYPOTHETICAL_PREVERIFIED_PROFILE"})
        )
        self.assertFalse(
            is_sample_evidence({"event": {"message": "sample application output"}})
        )

    def test_secret_references_cannot_export_backend_or_other_customer_secrets(self):
        from app.data_pipelines.service import bounded

        customer, other = uuid.uuid4(), uuid.uuid4()
        for ref in [
            "env:DATABASE_URL",
            "env:OPSCONTROL_AGENT_ACCESS_TOKEN",
            "env:OPSCONTROL_PIPELINE_SECRET_" + other.hex.upper() + "_TOKEN",
        ]:
            with self.assertRaises(PipelineError):
                bounded({"credential_ref": ref}, organization_id=customer)
        allowed = "env:OPSCONTROL_PIPELINE_SECRET_" + customer.hex.upper() + "_TOKEN"
        self.assertEqual(
            bounded({"credential_ref": allowed}, organization_id=customer)[
                "credential_ref"
            ],
            allowed,
        )

    def test_glue_uses_verified_account_and_partition_before_job_collection(self):
        from unittest.mock import patch
        from app.data_pipelines.bridge import collect_method
        from app.pipeline_adapters import PLATFORM_ADAPTERS
        from app.pipeline_adapters.core import AdapterError

        organization = uuid.uuid4()
        cfg = {
            "region": "cn-north-1",
            "profile_name": "opsc-pipeline-" + organization.hex + "-readonly",
        }
        integration = SimpleNamespace(platform="AWS_GLUE", organization_id=organization)
        method = SimpleNamespace(configuration={"method_type": "PLATFORM_API"})
        connection = SimpleNamespace(configuration=cfg)
        arn = "arn:aws-cn:glue:cn-north-1:000000000001:job/example"
        jobs = [SimpleNamespace(native_id=arn)]
        session = Mock()
        session.client.return_value.get_caller_identity.return_value = {
            "Account": "000000000001"
        }
        session.get_partition_for_region.return_value = "aws-cn"
        adapter = Mock()
        adapter.collect_with_retry.return_value = SimpleNamespace(
            events=[], checkpoint={"id": 1}, complete=True
        )
        factory = Mock(return_value=adapter)
        with patch("boto3.Session", return_value=session), patch.dict(
            PLATFORM_ADAPTERS, {"AWS_GLUE": factory}
        ):
            _, cursor, complete = collect_method(
                integration, method, connection, jobs, {}, {"account": "000000000001"}
            )
            self.assertTrue(complete)
            self.assertEqual(factory.call_args.args[0]["job_name"], "example")
            self.assertEqual(cursor["jobs"][arn], {"id": 1})
            with self.assertRaises(AdapterError):
                collect_method(
                    integration,
                    method,
                    connection,
                    jobs,
                    {},
                    {"account": "000000000002"},
                )

    def test_override_cannot_change_destination_without_canonical_handoff(self):
        from app.data_pipelines.service import validate_reader_target

        identity = {
            "platform": "AIRFLOW",
            "endpoint": "https://airflow.example.test",
            "account": "declared-account",
            "physical_scope": "dags",
        }
        validate_reader_target(
            "AIRFLOW", "PLATFORM_API", identity, {"base_url": identity["endpoint"]}
        )
        with self.assertRaises(PipelineError):
            validate_reader_target(
                "AIRFLOW",
                "PLATFORM_API",
                identity,
                {"base_url": "https://other.example.test"},
            )

    def test_name_is_never_a_native_identity(self):
        fact = {
            "event": {"jobchain": "matching-name"},
            "evidence": {
                "raw_record": {
                    "redacted_json": json.dumps({"taskName": "matching-name"})
                }
            },
        }
        self.assertIsNone(native_identity("IICS", fact))
        self.assertEqual(
            native_identity("IICS", fact, "verified-task-id"), "verified-task-id"
        )
        fact["evidence"]["raw_record"]["redacted_json"] = json.dumps(
            {"taskId": "other-task"}
        )
        self.assertIsNone(native_identity("IICS", fact, "verified-task-id"))

    def test_windows_paths_canonicalize_but_distinct_patterns_remain_separate(self):
        host = str(uuid.uuid4())
        a = canonical(
            "FILE_LOG",
            {
                "host_resource_id": host.upper(),
                "path": "C:\\Logs\\*.JSONL",
                "os": "Windows",
            },
        )
        b = canonical(
            "FILE_LOG",
            {"host_resource_id": host, "path": "c:/logs/*.jsonl", "os": "Windows"},
        )
        c = canonical(
            "FILE_LOG",
            {"host_resource_id": host, "path": "c:/logs/job*.jsonl", "os": "Windows"},
        )
        self.assertEqual(a, b)
        self.assertNotEqual(a[1], c[1])

    def test_checkpoint_outside_pattern_or_negative_position_is_rejected(self):
        source = SimpleNamespace(
            method_type="FILE_LOG", identity={"path": "/logs/*.jsonl", "os": "Linux"}
        )
        for path, position in [("/private/other.jsonl", 0), ("/logs/jobs.jsonl", -1)]:
            with self.assertRaises(PipelineError):
                validate_checkpoint(
                    source,
                    {"sources": {path: {"device": 1, "inode": 1, "offset": position}}},
                )

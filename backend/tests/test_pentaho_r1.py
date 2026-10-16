"""Deterministic R1 read-only contracts. None are genuine provider acceptance."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import app.main  # noqa: F401 - register shared model/security relationships
from fastapi import HTTPException
import uuid
from app.pipeline_adapters import PLATFORM_ADAPTERS, validate_platform_configuration
from app.pipeline_adapters.core import AdapterError
from app.pipeline_adapters.native import Pentaho
from app.pipeline_adapters.pentaho_observations import (
    context,
    normalize_observation,
    scoped_identity,
    proof_matches,
)
from app.pipeline_adapters.pentaho_carte import parse_status, xml, collect, reader
from app.data_pipelines.bridge import collect_method
from app.data_pipelines.service import validate_reader_target, PipelineError
from app.data_pipelines.agent_api import bound

START = "2026-10-16T01:00:00+00:00"
END = "2026-10-16T01:01:00+00:00"
HOST = "4d24797e-fd9b-4d8b-b5e3-9478aca07687"


def scope(surface="KITCHEN_PAN", **changes):
    return {
        "version": 1,
        "surface": surface,
        "exact_build": "10.2.0.0-222",
        "authority_id": "controlled-authority",
        "environment": "TEST",
        "workload_kind": "JOB",
        "native_job_id": "repository-guid-1",
        "host_resource_id": HOST,
        **({"restart_epoch": "controlled-epoch-1"} if surface == "CARTE" else {}),
        **changes,
    }


def observation(cfg=None, **changes):
    cfg = cfg or scope()
    return {
        **cfg,
        "native_execution_id": "native-run-1",
        "observation_id": "observation-1",
        "observed_at": END,
        "invocation_id": "native-run-1",
        "process_start": START,
        "executable_kind": "KITCHEN",
        "executable_sha256": "c" * 64,
        "os": "Linux",
        "state": "PROCESS_STARTED",
        **changes,
    }


def server_record(authority="EXECUTION_HISTORY", **changes):
    return {
        **scope("PENTAHO_SERVER"),
        "native_execution_id": "native-run-1",
        "observation_id": "observation-1",
        "observed_at": END,
        "authority": authority,
        "source_evidence_sha256": "a" * 64,
        "status": "SUCCESS",
        "started_at": START,
        "ended_at": END,
        **changes,
    }


def carte_config(**changes):
    return {
        "url": "https://carte.example.test/kettle",
        "job_name": "display name",
        "execution_id": "r&1",
        "allowed_hosts": ["carte.example.test"],
        "allowed_cidrs": ["192.0.2.0/24"],
        "monitoring_context": scope("CARTE"),
        **changes,
    }


def status_xml(kind="jobstatus", errors="0", state="Finished", identity="r&amp;1"):
    error = "" if errors is None else "<nr_errors>" + errors + "</nr_errors>"
    return (
        f"<{kind}><id>{identity}</id><status_desc>{state}</status_desc>"
        + error
        + f"</{kind}>"
    ).encode()


class PentahoR1Tests(unittest.TestCase):
    def test_cli_start_and_exit_do_not_invent_completion(self):
        start = normalize_observation(observation(pid=22), scope(), "customer-a")
        self.assertEqual(start["event"]["status"], "RUNNING")
        for exit_code in (0, 1):
            fact = normalize_observation(
                observation(state="PROCESS_EXITED", exit_code=exit_code),
                scope(),
                "customer-a",
            )
            self.assertEqual(fact["event"]["status"], "UNKNOWN")
            self.assertIsNone(fact["event"]["ended_at"])
            self.assertFalse(fact["event"]["terminal_status_observed"])

    def test_cli_bound_native_result_is_locally_normalized(self):
        result = {
            "invocation_id": "native-run-1",
            "source": "NATIVE_STRUCTURED_LOG",
            "evidence_sha256": "b" * 64,
            "status": "FAILED",
            "ended_at": END,
        }
        fact = normalize_observation(
            observation(state="EXECUTION_RESULT", result=result), scope(), "customer-a"
        )
        self.assertEqual(fact["event"]["status"], "FAILED")
        self.assertEqual(fact["event"]["ended_at"], END)
        self.assertFalse(fact["evidence"]["runtime_certified"])
        with self.assertRaises(AdapterError):
            normalize_observation(
                observation(
                    state="EXECUTION_RESULT",
                    result={**result, "invocation_id": "other"},
                ),
                scope(),
                "customer-a",
            )

    def test_pid_name_and_close_timestamps_are_not_identity(self):
        first = normalize_observation(observation(pid=9), scope(), "customer-a")
        again = normalize_observation(observation(pid=99), scope(), "customer-a")
        self.assertEqual(first["event"]["execution_id"], again["event"]["execution_id"])
        later = normalize_observation(
            observation(process_start=END), scope(), "customer-a"
        )
        self.assertNotEqual(
            first["event"]["execution_id"], later["event"]["execution_id"]
        )
        for changes in (
            {"process_start": None},
            {"invocation_id": None},
            {"native_execution_id": None},
        ):
            with self.subTest(changes=changes), self.assertRaises(AdapterError):
                normalize_observation(observation(**changes), scope(), "customer-a")

    def test_identity_scopes_customer_authority_environment_workload_epoch(self):
        cfg = scope("CARTE")
        base = scoped_identity("customer-a", cfg, "same-native-id")
        self.assertNotEqual(base, scoped_identity("customer-b", cfg, "same-native-id"))
        for key, value in {
            "authority_id": "other",
            "environment": "QA",
            "workload_kind": "TRANSFORMATION",
            "native_job_id": "other",
            "restart_epoch": "epoch-2",
        }.items():
            with self.subTest(field=key):
                self.assertNotEqual(
                    base,
                    scoped_identity(
                        "customer-a", {**cfg, key: value}, "same-native-id"
                    ),
                )

    def test_scope_mismatch_and_unsupported_agent_os_are_rejected(self):
        for field, value in {
            "authority_id": "other",
            "environment": "QA",
            "native_job_id": "other",
            "exact_build": "11.0.0.0-1",
            "host_resource_id": "other",
            "os": "Other",
        }.items():
            with self.subTest(field=field), self.assertRaises(AdapterError):
                normalize_observation(
                    observation(**{field: value}), scope(), "customer-a"
                )

    def test_pan_and_windows_remain_distinct_from_kitchen(self):
        cfg = scope(workload_kind="TRANSFORMATION")
        record = observation(cfg, executable_kind="PAN", os="Windows")
        self.assertEqual(
            normalize_observation(record, cfg, "a")["event"]["workload_kind"],
            "TRANSFORMATION",
        )
        with self.assertRaises(AdapterError):
            normalize_observation({**record, "executable_kind": "KITCHEN"}, cfg, "a")

    def test_raw_command_credentials_are_never_persisted(self):
        fact = normalize_observation(
            observation(argv=["kitchen.sh", "-pass", "controlled-sensitive-argument"]),
            scope(),
            "a",
        )
        serialized = json.dumps(fact)
        self.assertNotIn("controlled-sensitive-argument", serialized)
        self.assertNotIn('"argv"', serialized)
        self.assertIn("command_evidence", serialized)
        with self.assertRaises(AdapterError):
            normalize_observation(
                observation(command_line="not permitted"), scope(), "a"
            )

    def test_server_scheduler_and_repository_never_assert_execution_success(self):
        for authority in ("SCHEDULER", "REPOSITORY"):
            fact = normalize_observation(
                server_record(authority), scope("PENTAHO_SERVER"), "a"
            )
            self.assertEqual(fact["event"]["status"], "UNKNOWN")
            self.assertIsNone(fact["native_job_id"])
            self.assertIsNone(fact["event"]["ended_at"])
        native = normalize_observation(server_record(), scope("PENTAHO_SERVER"), "a")
        self.assertEqual(native["event"]["status"], "SUCCESS")
        self.assertEqual(native["native_job_id"], "repository-guid-1")

    def test_server_unknown_authority_missing_hash_and_universal_endpoint_fail_closed(
        self,
    ):
        for changes in ({"authority": "UNKNOWN"}, {"source_evidence_sha256": None}):
            with self.subTest(changes=changes), self.assertRaises(AdapterError):
                normalize_observation(
                    server_record(**changes), scope("PENTAHO_SERVER"), "a"
                )
        for surface in ("KITCHEN_PAN", "PENTAHO_SERVER"):
            adapter = Pentaho({"monitoring_context": scope(surface)}, customer_id="a")
            with self.assertRaises(AdapterError) as caught:
                adapter.collect()
            self.assertEqual(caught.exception.kind, "UNSUPPORTED_CAPABILITY")

    def test_unknown_build_family_and_schema_versions_fail_closed(self):
        for build in ("unknown", "10.2.x", "11.0.x", "10.2", "10.2.0.0-*"):
            with self.subTest(build=build), self.assertRaises(AdapterError):
                context(scope(exact_build=build))
        with self.assertRaises(AdapterError):
            context(scope(version=True))
        with self.assertRaises(AdapterError):
            normalize_observation(observation(version=2), scope(), "a")
        with self.assertRaises(AdapterError):
            context({**scope(), "start_endpoint": "/kettle/startJob"})

    def test_carte_parses_job_and_transformation_without_certification(self):
        for kind, workload in (("jobstatus", "JOB"), ("transstatus", "TRANSFORMATION")):
            cfg = scope("CARTE", workload_kind=workload)
            record = parse_status(status_xml(kind), cfg, "r&1", END)
            fact = normalize_observation(record, cfg, "a")
            self.assertEqual(fact["event"]["status"], "SUCCESS")
            self.assertFalse(fact["evidence"]["runtime_certified"])
            self.assertIsNone(fact["event"]["ended_at"])
            self.assertTrue(fact["event"]["terminal_status_observed"])

    def test_carte_missing_errors_unknown_and_stopped_never_become_success(self):
        for errors, state in (
            (None, "Finished"),
            ("0", "Stopped"),
            ("0", "not running"),
            ("0", "brand new state"),
        ):
            record = parse_status(
                status_xml(errors=errors, state=state), scope("CARTE"), "r&1", END
            )
            self.assertEqual(record["status"], "UNKNOWN")
        self.assertEqual(
            parse_status(status_xml(errors="1"), scope("CARTE"), "r&1", END)["status"],
            "FAILED",
        )

    def test_carte_wrong_native_id_epoch_and_workload_rejected(self):
        with self.assertRaises(AdapterError):
            parse_status(status_xml(identity="other"), scope("CARTE"), "r&1", END)
        with self.assertRaises(AdapterError):
            parse_status(status_xml("transstatus"), scope("CARTE"), "r&1", END)
        record = parse_status(status_xml(), scope("CARTE"), "r&1", END)
        with self.assertRaises(AdapterError):
            normalize_observation(
                {**record, "restart_epoch": "old-epoch"}, scope("CARTE"), "a"
            )

    def test_unsafe_xml_oversize_dtd_entities_and_alternate_encoding_rejected(self):
        for body in (
            b"x" * 65537,
            b'<!DOCTYPE jobstatus [<!ENTITY x "boom">]><jobstatus>&x;</jobstatus>',
            "<!DOCTYPE x><x/>".encode("utf-16"),
            b"<broken>",
            b"\xff",
        ):
            with self.subTest(prefix=repr(body[:15])), self.assertRaises(AdapterError):
                xml(body)

    def test_carte_inventory_is_advisory_and_not_complete_persistent_discovery(self):
        get = Mock(return_value=b"<unrelated/>")
        with patch(
            "app.pipeline_adapters.pentaho_carte.reader", return_value=(get, ())
        ):
            with self.assertRaises(AdapterError):
                collect(carte_config(execution_id=None), {}, "a")
            get.return_value = b"<server_status><job_status><jobname>name</jobname><id>r</id></job_status></server_status>"
            batch = collect(carte_config(execution_id=None), {"cursor": 1}, "a")
        self.assertEqual(batch.events, [])
        self.assertFalse(batch.complete)
        self.assertFalse(batch.evidence["persistent_inventory_authoritative"])
        self.assertEqual(batch.checkpoint, {"cursor": 1})

    def test_carte_only_fixed_get_status_paths_and_safe_escaped_parameters(self):
        for workload, path in (
            ("JOB", "/kettle/jobStatus/"),
            ("TRANSFORMATION", "/kettle/transStatus/"),
        ):
            cfg = carte_config(
                monitoring_context=scope("CARTE", workload_kind=workload)
            )
            get = Mock(
                return_value=status_xml(
                    "jobstatus" if workload == "JOB" else "transstatus"
                )
            )
            with patch(
                "app.pipeline_adapters.pentaho_carte.reader", return_value=(get, ())
            ):
                batch = collect(cfg, {}, "customer-a")
            self.assertEqual(get.call_args.args[0], path)
            self.assertIn("id=r%261", get.call_args.args[1])
            self.assertEqual(
                batch.events[0]["native_job_id"],
                cfg["monitoring_context"]["native_job_id"],
            )
            self.assertFalse(batch.evidence["runtime_verified"])

    def test_reader_enforces_local_policy_tls_auth_and_control_endpoint_deny(self):
        cfg = carte_config()
        env = {
            "OPSCONTROL_LOCAL_ALLOWED_HOSTS": "carte.example.test",
            "OPSCONTROL_LOCAL_ALLOWED_CIDRS": "192.0.2.0/24",
        }
        transport = Mock(return_value=(200, b"<server_status/>"))
        with patch.dict("os.environ", env), patch(
            "app.worker.egress.resolve_target", return_value="192.0.2.1"
        ):
            get, _ = reader(cfg, transport)
            with self.assertRaises(AdapterError):
                get("/kettle/startJob/", "")
            transport.assert_not_called()
            self.assertEqual(get("/kettle/status/", "xml=Y"), b"<server_status/>")
            transport.return_value = (403, b"denied")
            with self.assertRaises(AdapterError) as caught:
                get("/kettle/status/", "xml=Y")
            self.assertEqual(caught.exception.kind, "AUTHENTICATION")
        with patch.dict(
            "os.environ",
            {
                "OPSCONTROL_LOCAL_ALLOWED_HOSTS": "",
                "OPSCONTROL_LOCAL_ALLOWED_CIDRS": "",
            },
        ):
            with self.assertRaises(AdapterError):
                reader(cfg, transport)

    def test_carte_unbound_customer_cannot_collect(self):
        with self.assertRaises(AdapterError):
            Pentaho(carte_config()).collect()

    def test_context_validation_is_additive_legacy_and_other_eight_unchanged(self):
        cfg = carte_config()
        self.assertEqual(validate_platform_configuration("PENTAHO", cfg), cfg)
        legacy = {k: v for k, v in cfg.items() if k != "monitoring_context"}
        self.assertEqual(validate_platform_configuration("PENTAHO", legacy), legacy)
        self.assertEqual(len(set(PLATFORM_ADAPTERS) - {"PENTAHO"}), 8)
        for name, cls in PLATFORM_ADAPTERS.items():
            if name != "PENTAHO":
                self.assertNotIn("monitoring_context", cls.fields)

    def test_surface_method_and_host_cannot_bypass_canonical_identity(self):
        cfg = {"monitoring_context": scope()}
        validate_reader_target("PENTAHO", "FILE_LOG", {"host_resource_id": HOST}, cfg)
        for method, identity in (
            ("PLATFORM_API", {"endpoint": "https://carte.example.test"}),
            ("FILE_LOG", {"host_resource_id": "other"}),
        ):
            with self.subTest(method=method), self.assertRaises(PipelineError):
                validate_reader_target("PENTAHO", method, identity, cfg)

    def test_exact_build_surface_proof_is_additional_not_static_certification(self):
        cfg = scope()
        proof = SimpleNamespace(
            payload={
                "evidence": {
                    "surface": "KITCHEN_PAN",
                    "exact_build": cfg["exact_build"],
                }
            }
        )
        profile = SimpleNamespace(platform_version=cfg["exact_build"])
        self.assertTrue(proof_matches(cfg, profile, proof))
        self.assertFalse(
            proof_matches(cfg, SimpleNamespace(platform_version="10.2.x"), proof)
        )
        self.assertFalse(
            proof_matches(
                cfg,
                profile,
                SimpleNamespace(payload={"evidence": {"surface": "CARTE"}}),
            )
        )
        self.assertFalse(proof_matches(cfg, profile, None))

    def test_customer_bound_bridge_passes_scope_before_native_routing(self):
        cfg = carte_config()
        adapter = Mock()
        adapter.collect_with_retry.return_value = SimpleNamespace(
            events=[], checkpoint={}, complete=False
        )
        with patch.dict(PLATFORM_ADAPTERS, {"PENTAHO": Mock(return_value=adapter)}):
            factory = PLATFORM_ADAPTERS["PENTAHO"]
            collect_method(
                SimpleNamespace(
                    platform="PENTAHO", organization_id="customer-a", environment="TEST"
                ),
                SimpleNamespace(configuration={"method_type": "PLATFORM_API"}),
                SimpleNamespace(configuration=cfg),
                [],
                {},
            )
            factory.assert_called_once_with(cfg, customer_id="customer-a")

    def test_unauthenticated_or_other_customer_agent_is_rejected(self):
        db = Mock()
        with patch(
            "app.data_pipelines.agent_api.authenticate",
            side_effect=HTTPException(401),
        ):
            with self.assertRaises(HTTPException) as caught:
                bound(db, Mock(), "source-id")
            self.assertEqual(caught.exception.status_code, 401)
            db.get.assert_not_called()

        agent, collector = SimpleNamespace(
            organization_id=uuid.uuid4()
        ), SimpleNamespace(id=uuid.uuid4())
        source = SimpleNamespace(
            organization_id=uuid.uuid4(),
            method_type="FILE_LOG",
            identity={"host_resource_id": str(uuid.uuid4())},
        )
        db.get.side_effect = [
            source,
            SimpleNamespace(primary_collector_id=collector.id, domain="VM"),
        ]
        with patch(
            "app.data_pipelines.agent_api.authenticate",
            return_value=(agent, collector, None, None),
        ):
            with self.assertRaises(HTTPException) as caught:
                bound(db, Mock(), "source-id")
            self.assertEqual(caught.exception.status_code, 404)

    def test_carte_unchanged_status_does_not_repeat_evidence_and_epoch_continuity_fails_closed(
        self,
    ):
        get = Mock(return_value=status_xml())
        with patch(
            "app.pipeline_adapters.pentaho_carte.reader", return_value=(get, ())
        ):
            first = collect(carte_config(), {}, "a")
            second = collect(carte_config(), first.checkpoint, "a")
            self.assertEqual(len(first.events), 1)
            self.assertEqual(second.events, [])
            self.assertEqual(first.checkpoint, second.checkpoint)
            with self.assertRaises(AdapterError) as caught:
                collect(carte_config(), {"restart_epoch": "old-epoch"}, "a")
            self.assertEqual(caught.exception.kind, "CONTINUITY")

    def test_carte_tls_failure_is_structured_and_body_not_logged(self):
        import ssl

        env = {
            "OPSCONTROL_LOCAL_ALLOWED_HOSTS": "carte.example.test",
            "OPSCONTROL_LOCAL_ALLOWED_CIDRS": "192.0.2.0/24",
        }
        with patch.dict("os.environ", env), patch(
            "app.worker.egress.resolve_target", return_value="192.0.2.1"
        ):
            get, _ = reader(
                carte_config(),
                Mock(side_effect=ssl.SSLCertVerificationError("private diagnostic")),
            )
            with self.assertRaises(AdapterError) as caught:
                get("/kettle/status/", "xml=Y")
            self.assertEqual(caught.exception.kind, "TLS")
            self.assertNotIn("private diagnostic", str(caught.exception))

    def test_executable_and_scheduler_provenance_without_retry_grouping(self):
        original = normalize_observation(observation(), scope(), "a")
        scheduler = {
            "authority_id": "scheduler-a",
            "native_run_id": "scheduler-run-9",
            "native_attempt_id": "attempt-2",
        }
        fact = normalize_observation(
            observation(scheduler_identity=scheduler), scope(), "a"
        )
        self.assertEqual(
            fact["event"]["execution_id"], original["event"]["execution_id"]
        )
        self.assertEqual(
            fact["evidence"]["native_observation"]["scheduler_identity"], scheduler
        )
        for changes in (
            {"executable_sha256": None},
            {"scheduler_identity": {"authority_id": "a", "command": "unapproved"}},
        ):
            with self.assertRaises(AdapterError):
                normalize_observation(observation(**changes), scope(), "a")

    def test_runtime_profile_api_rejects_wrong_build_before_marking_certified(self):
        from app.data_pipelines.api import verify_profile, ProfileVerification

        generation = uuid.uuid4()
        profile = SimpleNamespace(
            platform_version="11.0.0.0-1",
            evidence_status="DOCUMENTED",
            compatibility="UNVERIFIED",
        )
        evidence = SimpleNamespace(
            id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            generation=generation,
            outcome="ACCEPTED",
            created_at=__import__("datetime").datetime.fromisoformat(START),
            payload={
                "runtime_origin": "AUTHENTICATED_RUNTIME",
                "reader_definition_hash": "reader-hash",
                "evidence": {"surface": "CARTE", "exact_build": "10.2.0.0-222"},
            },
        )
        method = SimpleNamespace(connection_id=uuid.uuid4(), configuration={})
        db = Mock()
        db.scalars.return_value = [method]
        db.scalar.return_value = SimpleNamespace(
            actor_id=uuid.uuid4(), reviewer_id=uuid.uuid4()
        )
        db.get.return_value = SimpleNamespace(
            configuration={"monitoring_context": scope("CARTE")}
        )
        with patch(
            "app.data_pipelines.api.checked", side_effect=[profile, evidence]
        ), patch("app.data_pipelines.api.require_admin"), patch(
            "app.data_pipelines.api.actor",
            return_value=SimpleNamespace(user_id=uuid.uuid4()),
        ), patch(
            "app.data_pipelines.api.s.is_sample_evidence", return_value=False
        ), patch(
            "app.data_pipelines.api.s.locked_source",
            return_value=SimpleNamespace(generation=generation),
        ), patch(
            "app.data_pipelines.api.s.reader_definition", return_value="reader-hash"
        ):
            with self.assertRaises(HTTPException) as caught:
                verify_profile(
                    uuid.uuid4(),
                    ProfileVerification(
                        idempotency_key="controlled-proof-test",
                        evidence_id=evidence.id,
                        compatibility="SUPPORTED",
                        confirmed=True,
                    ),
                    db,
                )
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(
            caught.exception.detail["code"], "PENTAHO_BUILD_SURFACE_PROOF_REQUIRED"
        )
        self.assertEqual(profile.evidence_status, "DOCUMENTED")

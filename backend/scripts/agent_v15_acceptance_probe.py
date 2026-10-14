"""Actual HTTP/DB Agent contracts in an explicitly disposable ARCH test fixture.

No assertions infer genuine host health from this labeled synthetic observation.
Run after the owned Agent runtime test so revocation cannot interrupt that test.
"""

import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select
from app.main import app  # Register security and scoped model contracts.
from app.core.config import settings
from app.db.session import SessionLocal
from app.security.http import token_digest
from app.security.models import SecurityAuditEvent, WorkerIdentity
from app.telemetry.models import AgentRegistration, ManagedAgent, TelemetryReceipt


def run(fixture, call):
    if (
        settings.environment != "test"
        or os.getenv("OPSCONTROL_ARCH001_ACCEPTANCE") != "1"
    ):
        raise RuntimeError(
            "Agent acceptance requires the owned disposable test environment"
        )
    admin = fixture["token"]
    label = uuid.uuid4().hex[:12]
    hostname = f"agent-contract-{label}.example.test"
    resource = call(
        "/api/v1/unified/resources/vm",
        "POST",
        {
            "name": "Controlled Agent contract " + label,
            "hostname": hostname,
            "address": hostname,
            "environment": "SANDBOX",
            "os_type": "Linux",
            "organization_id": fixture["other"],
            "native_os_metrics": False,
        },
        admin,
        201,
    )
    collector_id = resource["primary_collector_id"]
    prefix = "/api/v1/agent-control/collectors/" + collector_id
    method = call(
        prefix + "/methods",
        "POST",
        {
            "name": "Controlled selected signals",
            "method_type": "OTLP_RECEIVER",
            "configuration": {"signals": ["Logs", "Metrics"], "port": 15437},
        },
        admin,
        201,
    )
    version = call(prefix + "/versions", "POST", token=admin, expected=201)
    assert (
        version["validation_status"] == "VALIDATED"
    ), "Real Contrib validation required"
    reader = call(
        "/api/v1/auth/login",
        "POST",
        {"username": "arch001-reader", "password": fixture["password"]},
    )["access_token"]
    call(prefix, token=reader, expected=404)
    call(prefix + "/registration", "POST", token=reader, expected=403)
    call(
        "/api/v1/agent/heartbeat",
        "POST",
        {"version": "1.5.0", "runtime_version": "0.123.0", "health": "STOPPED"},
        expected=401,
    )

    def enrollment():
        return call(prefix + "/registration", "POST", token=admin, expected=201)

    def register_body(enroll):
        return {
            "enrollment_token": enroll["enrollment_token"],
            "hostname": hostname,
            "os_type": "Linux",
            "version": "1.5.0",
            "runtime_version": "0.123.0",
        }

    expired = enrollment()
    with SessionLocal() as db:
        row = db.scalar(
            select(AgentRegistration).where(
                AgentRegistration.token_hash
                == token_digest(expired["enrollment_token"])
            )
        )
        assert str(row.collector_id) == collector_id
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    call("/api/v1/agent/register", "POST", register_body(expired), expected=401)
    issued = enrollment()
    wrong_os = register_body(issued)
    wrong_os["os_type"] = "Windows"
    call("/api/v1/agent/register", "POST", wrong_os, expected=422)
    invalid = register_body(issued)
    invalid["runtime_version"] = "0.0.0"
    call("/api/v1/agent/register", "POST", invalid, expected=422)
    identity = call(
        "/api/v1/agent/register", "POST", register_body(issued), expected=201
    )
    credential = identity["access_token"]
    call("/api/v1/agent/register", "POST", register_body(issued), expected=401)
    call(prefix + "/registration", "POST", token=admin, expected=409)
    call(prefix, token=credential, expected=401)
    before = datetime.fromisoformat(identity["expires_at"])
    renewed = call("/api/v1/agent/credentials/renew", "POST", {}, credential)
    assert datetime.fromisoformat(renewed["expires_at"]) >= before
    assert renewed["agent_id"] == identity["agent_id"]
    call(
        prefix + "/apply",
        "POST",
        {"revision": version["revision"], "approve": True},
        admin,
    )
    downloaded = call("/api/v1/agent/configuration", token=credential)
    assert downloaded["sha256"] == version["sha256"]
    status = call(prefix, token=admin)["agent"]
    assert status["downloaded_revision"] == version["revision"]
    assert status["verified_revision"] is None
    heartbeat = {
        "version": "1.5.0",
        "runtime_version": "0.123.0",
        "applied_revision": version["revision"],
        "configuration_sha256": version["sha256"],
        "health": "RUNNING",
    }
    wrong = {**heartbeat, "configuration_sha256": "0" * 64}
    call("/api/v1/agent/heartbeat", "POST", wrong, credential, 409)
    wrong = {**heartbeat, "applied_revision": version["revision"] + 100}
    call("/api/v1/agent/heartbeat", "POST", wrong, credential, 409)
    call("/api/v1/agent/heartbeat", "POST", heartbeat, credential)
    assert call(prefix, token=admin)["agent"]["verified_revision"] is None
    foreign_collector = fixture["vm_resource"]["primary_collector_id"]
    foreign_methods = call(
        "/api/v1/agent-control/collectors/" + foreign_collector, token=admin
    )["methods"]
    assert foreign_methods and foreign_collector != collector_id
    foreign_method = foreign_methods[0]["id"]
    forged = call(
        "/api/v1/agent/configuration?collector_id=" + foreign_collector,
        token=credential,
    )
    assert forged["collector_id"] == collector_id
    call("/api/v1/agent/credentials/renew", "POST", {}, admin, 401)
    observation = {
        "method_id": foreign_method,
        "state": "IDLE",
        "sources_found": 0,
        "sources_readable": 0,
    }
    call(
        "/api/v1/agent/heartbeat",
        "POST",
        {**heartbeat, "method_observations": [observation]},
        credential,
        422,
    )
    observation["method_id"] = method["id"]
    call(
        "/api/v1/agent/heartbeat",
        "POST",
        {**heartbeat, "method_observations": [observation, observation]},
        credential,
        422,
    )

    def metrics(method_id, timestamp):
        return {
            "resourceMetrics": [
                {
                    "scopeMetrics": [
                        {
                            "metrics": [
                                {
                                    "name": "opscontrol.contract.observation",
                                    "unit": "1",
                                    "gauge": {
                                        "dataPoints": [
                                            {
                                                "timeUnixNano": str(timestamp),
                                                "asInt": "1",
                                                "attributes": [
                                                    {
                                                        "key": "opscontrol.method.id",
                                                        "value": {
                                                            "stringValue": method_id
                                                        },
                                                    },
                                                    {
                                                        "key": "evidence.origin",
                                                        "value": {
                                                            "stringValue": "CONTROLLED_AGENT_API_CONTRACT"
                                                        },
                                                    },
                                                ],
                                            }
                                        ]
                                    },
                                }
                            ]
                        }
                    ]
                }
            ]
        }

    call(
        "/api/v1/agent/otlp/v1/metrics",
        "POST",
        metrics(foreign_method, time.time_ns()),
        credential,
        422,
    )
    conflicting = metrics(method["id"], time.time_ns())
    conflicting["resourceMetrics"][0]["scopeMetrics"][0]["metrics"][0]["gauge"][
        "dataPoints"
    ][0]["attributes"].append(
        {"key": "opscontrol_method_id", "value": {"stringValue": foreign_method}}
    )
    call("/api/v1/agent/otlp/v1/metrics", "POST", conflicting, credential, 422)
    unselected_trace = {
        "resourceSpans": [
            {
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": uuid.uuid4().hex,
                                "spanId": uuid.uuid4().hex[:16],
                                "name": "Controlled rejected unselected signal",
                                "startTimeUnixNano": str(time.time_ns()),
                                "endTimeUnixNano": str(time.time_ns()),
                                "attributes": [
                                    {
                                        "key": "opscontrol.method.id",
                                        "value": {"stringValue": method["id"]},
                                    }
                                ],
                            }
                        ]
                    }
                ]
            }
        ]
    }
    call("/api/v1/agent/otlp/v1/traces", "POST", unselected_trace, credential, 422)
    payload = metrics(method["id"], time.time_ns())
    call("/api/v1/agent/otlp/v1/metrics", "POST", payload, credential)
    with SessionLocal() as db:
        receipt_count = db.scalar(
            select(func.count())
            .select_from(TelemetryReceipt)
            .where(TelemetryReceipt.agent_id == uuid.UUID(identity["agent_id"]))
        )
    call("/api/v1/agent/otlp/v1/metrics", "POST", payload, credential)
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(TelemetryReceipt)
                .where(TelemetryReceipt.agent_id == uuid.UUID(identity["agent_id"]))
            )
            == receipt_count
        )
    call("/api/v1/agent/heartbeat", "POST", heartbeat, credential)
    assert (
        call(prefix, token=admin)["agent"]["verified_revision"] is None
    ), "Partial metrics must not verify selected Logs"
    logs = {
        "resourceLogs": [
            {
                "scopeLogs": [
                    {
                        "logRecords": [
                            {
                                "timeUnixNano": str(time.time_ns()),
                                "body": {
                                    "stringValue": "Explicitly controlled Agent API acceptance observation "
                                    + label
                                },
                                "attributes": [
                                    {
                                        "key": "opscontrol.method.id",
                                        "value": {"stringValue": method["id"]},
                                    },
                                    {
                                        "key": "evidence.origin",
                                        "value": {
                                            "stringValue": "CONTROLLED_AGENT_API_CONTRACT"
                                        },
                                    },
                                ],
                            }
                        ]
                    }
                ]
            }
        ]
    }
    call("/api/v1/agent/otlp/v1/logs", "POST", logs, credential)
    acknowledgement = call(
        "/api/v1/agent/heartbeat",
        "POST",
        {**heartbeat, "method_observations": [observation]},
        credential,
    )
    assert acknowledgement["verified_revision"] == version["revision"]
    status = call(prefix, token=admin)["agent"]
    assert status["last_working_revision"] == version["revision"]
    assert "previous_token_hash" not in status and "token_hash" not in status

    rotated = call("/api/v1/agent/credentials/rotate", "POST", {}, credential)
    new_credential = rotated["access_token"]
    call("/api/v1/agent/heartbeat", "POST", heartbeat, credential)
    call("/api/v1/agent/heartbeat", "POST", heartbeat, new_credential)
    with SessionLocal() as db:
        agent = db.get(ManagedAgent, uuid.UUID(identity["agent_id"]))
        agent.previous_token_expires_at = datetime.now(timezone.utc) - timedelta(
            seconds=1
        )
        db.commit()
    call("/api/v1/agent/heartbeat", "POST", heartbeat, credential, 401)
    call("/api/v1/agent/heartbeat", "POST", heartbeat, new_credential)
    with SessionLocal() as db:
        agent = db.get(ManagedAgent, uuid.UUID(identity["agent_id"]))
        worker = db.get(WorkerIdentity, agent.worker_id)
        worker.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    call("/api/v1/agent/credentials/renew", "POST", {}, new_credential, 401)
    call(prefix + "/agent", "DELETE", token=admin, expected=204)
    call("/api/v1/agent/heartbeat", "POST", heartbeat, new_credential, 401)
    reenroll = enrollment()
    replacement = call(
        "/api/v1/agent/register", "POST", register_body(reenroll), expected=201
    )
    assert (
        replacement["agent_id"] == identity["agent_id"]
    ), "Re-enrollment preserves the logical Agent identity"
    call("/api/v1/agent/register", "POST", register_body(reenroll), expected=401)
    reset = call(prefix, token=admin)["agent"]
    assert reset["applied_revision"] is None and reset["verified_revision"] is None
    call("/api/v1/agent/heartbeat", "POST", heartbeat, new_credential, 401)
    call(
        "/api/v1/agent/heartbeat",
        "POST",
        {"version": "1.5.0", "runtime_version": "0.123.0", "health": "STOPPED"},
        replacement["access_token"],
    )
    with SessionLocal() as db:
        events = set(
            db.scalars(
                select(SecurityAuditEvent.event_type).where(
                    SecurityAuditEvent.target_id.in_(
                        [collector_id, identity["agent_id"]]
                    )
                )
            )
        )
    assert {
        "AGENT_REGISTER",
        "AGENT_CREDENTIAL_RENEW",
        "AGENT_CREDENTIAL_ROTATE",
        "AGENT_REVOKE",
        "AGENT_CONFIG_VERIFIED",
    } <= events
    # Retire this controlled Agent so the fixture does not imply an installed host.
    call(prefix + "/agent", "DELETE", token=admin, expected=204)
    report = {
        "status": "PASS",
        "origin": "CONTROLLED_AGENT_API_CONTRACT_OVER_ACTUAL_HTTP_DB",
        "enrollment_expiry_and_single_use": True,
        "renewal_rotation_expiry_revocation": True,
        "reenrollment_preserves_identity": True,
        "download_applied_verified_separate": True,
        "checksum_and_method_scopes_enforced": True,
        "unselected_signal_and_conflicting_method_aliases_rejected": True,
        "partial_receipts_not_verified": True,
        "batch_idempotency": True,
        "audit_events_verified": True,
        "production_modified": False,
        "genuine_host_health_claimed": False,
    }
    path = Path(os.environ["ARCH001_EVIDENCE_DIR"]) / "agent-v15.json"
    path.write_text(json.dumps(report, indent=2))
    return "Agent V1.5 actual API/DB enrollment, expiry, renewal/rotation/revocation, scope, checksum, receipts, deduplication and audit PASS"

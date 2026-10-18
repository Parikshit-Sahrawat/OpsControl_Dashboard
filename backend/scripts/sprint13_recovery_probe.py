"""Synthetic backup/restore probe; only run inside the owned V1.6 Docker harness."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.main  # noqa: F401 - register mapped FK targets
from app.data_pipelines import service as pipeline_service
from app.data_pipelines.models import PipelineEvidence, PipelineHold, PipelineSource
from app.models import (
    Collector,
    DataSource,
    ExecutionStatus,
    ExecutionType,
    IncidentActivity,
    JobOrder,
    JobOrderHistory,
    OperationalIncident,
    Organization,
)
from app.security.access_control import resolve_access
from app.security.access_models import (
    CustomerAccessGrant,
    Role,
    RolePermission,
    UserRoleAssignment,
)
from app.security.models import SecurityAuditEvent, User
from app.security.passwords import hash_password
from app.security.permission_catalog import PROVIDER_ID
from app.telemetry.models import CollectorMethod
from scripts import database_backup


def controlled_container() -> str:
    if (
        os.getenv("ENVIRONMENT") != "test"
        or os.getenv("OPSCONTROL_V16_ACCEPTANCE") != "1"
    ):
        raise RuntimeError("Owned test environment required")
    name = os.getenv("V16_OWNED_CONTAINER", "")
    if not name.startswith("opscontrol-v16-") or not os.getenv("V16_EVIDENCE_DIR"):
        raise RuntimeError("Owned V1.6 container and evidence directory required")
    url = make_url(os.environ["DATABASE_URL"])
    if (
        url.host != "127.0.0.1"
        or url.database != "opscontrol"
        or url.username != "opscontrol"
    ):
        raise RuntimeError("Only harness-owned loopback database permitted")
    return name


def docker(
    name: str, *args: str, input_data: bytes | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "exec", *(["-i"] if input_data is not None else []), name, *args],
        input=input_data,
        capture_output=True,
        check=True,
        timeout=180,
    )


@contextmanager
def service_file(name: str, url, folder: Path):
    path = folder / "pg_service.conf"
    target_name = "opscontrol_s13_restore_" + uuid.uuid4().hex[:10]
    body = "".join(
        f"[{service}]\nhost=127.0.0.1\nport=5432\nuser=opscontrol\npassword={url.password}\ndbname={database}\n"
        for service, database in (("source", "opscontrol"), ("target", target_name))
    )
    path.write_text(body)
    path.chmod(0o600)
    inside = "/tmp/opscontrol-s13-" + uuid.uuid4().hex + ".conf"
    subprocess.run(
        ["docker", "cp", str(path), name + ":" + inside],
        check=True,
        capture_output=True,
    )
    try:
        yield target_name, inside
    finally:
        docker(name, "rm", "-f", inside)


@contextmanager
def selected_service(service: str, inside: str):
    previous = (os.environ.get("PGSERVICE"), os.environ.get("PGSERVICEFILE"))
    os.environ["PGSERVICE"] = service
    os.environ["PGSERVICEFILE"] = inside
    try:
        yield database_backup.tools(os.environ["V16_OWNED_CONTAINER"])
    finally:
        for key, value in zip(("PGSERVICE", "PGSERVICEFILE"), previous):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def seed(source_engine) -> dict:
    token = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc)
    with Session(source_engine) as db:
        a = Organization(name="S13 A " + token, code="S13A-" + token, active=True)
        b = Organization(name="S13 B " + token, code="S13B-" + token, active=True)
        user = User(
            username="s13-" + token,
            full_name="Synthetic recovery operator",
            password_hash=hash_password("synthetic-recovery-password-" + token),
            active=True,
            service_provider_id=PROVIDER_ID,
        )
        db.add_all((a, b, user))
        db.flush()
        role = Role(
            service_provider_id=PROVIDER_ID,
            name="S13 view " + token,
            code="s13-" + token,
        )
        db.add(role)
        db.flush()
        db.add(RolePermission(role_id=role.id, permission_key="etl.view"))
        db.add(
            UserRoleAssignment(
                user_id=user.id, role_id=role.id, service_provider_id=PROVIDER_ID
            )
        )
        db.flush()
        db.add_all(
            (
                CustomerAccessGrant(
                    user_id=user.id,
                    role_id=role.id,
                    organization_id=a.id,
                    service_provider_id=PROVIDER_ID,
                ),
                CustomerAccessGrant(
                    user_id=user.id,
                    role_id=None,
                    organization_id=b.id,
                    effect="DENY",
                    service_provider_id=PROVIDER_ID,
                ),
            )
        )
        data_source = DataSource(
            organization_id=a.id, name="S13 source " + token, source_type="CONTROLLED"
        )
        db.add(data_source)
        db.flush()
        collector = Collector(
            data_source_id=data_source.id,
            name="S13 collector",
            collector_type="CONTROLLED",
        )
        db.add(collector)
        db.flush()
        method = CollectorMethod(
            organization_id=a.id,
            collector_id=collector.id,
            name="S13 method",
            method_type="METRICS",
            configuration={},
        )
        source = PipelineSource(
            organization_id=a.id,
            method_type="PLATFORM_API",
            canonical_key=uuid.uuid4().hex.ljust(64, "0"),
            identity={"physical_scope": "synthetic"},
            fence=7,
            owner_id=uuid.uuid4(),
            lease_until=now + timedelta(minutes=5),
            live_checkpoint={"cursor": 19},
            recovery_checkpoint={"cursor": 11},
            legacy_collector_id=collector.id,
        )
        db.add_all((method, source))
        db.flush()
        job = JobOrder(
            organization_id=a.id,
            name="S13 synthetic monitored job " + token,
            environment="TEST",
        )
        db.add(job)
        db.flush()
        history = JobOrderHistory(
            job_order_id=job.id,
            execution_type=ExecutionType.SCHEDULED,
            status=ExecutionStatus.UNKNOWN,
            provider_execution_id="synthetic-" + token,
            source_evidence={"synthetic": True, "verification": "restore_only"},
            started_at=now - timedelta(days=40),
        )
        db.add(history)
        db.flush()
        evidence = PipelineEvidence(
            organization_id=a.id,
            source_id=source.id,
            generation=source.generation,
            external_key="S13-synthetic-" + token,
            payload={"synthetic": True, "immutable_reference": token},
            outcome="ACCEPTED",
            observed_at=now - timedelta(days=40),
            created_at=now - timedelta(days=40),
        )
        incident = OperationalIncident(
            organization_id=a.id,
            episode_key="s13-" + token,
            source_kind="PIPELINE",
            source_reference="synthetic-" + token,
            history_id=history.id,
            title="Synthetic recovery incident",
            severity="P3",
            status="OPEN",
            condition_status="ACTIVE",
            opened_at=now,
        )
        db.add_all((evidence, incident))
        db.flush()
        activity = IncidentActivity(
            organization_id=a.id,
            incident_id=incident.id,
            event_type="CREATED",
            actor="synthetic",
            occurred_at=now,
            text="Controlled fixture",
        )
        audit = SecurityAuditEvent(
            event_type="S13_SYNTHETIC",
            actor_id=user.id,
            organization_id=a.id,
            target_type="incident",
            target_id=str(incident.id),
            outcome="ALLOWED",
        )
        db.add_all((activity, audit))
        hold = pipeline_service.hold(db, source.id, "LEGAL", "s13-" + token, user.id)
        db.commit()
        return {
            "a": a.id,
            "b": b.id,
            "user": user.id,
            "role": role.id,
            "data_source": data_source.id,
            "collector": collector.id,
            "method": method.id,
            "source": source.id,
            "evidence": evidence.id,
            "job": job.id,
            "history": history.id,
            "hold": hold.id,
            "incident": incident.id,
            "activity": activity.id,
            "audit": audit.id,
            "token": token,
        }


def snapshot(engine, ids: dict) -> dict:
    with Session(engine) as db:
        a = db.get(Organization, ids["a"])
        b = db.get(Organization, ids["b"])
        user = db.get(User, ids["user"])
        role = db.get(Role, ids["role"])
        grant = db.scalar(
            select(CustomerAccessGrant).where(
                CustomerAccessGrant.user_id == user.id,
                CustomerAccessGrant.organization_id == a.id,
            )
        )
        deny = db.scalar(
            select(CustomerAccessGrant).where(
                CustomerAccessGrant.user_id == user.id,
                CustomerAccessGrant.organization_id == b.id,
            )
        )
        data_source = db.get(DataSource, ids["data_source"])
        collector = db.get(Collector, ids["collector"])
        method = db.get(CollectorMethod, ids["method"])
        source = db.get(PipelineSource, ids["source"])
        evidence = db.get(PipelineEvidence, ids["evidence"])
        job = db.get(JobOrder, ids["job"])
        history = db.get(JobOrderHistory, ids["history"])
        hold = db.get(PipelineHold, ids["hold"])
        incident = db.get(OperationalIncident, ids["incident"])
        activity = db.get(IncidentActivity, ids["activity"])
        audit = db.get(SecurityAuditEvent, ids["audit"])
        principal = resolve_access(db, user)
        assert principal.allows("etl.view", a.id) and not principal.allows(
            "etl.view", b.id
        )
        return {
            "organizations": (str(a.id), str(b.id)),
            "user": (str(user.id), user.password_hash, user.active),
            "role": (str(role.id), role.active),
            "grants": (
                (str(grant.role_id), grant.effect),
                (str(deny.organization_id), deny.effect),
            ),
            "collector": (
                str(data_source.id),
                str(data_source.organization_id),
                str(collector.id),
                str(collector.data_source_id),
                str(method.id),
                str(method.collector_id),
                method.method_type,
            ),
            "source": (
                str(source.id),
                source.method_type,
                source.canonical_key,
                str(source.generation),
                source.fence,
                str(source.owner_id),
                str(source.lease_until),
                source.live_checkpoint,
                source.recovery_checkpoint,
                str(source.legacy_collector_id),
            ),
            "evidence": (
                str(evidence.source_id),
                str(evidence.generation),
                evidence.external_key,
                evidence.payload,
                evidence.outcome,
            ),
            "history": (
                str(job.organization_id),
                str(history.job_order_id),
                history.provider_execution_id,
                history.status.value,
                history.source_evidence,
            ),
            "hold": (
                str(hold.source_id),
                str(hold.actor_id),
                hold.kind,
                hold.reference,
                hold.released_at,
            ),
            "incident": (
                str(incident.organization_id),
                incident.episode_key,
                incident.status,
                str(incident.history_id),
                str(activity.incident_id),
                activity.event_type,
            ),
            "audit": (
                str(audit.actor_id),
                str(audit.organization_id),
                audit.target_id,
                audit.outcome,
            ),
            "effective_access": (
                principal.allows("etl.view", a.id),
                principal.allows("etl.view", b.id),
            ),
            "table_counts": {
                table: db.scalar(text("SELECT count(*) FROM " + table))
                for table in (
                    "organizations",
                    "users",
                    "roles",
                    "customer_access_grants",
                    "data_sources",
                    "collectors",
                    "collector_methods",
                    "pipeline_sources",
                    "pipeline_evidence",
                    "pipeline_holds",
                    "job_order_histories",
                    "operational_incidents",
                    "incident_activities",
                    "security_audit_events",
                )
            },
        }


def main() -> None:
    name = controlled_container()
    source_url = make_url(os.environ["DATABASE_URL"])
    source_engine = create_engine(source_url)
    ids = seed(source_engine)
    expected = snapshot(source_engine, ids)
    with tempfile.TemporaryDirectory(prefix="opscontrol-s13-") as private_name:
        private = Path(private_name)
        private.chmod(0o700)
        with service_file(name, source_url, private) as (target_name, inside):
            path = private / "controlled.dump"
            before_size = source_engine.connect()
            with before_size as conn:
                source_bytes = conn.scalar(
                    text("SELECT pg_database_size(current_database())")
                )
            start = time.monotonic()
            with selected_service("source", inside) as prefix:
                manifest = database_backup.backup(path, prefix)
            backup_seconds = time.monotonic() - start
            assert path.is_file() and manifest["bytes"] == path.stat().st_size
            with path.open("rb") as stream:
                listing = docker(name, "pg_restore", "--list", input_data=stream.read())
            assert (
                b"pipeline_holds" in listing.stdout
                and b"alembic_version" in listing.stdout
            )
            with source_engine.connect().execution_options(
                isolation_level="AUTOCOMMIT"
            ) as conn:
                conn.execute(text('CREATE DATABASE "' + target_name + '"'))
            target_url = source_url.set(database=target_name)
            target_engine = create_engine(target_url)
            start = time.monotonic()
            with selected_service("target", inside) as prefix:
                database_backup.restore(path, prefix)
            restore_seconds = time.monotonic() - start
            actual = snapshot(target_engine, ids)
            assert actual == expected, "Critical source/restored projections differ"
            restored_env = {
                **os.environ,
                "DATABASE_URL": target_url.render_as_string(hide_password=False),
            }
            backend_dir = Path(__file__).resolve().parents[1]
            drift = subprocess.run(
                [sys.executable, "-m", "alembic", "check"],
                cwd=backend_dir,
                env=restored_env,
                capture_output=True,
                text=True,
                timeout=120,
            )
            assert drift.returncode == 0, "Restored database has Alembic drift"
            downgrade = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alembic",
                    "downgrade",
                    "0031_in_app_notifications",
                ],
                cwd=backend_dir,
                env=restored_env,
                capture_output=True,
                text=True,
                timeout=120,
            )
            assert downgrade.returncode != 0 and any(
                marker in downgrade.stderr
                for marker in (
                    "V1.6 identities/evidence/checkpoints exist",
                    "Pentaho attempts/identity/evidence/recovery exist",
                    "Pentaho evidence review/decisions exist",
                    "Pentaho schedule/replay/notification evidence exists",
                    "Native incident recovery evidence exists",
                    "Access boundaries or decisions exist",
                )
            ), "Populated restored downgrade did not refuse with preservation guard"
            assert snapshot(target_engine, ids) == expected
            with Session(target_engine) as db:
                assert (
                    db.scalar(
                        text(
                            "SELECT count(*) FROM alembic_version WHERE version_num='0037_access_boundaries'"
                        )
                    )
                    == 1
                )
                target_bytes = db.scalar(
                    text("SELECT pg_database_size(current_database())")
                )
                db.add(
                    PipelineEvidence(
                        organization_id=ids["b"],
                        source_id=ids["source"],
                        generation=uuid.uuid4(),
                        external_key="wrong customer",
                        payload={},
                        outcome="ACCEPTED",
                        observed_at=datetime.now(timezone.utc),
                    )
                )
                try:
                    db.flush()
                except IntegrityError as exc:
                    assert exc.orig.diag.constraint_name == "fk_pipeline_evidence_scope"
                    db.rollback()
                else:
                    raise AssertionError("Cross-customer evidence accepted")
            with Session(target_engine) as db:
                old = db.get(PipelineEvidence, ids["evidence"])
                db.add(
                    PipelineEvidence(
                        organization_id=ids["a"],
                        source_id=ids["source"],
                        generation=old.generation,
                        external_key=old.external_key,
                        payload={},
                        outcome="ACCEPTED",
                        observed_at=datetime.now(timezone.utc),
                    )
                )
                try:
                    db.flush()
                except IntegrityError as exc:
                    assert (
                        exc.orig.diag.constraint_name == "uq_pipeline_evidence_identity"
                    )
                    db.rollback()
                else:
                    raise AssertionError("Duplicate evidence identity accepted")
            with Session(target_engine) as db:
                try:
                    pipeline_service.release_hold(db, ids["hold"], ids["user"])
                except pipeline_service.PipelineError as exc:
                    assert exc.code == "INDEPENDENT_LEGAL_RELEASE_REQUIRED"
                else:
                    raise AssertionError("Self-release of legal hold succeeded")
                db.rollback()
                pipeline_service.cleanup(db)
                db.commit()
                assert (
                    db.get(PipelineEvidence, ids["evidence"]).payload
                    == expected["evidence"][3]
                )
                assert db.get(PipelineHold, ids["hold"]).released_at is None
            bad = private / "invalid.dump"
            shutil.copyfile(path, bad)
            bad.write_bytes(bad.read_bytes() + b"corrupted")
            shutil.copyfile(
                path.with_suffix(".dump.json"), bad.with_suffix(".dump.json")
            )
            try:
                with selected_service("target", inside) as prefix:
                    database_backup.restore(bad, prefix)
            except ValueError as exc:
                assert str(exc) == "Backup checksum or format mismatch"
            else:
                raise AssertionError("Corrupt backup accepted")
            assert snapshot(target_engine, ids) == expected
            target_engine.dispose()
            # The harness will remove the entire private container and both databases.
            result = {
                "status": "PASS",
                "scenario_status": {f"REC-0{i}": "PASS" for i in range(1, 7)},
                "source_bytes": source_bytes,
                "restored_bytes": target_bytes,
                "backup_bytes": manifest["bytes"],
                "backup_sha256": manifest["sha256"],
                "backup_seconds": round(backup_seconds, 3),
                "restore_seconds": round(restore_seconds, 3),
                "migration_head": "0037_access_boundaries",
                "restored_alembic_drift": False,
                "restored_populated_downgrade_refused": True,
                "table_counts": expected["table_counts"],
                "critical_projection_equal": True,
                "corrupt_artifact_rejected": True,
                "production_rpo_rto_certified": False,
            }
            evidence_dir = Path(os.environ["V16_EVIDENCE_DIR"])
            evidence_dir.mkdir(parents=True, exist_ok=True)
            (evidence_dir / "sprint13-recovery.json").write_text(
                json.dumps(result, indent=2) + "\n"
            )
            print(json.dumps(result))
    source_engine.dispose()


if __name__ == "__main__":
    main()

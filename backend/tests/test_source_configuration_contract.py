"""Real PostgreSQL/HTTP enforcement, not mock-session certification."""

import hashlib
import json
import os
import secrets
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from app.db.session import SessionLocal
from app.models import (
    Organization,
    DataSource,
    MonitoringTemplate,
    MonitoringTemplateVersion,
    MonitoringTemplateAttachment,
)
from app.models.entities import SourceConfigurationRevision
from app.security.models import User, OrganizationMembership
from app.security.passwords import hash_password


@unittest.skipUnless(
    os.environ.get("S01_CONFIGURATION_ACCEPTANCE") == "1",
    "Owned migrated PostgreSQL and running HTTP required",
)
class SourceConfigurationContract(unittest.TestCase):
    def setUp(self):
        password = secrets.token_urlsafe(24)
        with SessionLocal() as db:
            org = Organization(name="Revision A " + uuid4().hex, code=uuid4().hex)
            other = Organization(name="Revision B " + uuid4().hex, code=uuid4().hex)
            admin = User(
                username="revision-admin-" + uuid4().hex,
                password_hash=hash_password(password),
                platform_admin=True,
            )
            viewer = User(
                username="revision-viewer-" + uuid4().hex,
                password_hash=hash_password(password),
                platform_admin=False,
            )
            db.add_all([org, other, admin, viewer])
            db.flush()
            db.add(
                OrganizationMembership(
                    user_id=viewer.id, organization_id=org.id, role="viewer"
                )
            )
            source = DataSource(
                organization_id=org.id,
                name="Revision source " + uuid4().hex,
                source_type="LINUX",
                connection_config={"opscontrol": {"os_type": "Linux"}},
            )
            foreign = DataSource(
                organization_id=other.id,
                name="Revision foreign " + uuid4().hex,
                source_type="LINUX",
            )
            package = {
                "applicability": {
                    "schema_version": 1,
                    "source_types": ["LINUX"],
                    "os": ["Linux"],
                    "methods": [
                        {
                            "name": "Host metrics",
                            "method_type": "HOST_METRICS",
                            "configuration": {
                                "scrapers": ["cpu", "memory"],
                                "interval_seconds": 30,
                            },
                        }
                    ],
                    "override_components": ["metrics"],
                },
                "metrics": [{"metric": "cpu", "unit": "%"}],
            }
            template = MonitoringTemplate(
                name="Revision template " + uuid4().hex,
                scope="VM",
                package_config=package,
            )
            db.add_all([source, foreign, template])
            db.flush()
            db.add(
                MonitoringTemplateVersion(
                    template_id=template.id, version=1, package_config=package
                )
            )
            db.commit()
            self.org, self.other, self.sid, self.foreign, self.tid, self.uid = map(
                str, [org.id, other.id, source.id, foreign.id, template.id, admin.id]
            )
            admin_name, viewer_name = admin.username, viewer.username
        self.admin = self.call(
            "POST",
            "auth/login",
            dict(username=admin_name, password=password),
            auth=False,
        )[1]["access_token"]
        self.viewer = self.call(
            "POST",
            "auth/login",
            dict(username=viewer_name, password=password),
            auth=False,
        )[1]["access_token"]
        self.base = f"monitoring/data-sources/{self.sid}/configuration"
        self.member = dict(
            template_id=self.tid,
            template_version=1,
            priority=100,
            enabled=True,
            overrides={},
        )

    def call(
        self, method, path, body=None, token=None, key=None, auth=True, selected=None
    ):
        headers = {"Content-Type": "application/json"}
        if auth:
            headers.update(
                Authorization="Bearer " + (token or self.admin),
                **{"X-OpsControl-Customers": selected or self.org},
            )
        if key:
            headers["Idempotency-Key"] = str(key)
        req = Request(
            os.environ["ETL_SCOPE_API_URL"] + "/api/v1/" + path,
            method=method,
            headers=headers,
            data=json.dumps(body).encode() if body is not None else None,
        )
        try:
            with urlopen(req, timeout=20) as r:
                return r.status, json.load(r) if r.status != 204 else None
        except HTTPError as e:
            return e.code, json.load(e)

    def command(self, revision=0, members=None, key=None, status=201):
        code, body = self.call(
            "POST",
            self.base + "/commands",
            dict(
                expected_revision=revision,
                attachments=members if members is not None else [self.member],
            ),
            key=key or uuid4(),
        )
        self.assertEqual(code, status, body)
        return body

    def test_attach_reload_history_rollback_and_detach(self):
        first = self.command()
        self.assertEqual(first["application"], "NOT_REQUESTED")
        self.assertEqual(first["health"], "UNVERIFIED")
        second = self.command(1, [])
        self.assertEqual(second["revision"], 2)
        code, third = self.call(
            "POST",
            self.base + "/rollback",
            dict(expected_revision=2, target_revision=1),
            key=uuid4(),
        )
        self.assertEqual(code, 201, third)
        self.assertEqual(third["revision"], 3)
        self.assertEqual(third["restores_revision"], 1)
        code, history = self.call("GET", self.base + "/history?limit=2")
        self.assertEqual(code, 200)
        self.assertEqual([r["revision"] for r in history["items"]], [3, 2])
        self.assertEqual(history["next_before"], 2)
        self.assertEqual(
            self.call("GET", self.base + "/history?before=2")[1]["items"][0][
                "revision"
            ],
            1,
        )
        self.assertEqual(
            self.call("GET", self.base + "/revisions/1")[1],
            {
                k: v
                for k, v in first.items()
                if k not in ("replayed", "current_revision")
            },
        )
        self.assertEqual(
            self.call("GET", f"monitoring/data-sources/{self.sid}/templates")[1][0][
                "template_version"
            ],
            1,
        )
        self.assertTrue(
            self.call("GET", self.base + "/diff?from_revision=1&to_revision=2")[1][
                "changed"
            ]
        )

    def test_concurrent_stale_commands_and_idempotent_retry(self):
        key = uuid4()
        first = self.command(key=key)
        again = self.command(key=key)
        self.assertTrue(again["replayed"])
        self.assertEqual(first["revision"], again["revision"])
        self.command(0, [], key, status=409)
        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(
                pool.map(
                    lambda priority: self.call(
                        "POST",
                        self.base + "/commands",
                        dict(
                            expected_revision=1,
                            attachments=[self.member | dict(priority=priority)],
                        ),
                        key=uuid4(),
                    ),
                    (201, 202),
                )
            )
        self.assertEqual(sorted(r[0] for r in result), [201, 409], result)
        self.assertEqual(self.call("GET", self.base)[1]["revision"], 2)

    def test_invalid_os_methods_overrides_missing_revision_and_secret(self):
        with SessionLocal() as db:
            source = db.get(DataSource, self.sid)
            source.connection_config = {"opscontrol": {"os_type": "Windows"}}
            db.commit()
        self.command(status=422)
        self.assertEqual(
            self.call(
                "POST", self.base + "/commands", dict(attachments=[]), key=uuid4()
            )[0],
            422,
        )
        self.assertEqual(
            self.call(
                "POST",
                self.base + "/commands",
                dict(expected_revision=0, attachments=[]),
            )[0],
            422,
        )
        self.command(
            members=[self.member | dict(overrides={"collector": {"type": "HTTP"}})],
            status=422,
        )
        self.command(
            members=[self.member | dict(overrides={"password": "never-store-this"})],
            status=422,
        )
        self.assertEqual(self.call("GET", self.base)[1]["revision"], 0)

    def test_legacy_import_is_explicit_non_operational_and_old_writers_fenced(self):
        with SessionLocal() as db:
            # Explicit maintenance import fixture, emulating rows retained by
            # the forward migration. Public/older writers cannot set this fence.
            db.execute(
                text("SELECT set_config('opscontrol.configuration_source', :id, true)"),
                dict(id=self.sid),
            )
            db.add(
                MonitoringTemplateAttachment(
                    data_source_id=self.sid,
                    template_id=self.tid,
                    template_version=1,
                    priority=100,
                )
            )
            db.commit()
        self.command(status=409)
        code, body = self.call(
            "POST", self.base + "/import-legacy", dict(expected_revision=0), key=uuid4()
        )
        self.assertEqual(code, 201, body)
        self.assertFalse(body["document"]["validation"]["valid"])
        self.command(1)
        with SessionLocal() as db:
            with self.assertRaises(DBAPIError):
                db.execute(
                    text(
                        "UPDATE monitoring_template_attachments SET priority=999 WHERE data_source_id=:id"
                    ),
                    dict(id=self.sid),
                )
                db.commit()
        self.assertEqual(
            self.call(
                "PATCH",
                f"monitoring/data-sources/{self.sid}",
                dict(connection_config={}),
            )[0],
            409,
        )
        self.assertEqual(
            self.call(
                "PATCH",
                f"monitoring/data-sources/{self.sid}",
                dict(endpoint="https://retarget.example.test"),
            )[0],
            409,
        )
        self.assertEqual(
            self.call(
                "POST",
                f"monitoring/data-sources/{self.sid}/templates",
                dict(template_id=self.tid, template_version=1),
            )[0],
            428,
        )

    def test_history_immutable_hash_and_atomic_failure(self):
        self.command()
        with SessionLocal() as db:
            row = db.scalar(
                select(SourceConfigurationRevision).where(
                    SourceConfigurationRevision.data_source_id == self.sid
                )
            )
            self.assertEqual(
                hashlib.sha256(row.canonical_document.encode()).hexdigest(),
                row.content_hash,
            )
            for verb in (
                "UPDATE source_configuration_revisions SET actor_name='forged'",
                "DELETE FROM source_configuration_revisions",
            ):
                with self.assertRaises(DBAPIError):
                    db.execute(
                        text(verb + " WHERE data_source_id=:id"), dict(id=self.sid)
                    )
                    db.commit()
                db.rollback()
            db.execute(
                text(
                    "CREATE FUNCTION s01_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.priority=99999 THEN RAISE EXCEPTION 'injected failure'; END IF; RETURN NEW; END $$"
                )
            )
            db.execute(
                text(
                    "CREATE TRIGGER s01_fail BEFORE UPDATE ON monitoring_template_attachments FOR EACH ROW EXECUTE FUNCTION s01_fail()"
                )
            )
            db.commit()
        try:
            self.command(1, [self.member | dict(priority=99999)], status=500)
            self.assertEqual(self.call("GET", self.base)[1]["revision"], 1)
            self.assertEqual(
                len(self.call("GET", self.base + "/history")[1]["items"]), 1
            )
        finally:
            with SessionLocal() as db:
                db.execute(
                    text("DROP TRIGGER s01_fail ON monitoring_template_attachments")
                )
                db.execute(text("DROP FUNCTION s01_fail()"))
                db.commit()

    def test_tenant_viewer_and_stale_session_denied(self):
        self.assertEqual(
            self.call(
                "POST",
                self.base + "/commands",
                dict(expected_revision=0, attachments=[]),
                token=self.viewer,
                key=uuid4(),
            )[0],
            403,
        )
        self.assertEqual(
            self.call(
                "GET",
                f"monitoring/data-sources/{self.foreign}/configuration",
                selected=self.org,
            )[0],
            404,
        )
        with SessionLocal() as db:
            db.get(User, self.uid).active = False
            db.commit()
        self.assertEqual(
            self.call(
                "POST",
                self.base + "/commands",
                dict(expected_revision=0, attachments=[]),
                key=uuid4(),
            )[0],
            401,
        )

    def test_populated_downgrade_refusal_preserves_revision(self):
        self.command()
        env = dict(os.environ)
        attempt = subprocess.run(
            [sys.executable, "-m", "alembic", "downgrade", "0041_etl_authority_writer"],
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(attempt.returncode, 0)
        self.assertIn(
            "Unsafe populated ETL downgrade blocked before DDL", attempt.stderr
        )
        self.assertEqual(self.call("GET", self.base)[1]["revision"], 1)
        self.assertEqual(
            self.call("GET", self.base + "/history")[1]["items"][0]["revision"], 1
        )
        with SessionLocal() as db:
            self.assertEqual(
                db.execute(
                    text("select version_num from alembic_version")
                ).scalar_one(),
                "0042_source_configuration",
            )
        (Path(os.environ["S01_EVIDENCE_DIR"]) / "populated-refusal.log").write_text(
            attempt.stdout + attempt.stderr
        )

    def test_retired_dependency_cannot_be_restored_and_version_rows_are_immutable(self):
        self.command()
        self.command(1, [])
        with SessionLocal() as db:
            for query in (
                "UPDATE monitoring_template_versions SET package_config='{}' WHERE template_id=:id",
                "DELETE FROM monitoring_template_versions WHERE template_id=:id",
            ):
                with self.assertRaises(DBAPIError):
                    db.execute(text(query), dict(id=self.tid))
                    db.commit()
                db.rollback()
            db.get(MonitoringTemplate, self.tid).status = "DISABLED"
            db.commit()
        status, body = self.call(
            "POST",
            self.base + "/rollback",
            dict(expected_revision=2, target_revision=1),
            key=uuid4(),
        )
        self.assertEqual(status, 409, body)
        self.assertEqual(self.call("GET", self.base)[1]["revision"], 2)

    def test_method_schema_and_ambiguous_priorities_fail_without_history(self):
        with SessionLocal() as db:
            template = db.get(MonitoringTemplate, self.tid)
            package = dict(template.package_config)
            package["applicability"] = dict(
                package["applicability"],
                methods=[
                    dict(
                        name="Windows journal",
                        method_type="FILE_LOG",
                        configuration=dict(
                            source="WINDOWS_EVENT", channels=["Application"]
                        ),
                    )
                ],
            )
            template.version = 2
            template.package_config = package
            db.add(
                MonitoringTemplateVersion(
                    template_id=self.tid, version=2, package_config=package
                )
            )
            db.commit()
        self.command(members=[self.member | dict(template_version=2)], status=422)
        self.command(members=[self.member, self.member], status=422)
        excluded = {
            "applicability": {
                "schema_version": 1,
                "source_types": ["AWS_EKS"],
                "os": ["Linux"],
                "methods": [
                    {
                        "name": "Host",
                        "method_type": "HOST_METRICS",
                        "configuration": {"scrapers": ["cpu"]},
                    }
                ],
            }
        }
        self.assertEqual(
            self.call(
                "POST",
                "monitoring/templates",
                dict(name="Excluded manifest " + uuid4().hex, package_config=excluded),
            )[0],
            422,
        )
        self.assertEqual(self.call("GET", self.base)[1]["revision"], 0)

    def test_source_history_foreign_key_and_actor_are_not_client_controlled(self):
        self.command()
        self.assertEqual(
            self.call(
                "POST",
                self.base + "/commands",
                dict(expected_revision=1, attachments=[], actor_id=self.uid),
                key=uuid4(),
            )[0],
            422,
        )
        with SessionLocal() as db:
            with self.assertRaises(DBAPIError):
                db.execute(
                    text(
                        "INSERT INTO source_configuration_revisions(id,organization_id,data_source_id,revision,kind,actor_id,actor_name,command_key,request_hash,content_hash,canonical_document,document) VALUES(:id,:org,:source,2,'UPDATE',:actor,'forged',:key,'x','x','{}','{}')"
                    ),
                    dict(
                        id=str(uuid4()),
                        org=self.other,
                        source=self.sid,
                        actor=self.uid,
                        key=str(uuid4()),
                    ),
                )
                db.commit()
        self.assertEqual(len(self.call("GET", self.base + "/history")[1]["items"]), 1)

    def test_configuration_commit_does_not_create_or_enable_collector(self):
        self.command()
        from app.models import Collector

        with SessionLocal() as db:
            self.assertEqual(
                list(
                    db.scalars(
                        select(Collector).where(Collector.data_source_id == self.sid)
                    )
                ),
                [],
            )
            self.assertEqual(db.get(DataSource, self.sid).status, "UNKNOWN")

    def test_https_template_uses_real_api_schema_without_claiming_network_authority(
        self,
    ):
        package = {
            "collector": {"type": "HTTP"},
            "applicability": {
                "schema_version": 1,
                "family": "API",
                "source_types": ["API"],
                "methods": [
                    {
                        "name": "Read-only check",
                        "method_type": "HTTPS",
                        "configuration": {
                            "method": "HEAD",
                            "expected_status": 204,
                            "max_response_time_ms": 10000,
                            "headers": {"x-opscontrol-check": "source-revision"},
                        },
                    }
                ],
            },
        }
        with SessionLocal() as db:
            source = db.get(DataSource, self.sid)
            source.source_type = "API"
            source.endpoint = "https://synthetic-api.example.test/health"
            template = db.get(MonitoringTemplate, self.tid)
            template.version = 2
            template.package_config = package
            db.add(
                MonitoringTemplateVersion(
                    template_id=self.tid, version=2, package_config=package
                )
            )
            db.commit()
        row = self.command(members=[self.member | dict(template_version=2)])
        self.assertEqual(row["application"], "NOT_REQUESTED")
        status, effective = self.call(
            "GET", f"monitoring/data-sources/{self.sid}/effective-configuration"
        )
        self.assertEqual(status, 200)
        self.assertTrue(effective["valid"])
        self.assertEqual(effective["collector"]["method"], "HEAD")
        self.assertEqual(effective["collector"]["max_response_time_ms"], 10000)
        for version, configuration in enumerate(
            [
                {"method": "POST"},
                {"method": "GET", "body": "forbidden"},
                {"url": "http://synthetic-api.example.test"},
            ],
            start=3,
        ):
            invalid = {
                **package,
                "applicability": {
                    **package["applicability"],
                    "methods": [
                        {
                            "name": "Unsafe method",
                            "method_type": "HTTPS",
                            "configuration": configuration,
                        }
                    ],
                },
            }
            with SessionLocal() as db:
                template = db.get(MonitoringTemplate, self.tid)
                template.version = version
                template.package_config = invalid
                db.add(
                    MonitoringTemplateVersion(
                        template_id=self.tid, version=version, package_config=invalid
                    )
                )
                db.commit()
            self.command(1, [self.member | dict(template_version=version)], status=422)
        self.assertEqual(self.call("GET", self.base)[1]["revision"], 1)

"""Registry schema/ownership unit contracts, not PostgreSQL acceptance evidence."""

import hashlib
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.registry import api
from app.registry.definitions import package, render_definition
from app.registry.models import ResourceDraft, now
from app.security.scope import Principal, current_principal


class RegistryDefinitionTests(unittest.TestCase):
    def test_package_checksum_is_stable_and_covers_capabilities(self):
        first, second = package(), package()
        self.assertEqual(first, second)
        payload = {key: first[key] for key in ("definitions", "capabilities")}
        digest = hashlib.sha256(
            json.dumps(
                payload, sort_keys=True, default=str, separators=(",", ":")
            ).encode()
        ).hexdigest()
        self.assertEqual(first["sha256"], digest)
        payload["capabilities"]["os"]["Other"]["agent"] = True
        changed = hashlib.sha256(
            json.dumps(
                payload, sort_keys=True, default=str, separators=(",", ":")
            ).encode()
        ).hexdigest()
        self.assertNotEqual(changed, first["sha256"])

    def test_supported_sources_and_nine_adapters_have_typed_definitions(self):
        result = package()
        methods = result["capabilities"]["methods"]
        for name in (
            "HOST_METRICS",
            "SERVICES",
            "SYSLOG_RECEIVER",
            "FILE_LOG",
            "METRIC_SCRAPE",
        ):
            self.assertIn(name, methods)
            self.assertTrue(methods[name]["concurrent"])
            self.assertIn(name, result["definitions"])
        self.assertEqual(methods["FILE_LOG"]["signals"], ["logs"])
        self.assertEqual(methods["HOST_METRICS"]["signals"], ["metrics"])
        self.assertEqual(
            methods["OTLP_RECEIVER"]["signals"], ["logs", "metrics", "traces"]
        )
        self.assertEqual(len(result["capabilities"]["platforms"]), 9)
        for name in result["capabilities"]["platforms"]:
            self.assertIn("PLATFORM_" + name, result["definitions"])
        self.assertFalse(result["capabilities"]["os"]["Other"]["agent"])

    def test_nullable_refs_defaults_and_validation_render_without_secret_values(self):
        definition = render_definition(
            "API",
            {
                "required": ["port"],
                "properties": {
                    "port": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 65535,
                        "default": 443,
                    },
                    "enabled": {"type": "boolean", "default": True},
                    "protocol": {"enum": ["HTTP", "HTTPS"], "type": "string"},
                    "credential_ref": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "nested": {"$ref": "#/$defs/Nested"},
                    "paths": {"type": "array", "minItems": 1, "maxItems": 10},
                    "optional_enum": {
                        "anyOf": [
                            {"type": "null"},
                            {"type": "string", "enum": ["x", "y"]},
                        ]
                    },
                },
            },
        )
        fields = {field["key"]: field for field in definition["fields"]}
        self.assertEqual(fields["port"]["input_type"], "number")
        self.assertEqual(fields["port"]["default"], 443)
        self.assertTrue(fields["port"]["required"])
        self.assertEqual(fields["port"]["validation"], {"minimum": 1, "maximum": 65535})
        self.assertEqual(fields["enabled"]["input_type"], "checkbox")
        self.assertEqual(fields["credential_ref"]["secret_handling"], "REFERENCE_ONLY")
        self.assertEqual(
            fields["credential_ref"]["conditional_requirements"], {"protocol": "HTTPS"}
        )
        self.assertEqual(fields["nested"]["input_type"], "json")
        self.assertEqual(fields["paths"]["validation"], {"minItems": 1, "maxItems": 10})
        self.assertEqual(fields["optional_enum"]["allowed_values"], ["x", "y"])
        inherited = render_definition(
            "ETL", {"properties": {"environment": {"type": "string"}}}
        )["fields"][0]
        self.assertEqual(inherited["inheritance"], "VM")
        self.assertEqual(inherited["override_policy"], "READ_ONLY_INHERITED")


class DraftValidationTests(unittest.TestCase):
    def draft(self, configuration=None, **kwargs):
        return api.DraftInput(
            domain="VM",
            name="Unactivated draft",
            stage=1,
            configuration=configuration or {},
            **kwargs
        )

    def test_partial_draft_retains_empty_fields_without_claiming_activation(self):
        value = {
            "hostname": "",
            "address": None,
            "environment": "QA",
            "os_type": "Linux",
        }
        self.assertEqual(api.validate_draft(self.draft(value)), value)
        for stage in (0, 11):
            with self.assertRaises(ValidationError):
                api.DraftInput(domain="VM", name="Draft", stage=stage, configuration={})

    def test_unknown_attributes_bad_types_and_embedded_credentials_are_rejected(self):
        for value in (
            {"platform_admin": True},
            {"os_type": "Other"},
            {"hostname": "x" * 201},
            {"tags": {"password": "unit-fixture-only"}},
            {"tags": {"url": "https://user:password@example.test"}},
            {"tags": {"oversized": "x" * (256 * 1024)}},
        ):
            with self.subTest(keys=list(value)), self.assertRaises(ValueError):
                api.validate_draft(self.draft(value))

    def test_customer_fields_must_agree_and_resource_id_is_valid_uuid(self):
        organization, other = uuid4(), uuid4()
        value = self.draft(
            {"organization_id": str(organization)}, organization_id=organization
        )
        api.validate_draft(value)
        with self.assertRaises(ValueError):
            api.validate_draft(
                self.draft(
                    {"organization_id": str(other)}, organization_id=organization
                )
            )
        with self.assertRaises(ValueError):
            api.validate_draft(self.draft({"resource_id": "invalid"}))
        api.validate_draft(self.draft({"resource_id": ""}))

    def test_linked_resource_cannot_change_domain_or_customer(self):
        organization = uuid4()
        payload = self.draft(
            {"resource_id": str(uuid4())}, organization_id=organization
        )
        for row in (
            SimpleNamespace(domain="API", organization_id=organization),
            SimpleNamespace(domain="VM", organization_id=uuid4()),
        ):
            with patch.object(api, "resource", return_value=row), self.assertRaises(
                ValueError
            ):
                api.validate_draft(payload, Mock())
        with patch.object(
            api,
            "resource",
            return_value=SimpleNamespace(domain="VM", organization_id=organization),
        ):
            self.assertEqual(api.validate_draft(payload, Mock()), payload.configuration)


class RegistryRouteGuardTests(unittest.TestCase):
    def setUp(self):
        self.organization, self.provider, self.user = uuid4(), uuid4(), uuid4()
        self.principal = Principal(
            self.user,
            "unit-reader",
            False,
            {},
            service_provider_id=self.provider,
            permissions=frozenset(),
            customer_permissions={},
        )
        self.context = current_principal.set(self.principal)
        self.addCleanup(current_principal.reset, self.context)

    def test_owner_context_requires_authenticated_provider(self):
        self.assertEqual(api.owner(Mock()).user_id, self.user)
        token = current_principal.set(None)
        try:
            with self.assertRaises(HTTPException) as caught:
                api.owner(Mock())
            self.assertEqual(caught.exception.status_code, 403)
        finally:
            current_principal.reset(token)

    def test_lookup_query_binds_id_provider_and_owner_before_returning_data(self):
        db = Mock()
        db.scalar.return_value = None
        id = uuid4()
        with self.assertRaises(HTTPException) as caught:
            api.lookup(db, id, write=True)
        self.assertEqual(caught.exception.status_code, 404)
        query = db.scalar.call_args.args[0].compile(dialect=postgresql.dialect())
        self.assertEqual(set(query.params.values()), {id, self.provider, self.user})
        self.assertIn("FOR UPDATE", str(query))
        db.scalar.return_value = SimpleNamespace(organization_id=self.organization)
        with self.assertRaises(HTTPException) as denied:
            api.lookup(db, id)
        self.assertEqual(denied.exception.status_code, 403)

    def test_customer_permission_denial_precedes_any_draft_write(self):
        db = Mock()
        payload = api.DraftInput(
            domain="VM",
            name="Draft",
            stage=1,
            configuration={},
            organization_id=self.organization,
        )
        with self.assertRaises(HTTPException) as caught:
            api.create_draft(payload, db)
        self.assertEqual(caught.exception.status_code, 403)
        db.add.assert_not_called()
        db.flush.assert_not_called()

    def test_bad_payload_is_422_without_persistence_or_secret_error_echo(self):
        db = Mock()
        payload = api.DraftInput(
            domain="VM",
            name="Draft",
            stage=1,
            configuration={"tags": {"token": "private-test-value"}},
        )
        with self.assertRaises(HTTPException) as caught:
            api.create_draft(payload, db)
        self.assertEqual(caught.exception.status_code, 422)
        self.assertNotIn("private-test-value", caught.exception.detail)
        db.add.assert_not_called()

    def test_stale_revision_and_domain_changes_are_conflicts_before_mutation(self):
        row = SimpleNamespace(domain="VM", revision=2)
        for domain, revision in (("API", 2), ("VM", 1)):
            payload = api.DraftInput(
                domain=domain,
                name="Draft",
                stage=1,
                configuration={},
                expected_revision=revision,
            )
            with patch.object(api, "lookup", return_value=row), self.assertRaises(
                HTTPException
            ) as caught:
                api.update_draft(uuid4(), payload, Mock())
            self.assertEqual(caught.exception.status_code, 409)
            self.assertEqual(row.revision, 2)

    def test_uninstalled_registry_is_503_not_a_fake_default(self):
        db = Mock()
        db.scalar.return_value = None
        with self.assertRaises(HTTPException) as caught:
            api.registry(version=99, db=db)
        self.assertEqual(caught.exception.status_code, 503)
        db.scalar.return_value = SimpleNamespace(
            version=2, definitions={"VM": {}}, capabilities={"os": {}}, sha256="a" * 64
        )
        self.assertEqual(api.registry(version=2, db=db)["version"], 2)

    def test_runtime_model_defaults_are_timezone_aware_and_scoped(self):
        self.assertIsNotNone(now().tzinfo)
        columns = ResourceDraft.__table__.columns
        self.assertFalse(columns.owner_id.nullable)
        self.assertFalse(columns.service_provider_id.nullable)
        self.assertIn(
            "fk_draft_owner_provider",
            {c.name for c in ResourceDraft.__table__.constraints},
        )

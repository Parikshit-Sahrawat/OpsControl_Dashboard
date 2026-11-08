"""Offline preparation only: synthetic records can never qualify a provider."""

import base64
import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import HTTPException
from pydantic import ValidationError
from app.etl_bindings.authority import (
    Envelope,
    AuthorityBody,
    signed_bytes,
    verify_signature,
)
from app.pipeline_adapters.core import AdapterError
from app.pipeline_adapters.pentaho_observations import (
    normalize_observation,
    scoped_identity,
)

PACKAGE = Path(__file__).resolve().parents[2] / "docs/verification/oc-etl-008"
NOW = datetime(2026, 11, 7, 1, 2, tzinfo=timezone.utc)


class QualificationPreparationTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = {
            r["case"]: r
            for r in json.loads((PACKAGE / "SYNTHETIC_FIXTURES.json").read_text())[
                "cases"
            ]
        }

    def normalize(self, name):
        row = self.fixtures[name]
        return normalize_observation(
            row["record"], row["context"], "synthetic-customer"
        )

    def test_success_failure_running_are_only_synthetic_observations(self):
        for name in ("success", "failure", "running"):
            with self.subTest(name=name):
                fact = self.normalize(name)
                self.assertEqual(
                    fact["event"]["status"], self.fixtures[name]["expected"]
                )
                self.assertFalse(fact["evidence"]["runtime_certified"])

    def test_missing_and_conflicting_identity_refuse(self):
        for name in ("missing", "conflicting"):
            with self.subTest(name=name), self.assertRaises(AdapterError):
                self.normalize(name)

    def test_duplicate_identity_is_stable_without_claiming_database_dedup(self):
        first, second = self.normalize("success"), self.normalize("duplicate")
        self.assertEqual(
            first["event"]["pentaho_identity"]["invocation_alias"],
            second["event"]["pentaho_identity"]["invocation_alias"],
        )
        self.assertEqual(first, second)

    def test_scheduler_trigger_success_does_not_assert_execution_success(self):
        row = copy.deepcopy(self.fixtures["success"])
        row["record"]["authority"] = "SCHEDULER"
        fact = normalize_observation(
            row["record"], row["context"], "synthetic-customer"
        )
        self.assertEqual(fact["event"]["status"], "UNKNOWN")
        self.assertFalse(fact["event"]["terminal_status_observed"])

    def test_carte_epoch_and_tenant_are_identity_boundaries(self):
        ctx = {
            **self.fixtures["success"]["context"],
            "surface": "CARTE",
            "restart_epoch": "synthetic-epoch-1",
        }
        first = scoped_identity("a", ctx, "registration-1")
        self.assertNotEqual(
            first,
            scoped_identity(
                "a", {**ctx, "restart_epoch": "synthetic-epoch-2"}, "registration-1"
            ),
        )
        self.assertNotEqual(first, scoped_identity("b", ctx, "registration-1"))

    def envelope(self):
        def uid(n):
            return str(UUID(int=n))

        body = {
            "schema_version": 1,
            "assurance": "CONTRACT_TEST_ONLY",
            "organization_id": uid(1),
            "environment": "TEST",
            "platform": "PENTAHO",
            "binding_id": uid(2),
            "native_job_id": uid(3),
            "observed_native_id": "synthetic-repository-object-1",
            "canonical_authority_id": "SYNTHETIC-SERVER-ONLY",
            "authority_aliases": ["SYNTHETIC-SERVER-ONLY"],
            "canonical_object_key": "synthetic:repository-object-1",
            "object_kind": "JOB",
            "not_before": NOW - timedelta(minutes=1),
            "issued_at": NOW,
            "expires_at": NOW + timedelta(minutes=10),
            "methods": [
                {
                    "method_id": uid(4),
                    "source_id": uid(5),
                    "generation": uid(6),
                    "revision": 1,
                    "reader_definition_hash": "b" * 64,
                    "evidence_id": uid(7),
                    "payload_sha256": "a" * 64,
                    "exact_build": "10.2.0.0-222",
                }
            ],
        }
        key = Ed25519PrivateKey.generate()
        store = {
            "version": 1,
            "issuers": {
                "offline-test-only": {
                    "assurance": "CONTRACT_TEST_ONLY",
                    "revoked": False,
                    "targets": {},
                    "public_key_base64": base64.b64encode(
                        key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
                    ).decode(),
                }
            },
        }
        return body, key, store

    def sign(self, body, key):
        raw = AuthorityBody.model_validate(body).model_dump(mode="json")
        return Envelope.model_validate(
            {
                "issuer_key_id": "offline-test-only",
                "body": raw,
                "signature": base64.b64encode(key.sign(signed_bytes(raw))).decode(),
            }
        )

    def test_signature_validity_never_grants_qualification(self):
        body, key, store = self.envelope()
        result = verify_signature(self.sign(body, key), store, NOW)
        self.assertEqual(result["status"], "CONTRACT_VALID_NOT_QUALIFIED")
        self.assertFalse(result["qualified"])
        body["assurance"] = "PROVIDER_QUALIFIED"
        with self.assertRaises(HTTPException) as error:
            verify_signature(self.sign(body, key), store, NOW)
        self.assertEqual(error.exception.detail, "TEST_ISSUER_CANNOT_QUALIFY_PROVIDER")

    def test_stale_observation_can_parse_but_expired_proof_refuses(self):
        # Parser is not the freshness/authority gate: record that distinction.
        fact = self.normalize("stale")
        self.assertEqual(fact["event"]["status"], "SUCCESS")
        self.assertFalse(fact["evidence"]["runtime_certified"])
        body, key, store = self.envelope()
        body.update(
            not_before=NOW - timedelta(hours=2),
            issued_at=NOW - timedelta(hours=1),
            expires_at=NOW - timedelta(seconds=1),
        )
        with self.assertRaises(HTTPException):
            verify_signature(self.sign(body, key), store, NOW)

    def test_alias_tamper_and_ambiguous_alias_refuse(self):
        body, key, store = self.envelope()
        signed = self.sign(body, key).model_dump(mode="json")
        signed["body"]["canonical_object_key"] = "other-object"
        with self.assertRaises(HTTPException):
            verify_signature(Envelope.model_validate(signed), store, NOW)
        body["authority_aliases"] *= 2
        with self.assertRaises(HTTPException):
            verify_signature(self.sign(body, key), store, NOW)

    def test_no_scheduler_or_execution_fields_added_to_authority_schema(self):
        body, key, _ = self.envelope()
        for changed in (
            {**body, "schedule_id": "unapproved"},
            {**body, "object_kind": "TRANSFORMATION"},
        ):
            with self.assertRaises(ValidationError):
                self.sign(changed, key)

    def test_endpoint_candidates_never_authorize_live_requests(self):
        rows = json.loads((PACKAGE / "ENDPOINT_CANDIDATES.json").read_text())
        self.assertEqual(len(rows), 5)
        for row in rows:
            self.assertEqual(row["status"], "UNVERIFIED")
            self.assertIsNone(row["exact_build"])
            self.assertFalse(row["live_request_permitted"])
            self.assertEqual(row["method"], "GET")

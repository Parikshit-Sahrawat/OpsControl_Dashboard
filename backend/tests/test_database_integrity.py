"""Restore fingerprints tolerate only explicitly approved PostgreSQL cast rewrites."""

from collections import namedtuple
from unittest import TestCase
from unittest.mock import Mock, patch

from scripts.database_integrity import fingerprint

Constraint = namedtuple("Constraint", "relname conname contype convalidated definition")


class RestoreFingerprintTests(TestCase):
    def document(self, definition, name="ck_pipeline_transport", valid=True):
        connection = Mock()
        connection.execute.return_value.all.return_value = [
            Constraint("pipeline_methods", name, "c", valid, definition)
        ]
        inspector = Mock()
        inspector.get_table_names.return_value = []
        with patch("scripts.database_integrity.inspect", return_value=inspector):
            return fingerprint(connection)

    def test_restore_text_array_cast_rewrite_is_equivalent(self):
        before = "CHECK (((transport)::text = ANY ((ARRAY['BACKEND'::character varying, 'AGENT'::character varying])::text[])))"
        restored = "CHECK (((transport)::text = ANY (ARRAY[('BACKEND'::character varying)::text, ('AGENT'::character varying)::text])))"
        self.assertEqual(self.document(before), self.document(restored))

    def test_changed_allowed_values_and_operator_are_rejected(self):
        for expression in [
            "CHECK (transport = ANY (ARRAY['BACKEND','AGENT','PUBLIC']))",
            "CHECK (transport != ANY (ARRAY['BACKEND','AGENT']))",
            "CHECK (transport = ANY (ARRAY['BACKEND']))",
        ]:
            with self.subTest(expression=expression), self.assertRaises(AssertionError):
                self.document(expression)

    def test_unapproved_constraint_definition_remains_byte_exact(self):
        a = self.document("CHECK (revision > 0)", "other_constraint")
        b = self.document("CHECK ((revision > 0))", "other_constraint")
        self.assertNotEqual(a, b)

    def test_unvalidated_constraint_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "Unvalidated"):
            self.document("CHECK (revision > 0)", "other_constraint", False)

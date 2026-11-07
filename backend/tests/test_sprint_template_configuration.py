import unittest
from fastapi import HTTPException
from app.services.template_resolution import _apply_package


class TemplateConfigurationTests(unittest.TestCase):
    def test_malformed_package_fails_with_validation_instead_of_500(self):
        for package in (
            {"collector": []},
            {"metrics": "invalid"},
            {"logs": [1]},
            {"attributes": None},
        ):
            with self.subTest(package=package), self.assertRaises(
                HTTPException
            ) as error:
                _apply_package({}, package)
            self.assertEqual(error.exception.status_code, 422)

    def test_named_overrides_preserve_unrelated_metrics(self):
        original = {
            "metrics": [
                {"metric": "cpu", "unit": "pct"},
                {"metric": "disk", "unit": "bytes"},
            ]
        }
        output = _apply_package(
            original, {"metrics": [{"metric": "cpu", "interval": 30}]}
        )
        self.assertEqual(
            output["metrics"],
            [
                {"metric": "cpu", "unit": "pct", "interval": 30},
                {"metric": "disk", "unit": "bytes"},
            ],
        )
        self.assertEqual(original["metrics"][1], {"metric": "disk", "unit": "bytes"})

    def test_attachment_update_rejects_forged_ownership_and_null_state(self):
        from pydantic import ValidationError
        from app.schemas.monitoring import MonitoringTemplateAttachmentUpdate

        for data in (
            {"data_source_id": "forged"},
            {"enabled": None},
            {"template_version": None},
            {"priority": None},
        ):
            with self.subTest(data=data), self.assertRaises(ValidationError):
                MonitoringTemplateAttachmentUpdate.model_validate(data)

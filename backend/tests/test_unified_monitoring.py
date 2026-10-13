"""Security and calendar boundaries for ARCH-001, without simulated DB success."""

import unittest
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError
from app.unified.schemas import (
    VMCreate,
    ETLCreate,
    APICreate,
    LogParser,
    Schedule,
    import_document,
    validate_parameters,
)
from app.unified.normalization import normalize, NormalizationError
from app.unified.calendar import occurrences


class UnifiedSchemaTests(unittest.TestCase):
    def test_saas_etl_requires_customer_but_not_vm(self):
        r = ETLCreate(
            name="Cloud task",
            platform="IICS",
            jobchain="Task",
            organization_id=uuid4(),
            environment="PROD",
        )
        self.assertIsNone(r.vm_resource_id)
        with self.assertRaises(ValidationError):
            ETLCreate(name="Cloud task", platform="IICS", jobchain="Task")
        with self.assertRaises(ValidationError):
            ETLCreate(
                name="Cloud task",
                platform="IICS",
                jobchain="Task",
                organization_id=uuid4(),
                environment="PROD",
                log_paths=["/private/log"],
            )

    def test_api_identity_rejects_credentials_and_unsafe_configuration(self):
        base = {
            "name": "Endpoint",
            "organization_id": uuid4(),
            "environment": "QA",
            "dns": "api.example.test",
        }
        for update in (
            {"dns": "https://host/path"},
            {"tls_validation": False},
            {"headers": {"Authorization": "secret"}},
            {
                "protocol": "HTTP",
                "auth_type": "BEARER",
                "credential_ref": "env:API_TOKEN",
            },
        ):
            with self.subTest(update=list(update)), self.assertRaises(ValidationError):
                APICreate(**{**base, **update})

    def test_import_never_executes_yaml_or_accepts_recursive_aliases(self):
        for text in (
            "!!python/object/apply:os.system [echo forbidden]",
            "a: &a [*a]",
            "[1,2]",
        ):
            with self.assertRaises(ValueError):
                import_document(text, "YAML")
        self.assertEqual(
            import_document("domain: ETL\nno_run_grace_seconds: 60", "YAML")["domain"],
            "ETL",
        )

    def test_override_cannot_change_tenant_identity_or_invalid_units(self):
        with self.assertRaises(ValueError):
            validate_parameters("VM", {"overrides": {"customer_id": str(uuid4())}})
        with self.assertRaises(ValueError):
            validate_parameters(
                "VM",
                {"thresholds": [{"metric_name": "cpu", "critical": 101, "unit": "%"}]},
            )
        result = validate_parameters("ETL", {"overrides": {"long_running_seconds": 30}})
        self.assertEqual(result["long_running_seconds"], 30)

    def test_missing_execution_id_is_unresolved_not_inferred(self):
        with self.assertRaisesRegex(NormalizationError, "IDENTITY_REQUIRED"):
            normalize(
                {"event": "START", "status": "RUNNING"},
                LogParser().model_dump(),
                datetime.now(timezone.utc),
                "Task",
            )

    def test_jobchain_filter_and_retry_identity(self):
        now = datetime.now(timezone.utc)
        with self.assertRaisesRegex(NormalizationError, "OTHER_JOBCHAIN"):
            normalize(
                {"execution_id": "x", "jobchain": "Other"},
                LogParser().model_dump(),
                now,
                "Task",
            )
        event, _ = normalize(
            {
                "execution_id": "x",
                "event": "STEP_FAILED",
                "step": "Load",
                "attempt": 2,
                "status": "FAILED",
            },
            LogParser().model_dump(),
            now,
            "Task",
        )
        self.assertEqual(
            (event["execution_id"], event["step_id"], event["attempt"]),
            ("x", "Load", 2),
        )

    def test_unknown_timezone_and_invalid_pattern_fail_as_validation(self):
        with self.assertRaises(ValidationError):
            Schedule(timezone="Not/AZone")
        with self.assertRaises(ValidationError):
            LogParser(format="REGEX", pattern="(")


class CalendarTests(unittest.TestCase):
    def test_spring_gap_is_skipped_and_fall_fold_is_deterministic(self):
        utc = timezone.utc
        spring = list(
            occurrences(
                {"frequency": "DAILY", "time": "02:30", "timezone": "America/New_York"},
                datetime(2026, 3, 7, 23, tzinfo=utc),
                datetime(2026, 3, 9, 23, tzinfo=utc),
            )
        )
        self.assertEqual(spring, [datetime(2026, 3, 9, 6, 30, tzinfo=utc)])
        start = datetime(2026, 11, 1, 0, tzinfo=utc)
        end = datetime(2026, 11, 2, 0, tzinfo=utc)
        for fold, hour in [("FIRST", 5), ("SECOND", 6)]:
            self.assertEqual(
                list(
                    occurrences(
                        {
                            "frequency": "DAILY",
                            "time": "01:30",
                            "timezone": "America/New_York",
                            "dst_policy": fold,
                        },
                        start,
                        end,
                    )
                ),
                [datetime(2026, 11, 1, hour, 30, tzinfo=utc)],
            )

    def test_calendar_month_quarter_custom_and_exceptions(self):
        utc = timezone.utc
        start = datetime(2026, 1, 1, tzinfo=utc)
        end = datetime(2026, 5, 1, tzinfo=utc)
        quarter = list(
            occurrences(
                {"frequency": "QUARTERLY", "time": "09:00", "timezone": "UTC"},
                start,
                end,
            )
        )
        self.assertEqual([d.month for d in quarter], [1, 4])
        custom = list(
            occurrences(
                {
                    "frequency": "CUSTOM",
                    "cron": "0 12 * * 1",
                    "timezone": "UTC",
                    "exceptions": ["2026-01-05"],
                },
                start,
                datetime(2026, 1, 13, tzinfo=utc),
            )
        )
        self.assertEqual(custom, [datetime(2026, 1, 12, 12, tzinfo=utc)])

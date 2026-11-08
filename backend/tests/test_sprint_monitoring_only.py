"""The VM configuration surface describes observation, never workload commands."""

import unittest
from pydantic import ValidationError
from app.unified.schemas import VMCreate, VMParameters


class MonitoringOnlyConfigurationTests(unittest.TestCase):
    def test_workload_operations_are_not_vm_registration_fields(self):
        valid = {
            "organization_id": "00000000-0000-0000-0000-000000000001",
            "name": "read-only",
            "environment": "DEV",
            "hostname": "synthetic.invalid",
            "address": "203.0.113.10",
            "os_type": "Linux",
        }
        self.assertEqual(VMCreate.model_validate(valid).hostname, "synthetic.invalid")
        for key in ("remote_command", "service_action", "restart_process", "etl_retry"):
            with self.subTest(operation=key), self.assertRaises(ValidationError) as exc:
                VMCreate.model_validate({**valid, key: "forbidden"})
            self.assertTrue(
                any(
                    e["type"] == "extra_forbidden" and e["loc"] == (key,)
                    for e in exc.exception.errors()
                )
            )

    def test_parameter_selectors_do_not_authorize_service_control(self):
        baseline = VMParameters.model_validate(
            {"domain": "VM", "services": ["sshd"], "processes": ["python"]}
        )
        self.assertEqual(baseline.services, ["sshd"])
        with self.assertRaises(ValidationError):
            VMParameters.model_validate(
                {"domain": "VM", "services": ["sshd"], "service_action": "restart"}
            )

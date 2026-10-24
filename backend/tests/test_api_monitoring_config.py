"""DEV-04.3 API configuration contract tests using the repository's unittest runner."""
import unittest
from types import SimpleNamespace
from fastapi import HTTPException
from app.services.api_monitoring_config import build_api_config


class APIConfigTests(unittest.TestCase):
    def setUp(self):
        self.worker = SimpleNamespace(allowed_hosts=["api.example.test"], allowed_cidrs=["203.0.113.0/24"])
        self.source = SimpleNamespace(endpoint="https://api.example.test/health")

    def test_get_defaults_preserve_existing_remote_worker_protocol(self):
        self.assertEqual(build_api_config({}, self.source, self.worker), {
            "url": "https://api.example.test/health", "expected_status": 200,
            "timeout_seconds": 8, "method": "GET",
        })

    def test_unsupported_or_unsafe_api_configuration_fails_closed(self):
        cases = [
            {"method": "POST"}, {"method": "DELETE"},
            {"method": "get"}, {"headers": {"Authorization": "Bearer secret"}},
            {"headers": {"X-Evil": "unexpected"}},
            {"body": {"password": "secret"}}, {"query": {"token": "sensitive"}},
            {"url": "http://api.example.test/health"},
            {"url": "https://evil.example.test/health"},
            {"url": "https://api.example.test/health?secret=x"},
            {"expected_status": True}, {"expected_status": 600},
            {"timeout_seconds": 0}, {"timeout_seconds": 11},
            {"max_response_time_ms": True}, {"max_response_time_ms": 0},
            {"max_response_time_ms": 10001},
        ]
        for config in cases:
            with self.subTest(config=config):
                with self.assertRaises(HTTPException) as error:
                    build_api_config(config, self.source, self.worker)
                self.assertEqual(error.exception.status_code, 422)

    def test_bounded_latency_assertion_is_retained(self):
        cfg=build_api_config({"max_response_time_ms":250},self.source,self.worker)
        self.assertEqual(cfg["max_response_time_ms"],250)

    def test_head_and_allowlisted_headers_are_valid(self):
        config=build_api_config({"method":"HEAD","headers":{"X-OpsControl-Check":"ready"}},self.source,self.worker)
        self.assertEqual(config["method"],"HEAD")
        self.assertEqual(config["headers"],{"x-opscontrol-check":"ready"})

    def test_header_injection_is_rejected(self):
        with self.assertRaises(HTTPException):
            build_api_config({"headers":{"Accept":"text/plain\\r\\nAuthorization: token"}},self.source,self.worker)

    def test_valid_explicit_get_preserves_status_and_timeout(self):
        config = build_api_config({"method": "GET", "expected_status": 204, "timeout_seconds": 5}, self.source, self.worker)
        self.assertEqual(config["method"], "GET")
        self.assertEqual(config["expected_status"], 204)
        self.assertEqual(config["timeout_seconds"], 5)


if __name__ == "__main__":
    unittest.main()

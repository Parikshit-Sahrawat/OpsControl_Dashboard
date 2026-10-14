"""Offline security regressions. Run python -m unittest discover -s tests -v."""

import asyncio
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pydantic import ValidationError
from fastapi import HTTPException

from app.core.config import Settings, settings
from app.security.secret_refs import require_safe_config, redact_config
from app.security.deployment import trusted_proxies
from app.security.http import UserCreate, IdentityMiddleware
from app.api.rule_catalogs import validate_definition
from app.schemas.monitoring import AlertRuleBase, AlertRuleUpdate
from app.worker.credentials import resolve_basic_auth, CredentialProviderError
from app.worker.collector_runtime import ApiAdapter


class ReleaseSecurityTests(unittest.TestCase):
    def test_mixed_case_and_other_url_credentials_are_rejected_and_redacted(self):
        for url in (
            "HTTPS://reader:private@example.test",
            "hTtPs://reader:private@example.test",
            "//reader:private@example.test",
            "postgresql://reader:private@example.test",
            "https://[malformed/private",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    require_safe_config({"nested": [{"url": url}]})
                self.assertNotIn("private", str(redact_config({"url": url})))

    def test_url_without_credentials_is_preserved(self):
        value = {
            "url": "HTTPS://service.example.test/ready",
            "credential_ref": "approved-reference",
        }
        self.assertEqual(require_safe_config(value), value)
        self.assertEqual(redact_config(value), value)

    def test_production_loaded_from_dotenv_denies_environment_credentials(self):
        # A separate interpreter reproduces startup with no exported ENVIRONMENT.
        backend = str(Path(__file__).resolve().parents[1])
        env = os.environ.copy()
        env.pop("ENVIRONMENT", None)
        env["PYTHONPATH"] = backend
        env["OPSCONTROL_CREDENTIAL_FIXTURE_USERNAME"] = "synthetic-reader"
        env["OPSCONTROL_CREDENTIAL_FIXTURE_PASSWORD"] = "synthetic-only"
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, ".env").write_text("ENVIRONMENT=production\n")
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from app.worker.credentials import resolve_basic_auth, CredentialProviderError\n"
                    'try: resolve_basic_auth("fixture")\n'
                    'except CredentialProviderError: print("DENIED")\n'
                    'else: raise AssertionError("production bypass")',
                ],
                cwd=directory,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "DENIED")

    def test_invalid_environment_fails_closed(self):
        with self.assertRaises(ValidationError):
            Settings(environment="prodution", _env_file=None)

    def test_short_user_password_is_validation_error(self):
        with self.assertRaises(ValidationError):
            UserCreate(username="synthetic", password="short")

    def test_nonfinite_thresholds_are_rejected_on_all_write_paths(self):
        for value in ("NaN", "inf", "-Infinity", "1e999", "not-a-number"):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    AlertRuleBase(name="sample", threshold_value=value)
                with self.assertRaises(ValidationError):
                    AlertRuleUpdate(threshold_value=value)
                with self.assertRaises(HTTPException) as error:
                    validate_definition(
                        "ALERT",
                        {
                            "metric_name": "http_up",
                            "operator": "LT",
                            "threshold_value": value,
                        },
                    )
                self.assertEqual(error.exception.status_code, 422)

    def test_finite_threshold_is_preserved(self):
        self.assertEqual(
            AlertRuleBase(name="sample", threshold_value="0.50").threshold_value, "0.50"
        )

    def test_proxy_trust_rejects_wildcards_and_unbounded_networks(self):
        for value in ("", "*", "0.0.0.0/0", "::/0", "localhost", "10.0.0.1,*"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                trusted_proxies(value)
        self.assertEqual(
            trusted_proxies(" 10.0.0.2,10.0.1.0/24 "), "10.0.0.2,10.0.1.0/24"
        )


class AsyncSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_production_legacy_api_fails_before_secret_or_network_access(self):
        with patch.object(settings, "environment", "production"), patch(
            "app.worker.collector_runtime.resolve_basic_auth",
            side_effect=AssertionError("secret accessed"),
        ):
            result = await ApiAdapter().collect(
                SimpleNamespace(
                    configuration={
                        "url": "http://127.0.0.1",
                        "credential_ref": "fixture",
                    }
                )
            )
        self.assertFalse(result.success)
        self.assertEqual(result.payload["outcome"], "CONFIGURATION_ERROR")

    async def test_slow_identity_database_does_not_block_asgi_event_loop(self):
        import threading
        from starlette.requests import Request
        from starlette.responses import Response
        from app.security.scope import Principal
        from uuid import uuid4

        principal = Principal(uuid4(), "synthetic", True, {})
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/api/v1/auth/me",
                "headers": [(b"authorization", b"Bearer synthetic")],
                "query_string": b"",
            }
        )
        entered, release, finished = (
            threading.Event(),
            threading.Event(),
            threading.Event(),
        )

        def slow(token):
            entered.set()
            release.wait(2)
            finished.set()
            return principal

        async def next_handler(request):
            return Response()

        with patch("app.security.http._identify_token", slow):
            task = asyncio.create_task(
                IdentityMiddleware(lambda scope, receive, send: None).dispatch(
                    request, next_handler
                )
            )
            try:
                # If identity executes on the event loop, this await cannot run
                # until the blocking lookup times out and finished is set.
                await asyncio.wait_for(asyncio.to_thread(entered.wait, 1), 2)
                self.assertTrue(entered.is_set())
                self.assertFalse(
                    finished.is_set(), "Identity lookup blocked the ASGI event loop"
                )
                self.assertFalse(task.done())
            finally:
                release.set()
                response = await task
            self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()

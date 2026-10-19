"""Backward compatibility and fail-closed human client contracts."""

import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from app.main import app
from scripts.acceptance_scope import probe_headers


class Sprint09Contracts(unittest.TestCase):
    def test_new_archives_are_read_only_and_bounded(self):
        paths = app.openapi()["paths"]
        for path in (
            "/api/v1/unified/resources/{id}/schedule-occurrences",
            "/api/v1/unified/resources/{id}/executions/{history_id}/steps",
            "/api/v1/unified/resources/{id}/executions/{history_id}/attempts/{attempt_id}/{collection}",
            "/api/v1/data-pipelines/integrations/{id}/records/{collection}",
            "/api/v1/native-incidents/{incident_id}/activities",
        ):
            self.assertEqual(set(paths[path]), {"get"})
            params = {p["name"]: p["schema"] for p in paths[path]["get"]["parameters"]}
            self.assertEqual(params["limit"]["maximum"], 200)
            self.assertEqual(params["limit"]["minimum"], 1)
            self.assertEqual(params["offset"]["minimum"], 0)

    def test_collection_filters_use_fixed_contract_allowlists(self):
        paths = app.openapi()["paths"]
        path = "/api/v1/unified/resources/{id}/executions/{history_id}/attempts/{attempt_id}/{collection}"
        collection = next(
            p for p in paths[path]["get"]["parameters"] if p["name"] == "collection"
        )
        self.assertEqual(set(collection["schema"]["enum"]), {"aliases", "revisions"})

    def test_invalid_client_authority_never_becomes_all(self):
        with patch(
            "scripts.acceptance_scope.selection_headers",
            side_effect=HTTPError("http://local", 401, "revoked", {}, None),
        ):
            self.assertEqual(
                probe_headers("http://local", "revoked", "/api/v1/unified/resources"),
                {"X-OpsControl-Customers": ""},
            )
        with patch(
            "scripts.acceptance_scope.selection_headers",
            side_effect=HTTPError("http://local", 500, "error", {}, None),
        ):
            with self.assertRaises(HTTPError):
                probe_headers("http://local", "token", "/api/v1/unified/resources")

    def test_service_credentials_do_not_request_employee_scope(self):
        with patch("scripts.acceptance_scope.selection_headers") as lookup:
            for path in (
                "/api/v1/agent/pipeline-claim",
                "/api/v1/worker/results",
                "/api/v1/auth/me",
            ):
                self.assertEqual(probe_headers("http://local", "service", path), {})
            lookup.assert_not_called()

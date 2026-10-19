"""Static R1 contracts only; no test here certifies a genuine Pentaho runtime."""

import json
import unittest
from unittest.mock import patch

import app.main  # register existing model/security contracts
from app.data_pipelines.api import catalogue
from app.pipeline_adapters import (
    ADAPTER_DEFINITIONS,
    PLATFORM_ADAPTERS,
    AdapterError,
    describe_platform,
    validate_platform_configuration,
)
from app.pipeline_adapters.native import Pentaho
from app.pipeline_adapters.pentaho_contracts import describe_pentaho_monitoring_contract


class PentahoMonitoringContractTests(unittest.TestCase):
    def test_three_surfaces_are_read_only_and_never_runtime_verified(self):
        contract = describe_pentaho_monitoring_contract()
        self.assertEqual(contract["version"], 2)
        self.assertTrue(contract["monitoring_only"])
        self.assertFalse(contract["runtime_verified"])
        self.assertEqual(
            {s["surface"] for s in contract["surfaces"]},
            {"KITCHEN_PAN", "PENTAHO_SERVER", "CARTE"},
        )
        for surface in contract["surfaces"]:
            self.assertTrue(surface["read_only"])
            self.assertFalse(surface["runtime_verified"])
        self.assertIn("EXACT_INSTALLED_BUILD", contract["certification_requires"])
        self.assertIn("INDEPENDENT_APPROVAL", contract["certification_requires"])
        self.assertIn("GENUINE_NATIVE_EVIDENCE", contract["certification_requires"])
        json.dumps(contract)

    def test_partial_surfaces_do_not_claim_native_producers_or_live_support(
        self,
    ):
        surfaces = {
            s["surface"]: s for s in describe_pentaho_monitoring_contract()["surfaces"]
        }
        for key in ("KITCHEN_PAN", "PENTAHO_SERVER"):
            self.assertEqual(surfaces[key]["implementation_status"], "PARTIAL")
            self.assertTrue(surfaces[key]["implemented_observations"])
        carte = surfaces["CARTE"]
        self.assertEqual(carte["implementation_status"], "PARTIAL")
        self.assertTrue(carte["implemented_observations"])
        self.assertTrue(
            any("genuine runtime" in s for s in carte["proposed_observations"])
        )
        self.assertTrue(any("restart" in s for s in carte["identity_requirements"]))

    def test_consumer_mutation_cannot_rewrite_later_declarations(self):
        first = describe_platform("PENTAHO")
        first["monitoring_surface_contract"]["surfaces"][0]["runtime_verified"] = True
        first["monitoring_surface_contract"]["certification_requires"].clear()
        fresh = describe_platform("PENTAHO")["monitoring_surface_contract"]
        self.assertFalse(fresh["surfaces"][0]["runtime_verified"])
        self.assertTrue(fresh["certification_requires"])
        self.assertEqual(
            fresh, ADAPTER_DEFINITIONS["PENTAHO"]["monitoring_surface_contract"]
        )

    def test_other_eight_platform_descriptions_remain_unchanged(self):
        expected_keys = {
            "platform",
            "configuration_schema",
            "capabilities",
            "step_collection",
            "live_verified",
        }
        others = set(PLATFORM_ADAPTERS) - {"PENTAHO"}
        self.assertEqual(len(others), 8)
        for key in others:
            with self.subTest(platform=key):
                desc = describe_platform(key)
                self.assertEqual(set(desc), expected_keys)
                self.assertNotIn(
                    "monitoring_surface_contract", ADAPTER_DEFINITIONS[key]
                )
                self.assertEqual(
                    desc["capabilities"], list(PLATFORM_ADAPTERS[key].capabilities)
                )
                self.assertFalse(desc["live_verified"])

    def test_declarations_cannot_select_an_unimplemented_runtime(self):
        self.assertIs(PLATFORM_ADAPTERS["PENTAHO"], Pentaho)
        cfg = {
            "url": "https://carte.example.test",
            "job_name": "Controlled job",
            "allowed_hosts": ["carte.example.test"],
            "allowed_cidrs": ["192.0.2.0/24"],
        }
        self.assertEqual(validate_platform_configuration("PENTAHO", cfg), cfg)
        for surface in ("KITCHEN_PAN", "PENTAHO_SERVER"):
            with self.subTest(surface=surface), self.assertRaises(AdapterError):
                validate_platform_configuration(
                    "PENTAHO", {**cfg, "monitoring_surface": surface}
                )

    def test_authorized_catalogue_exposes_candidates_without_certification(self):
        with patch("app.data_pipelines.api.require_permission") as require:
            result = catalogue()
        require.assert_called_once_with("etl.view")
        platform = next(p for p in result["platforms"] if p["platform"] == "PENTAHO")
        versions = {v["version"] for v in platform["versions"]}
        self.assertTrue({"8.3", "9.3", "9.4", "10.2.x", "11.0.x"} <= versions)
        for candidate in platform["versions"]:
            self.assertTrue(candidate["candidate_only"])
            self.assertEqual(candidate["compatibility"], "UNVERIFIED")
            self.assertEqual(candidate["evidence_status"], "DOCUMENTED")
        self.assertFalse(
            platform["adapter"]["monitoring_surface_contract"]["runtime_verified"]
        )

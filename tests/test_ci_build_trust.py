"""Required build trust cannot silently disappear during CI refactoring."""
import ssl
import unittest
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
class BuildTrustTests(unittest.TestCase):
    def test_real_runner_trust_bundle_loads_without_disabling_verification(self):
        context=ssl.create_default_context(cafile='/etc/ssl/certs/ca-certificates.crt')
        self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertGreater(len(context.get_ca_certs()),0)

    def test_required_build_actions_supply_file_secret(self):
        for name in ('local-uat-image-validation.yml','v15-quality.yml'):
            data=yaml.load((ROOT/'.github/workflows'/name).read_text(),Loader=yaml.BaseLoader)
            for job in data['jobs'].values():
                for step in job.get('steps',[]):
                    if step.get('uses','').startswith('docker/build-push-action@'):
                        self.assertIn('proxy_ca=/etc/ssl/certs/ca-certificates.crt',step['with']['secret-files'])
        self.assertIn('id=proxy_ca,required=true',(ROOT/'frontend/Dockerfile.demo').read_text())
        source=(ROOT/'scripts/access-docker-demo.py').read_text()
        self.assertIn('secrets: [proxy_ca]',source)
        self.assertNotIn('"prune", "--all"',source)

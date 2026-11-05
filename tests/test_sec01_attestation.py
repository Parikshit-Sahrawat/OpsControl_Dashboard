import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'scripts/uat/pull_release.py'
spec = importlib.util.spec_from_file_location('sec01_pull_release', PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class AttestationBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'release.json'
        self.path.write_text('{"release":"test"}')
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.manifest = {'run_id': 1234, 'run_attempt': 2, 'sha': 'a'*40}
        self.uri = f'https://github.com/{m.REPO}/actions/runs/1234/attempts/2'

    def attestation(self, uri=None, digest=None):
        return [{'verificationResult': {
            'statement': {'predicateType': 'https://slsa.dev/provenance/v1',
                          'subject': [{'digest': {'sha256': digest or self.digest}}]},
            'signature': {'certificate': {'workflowRunInvocationURI': uri or self.uri}}
        }}]

    def test_verified_certificate_and_subject(self):
        self.assertEqual(m.check_attestation(self.path, self.manifest,
                         self.attestation()), self.digest)

    def test_wrong_subject_digest(self):
        with self.assertRaises(m.Rejected):
            m.check_attestation(self.path, self.manifest, self.attestation(digest='0'*64))

    def test_wrong_run_attempt_in_certificate(self):
        with self.assertRaises(m.Rejected):
            m.check_attestation(self.path, self.manifest,
                                self.attestation(uri=self.uri.replace('/attempts/2', '/attempts/1')))

    def test_missing_certificate_run_binding(self):
        result = self.attestation()
        result[0]['verificationResult']['signature']['certificate'] = {}
        result[0]['verificationResult']['statement']['predicate'] = {'run_id': 1234}
        with self.assertRaises(m.Rejected):
            m.check_attestation(self.path, self.manifest, result)

    def test_no_attestation(self):
        with self.assertRaises(m.Rejected):
            m.check_attestation(self.path, self.manifest, [])

    def run_data(self):
        return dict(id=1234, run_attempt=2, head_sha='a'*40,
                    head_branch='main', event='push', path=m.WORKFLOW,
                    repository={'full_name':m.REPO}, status='completed', conclusion='success')

    def test_authoritative_run_and_attempt(self):
        with patch.object(m, 'api', side_effect=[self.run_data(), self.run_data()]):
            self.assertEqual(m.check_workflow_run(self.manifest), 1234)

    def test_failed_attempt_rejected(self):
        bad = self.run_data(); bad['conclusion'] = 'failure'
        with patch.object(m, 'api', side_effect=[self.run_data(), bad]):
            with self.assertRaises(m.Rejected):
                m.check_workflow_run(self.manifest)

    def test_wrong_source_sha_rejected(self):
        bad = self.run_data(); bad['head_sha'] = 'b'*40
        with patch.object(m, 'api', return_value=bad):
            with self.assertRaises(m.Rejected):
                m.check_workflow_run(self.manifest)

    def test_wrong_run_attempt_rejected(self):
        bad = self.run_data(); bad['run_attempt'] = 3
        with patch.object(m, 'api', return_value=bad):
            with self.assertRaises(m.Rejected):
                m.check_workflow_run(self.manifest)

if __name__ == '__main__':
    unittest.main()

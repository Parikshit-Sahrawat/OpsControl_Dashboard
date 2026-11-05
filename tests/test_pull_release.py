import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'scripts/uat/pull_release.py'
spec = importlib.util.spec_from_file_location('pull_release', PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.sha = 'a'*40
        self.image = lambda k: f'ghcr.io/parikshit-sahrawat/opscontrol_dashboard-{k}@sha256:'+'b'*64
        self.manifest = dict(schema=1, repository=m.REPO, ref='refs/heads/main',sha=self.sha,
            workflow=m.WORKFLOW,policy='uat-pull-v1',run_id=1,run_attempt=1,
            migration_hash='c'*64,images={'backend':self.image('backend'),'frontend':self.image('frontend')})
    def test_valid_manifest(self):
        self.assertEqual(m.check_manifest(self.manifest,self.sha,None),self.sha)
    def test_replay(self):
        with self.assertRaises(m.Rejected):m.check_manifest(self.manifest,self.sha,{'sha':self.sha})
    def test_wrong_main(self):
        with self.assertRaises(m.Rejected):m.check_manifest(self.manifest,'d'*40,None)
    def test_wrong_repository(self):
        self.manifest['repository']='attacker/repo'
        with self.assertRaises(m.Rejected):m.check_manifest(self.manifest,self.sha,None)
    def test_wrong_ref(self):
        self.manifest['ref']='refs/heads/feature'
        with self.assertRaises(m.Rejected):m.check_manifest(self.manifest,self.sha,None)
    def test_wrong_workflow(self):
        self.manifest['workflow']='attacker.yml'
        with self.assertRaises(m.Rejected):m.check_manifest(self.manifest,self.sha,None)
    def test_malformed_digest(self):
        self.manifest['images']['backend']='latest'
        with self.assertRaises(m.Rejected):m.check_manifest(self.manifest,self.sha,None)
    def test_unknown_service(self):
        self.manifest['images']['postgres']=self.image('backend')
        with self.assertRaises(m.Rejected):m.check_manifest(self.manifest,self.sha,None)
    def test_missing_migration(self):
        self.manifest.pop('migration_hash')
        with self.assertRaises(m.Rejected):m.check_manifest(self.manifest,self.sha,None)
    def test_failed_ci(self):
        pr={'merged_at':'2026-10-29','base':{'ref':'main'},'merge_commit_sha':self.sha,'head':{'sha':'d'*40},'number':75}
        with patch.object(m,'api',side_effect=[ [pr], {'check_runs':[]}]):
            with self.assertRaisesRegex(m.Rejected,'mapping'):m.check_ci(self.sha)
    def test_missing_approval(self):
        pr={'merged_at':'2026-10-29','base':{'ref':'main'},'merge_commit_sha':self.sha,'head':{'sha':'d'*40},'number':75}
        runs={'check_runs':[{'name':x,'app':{'slug':'github-actions'},'conclusion':'success'} for x in m.CHECKS]}
        with patch.object(m,'api',side_effect=[[pr],runs,[]]):
            with self.assertRaisesRegex(m.Rejected,'mapping'):m.check_ci(self.sha)
    def test_atomic_json(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'state.json'
            m.atomic_json(p,{'sha':self.sha})
            self.assertIn(self.sha,p.read_text())
            self.assertEqual(p.stat().st_mode & 0o077,0)

if __name__=='__main__':unittest.main()

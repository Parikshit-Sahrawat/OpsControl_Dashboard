import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / 'scripts/uat'
spec = importlib.util.spec_from_file_location('release_handoff', ROOT / 'release_handoff.py')
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
B = 'ghcr.io/parikshit-sahrawat/opscontrol_dashboard-backend@sha256:'+'a'*64
F = 'ghcr.io/parikshit-sahrawat/opscontrol_dashboard-frontend@sha256:'+'b'*64

class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        key = self.state/'handoff.key'; key.write_bytes(b'K'*32); key.chmod(0o600)
        self.manifest = {'sha':'c'*40, 'images':{'backend':B,'frontend':F}, 'run_id':5,'run_attempt':2}
    def issue(self): return h.create(self.state, self.manifest)
    def test_valid(self): self.assertEqual(h.verify_and_consume(self.state,self.issue())['sha'],'c'*40)
    def test_missing_fd(self):
        with patch.dict(os.environ,{},clear=True),self.assertRaisesRegex(h.HandoffError,'FD required'):h.read_fd(self.state)
    def test_env_only_cannot_bypass(self):
        with patch.dict(os.environ,{'SOURCE_SHA':'c'*40,'BACKEND_IMAGE':B,'FRONTEND_IMAGE':F},clear=True),self.assertRaises(h.HandoffError):h.read_fd(self.state)
    def test_tamper_image(self):
        data=json.loads(self.issue());data['body']['images']['backend']=F
        with self.assertRaisesRegex(h.HandoffError,'authentication'):h.verify_and_consume(self.state,json.dumps(data).encode())
    def test_tamper_sha(self):
        data=json.loads(self.issue());data['body']['sha']='d'*40
        with self.assertRaises(h.HandoffError):h.verify_and_consume(self.state,json.dumps(data).encode())
    def test_tamper_run(self):
        data=json.loads(self.issue());data['body']['run_attempt']=3
        with self.assertRaises(h.HandoffError):h.verify_and_consume(self.state,json.dumps(data).encode())
    def test_replay(self):
        token=self.issue();h.verify_and_consume(self.state,token)
        with self.assertRaisesRegex(h.HandoffError,'Replayed'):h.verify_and_consume(self.state,token)
    def test_expired(self):
        token=self.issue();data=json.loads(token)
        with self.assertRaisesRegex(h.HandoffError,'Expired'):h.verify_and_consume(self.state,token,now=data['body']['issued_at']+121)
    def test_future(self):
        token=self.issue();data=json.loads(token)
        with self.assertRaisesRegex(h.HandoffError,'Expired'):h.verify_and_consume(self.state,token,now=data['body']['issued_at']-11)
    def test_missing_key(self):
        (self.state/'handoff.key').unlink()
        with self.assertRaises(FileNotFoundError):self.issue()
    def test_weak_key_permissions(self):
        (self.state/'handoff.key').chmod(0o644)
        with self.assertRaisesRegex(h.HandoffError,'permissions'):self.issue()
    def test_key_symlink(self):
        key=self.state/'handoff.key'; key.rename(self.state/'real.key'); key.symlink_to(self.state/'real.key')
        with self.assertRaisesRegex(h.HandoffError,'Symlink'):self.issue()
    def test_concurrent_replay_exactly_one_wins(self):
        token=self.issue(); barrier=threading.Barrier(8); results=[]; mutex=threading.Lock()
        def attempt():
            barrier.wait()
            try: h.verify_and_consume(self.state,token); outcome='accepted'
            except h.HandoffError: outcome='rejected'
            with mutex:results.append(outcome)
        threads=[threading.Thread(target=attempt) for _ in range(8)]
        for thread in threads:thread.start()
        for thread in threads:thread.join()
        self.assertEqual(results.count('accepted'),1)
        self.assertEqual(results.count('rejected'),7)
    def test_oversize(self):
        with self.assertRaisesRegex(h.HandoffError,'Oversized'):h.verify_and_consume(self.state,b'x'*8193)

if __name__=='__main__':unittest.main()

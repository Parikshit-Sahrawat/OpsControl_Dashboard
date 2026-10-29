import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

P = Path(__file__).resolve().parents[1] / 'scripts/uat/local_auto_deploy.py'
spec=importlib.util.spec_from_file_location('local_auto_deploy',P)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
B='ghcr.io/parikshit-sahrawat/opscontrol_dashboard-backend@sha256:'+'a'*64
F='ghcr.io/parikshit-sahrawat/opscontrol_dashboard-frontend@sha256:'+'b'*64

class DeployTests(unittest.TestCase):
    def test_app_only_commands(self):
        calls=[]
        def fake_run(*args,**kwargs):
            calls.append(args)
            if args[-3:]==('config','--format','json'):
                return json.dumps({'services':{
                    'api':{'image':B},'worker':{'image':B},'frontend':{'image':F},
                    'postgres':{},'ingestion-gateway':{}}})
            return ''
        with patch.object(m,'run',side_effect=fake_run),patch.object(m,'check_url') as health, patch.object(m,'check_worker') as worker:
            m.deploy_images(('docker','compose'),{},B,F,['http://127.0.0.1/health'])
        self.assertEqual(len(calls),3)
        self.assertEqual(calls[1][-3:],('api','worker','frontend'))
        self.assertEqual(calls[2][-3:],('api','worker','frontend'))
        self.assertIn('--no-deps',calls[2])
        health.assert_called_once()
    def test_unexpected_service_image_rejected(self):
        wrong={'services':{'api':{'image':'wrong'},'worker':{'image':B},
            'frontend':{'image':F},'postgres':{},'ingestion-gateway':{}}}
        with patch.object(m,'run',return_value=json.dumps(wrong)):
            with self.assertRaisesRegex(RuntimeError,'Unexpected'):m.config(('docker','compose'),{},B,F)
    def test_no_build_allowed(self):
        wrong={'services':{'api':{'image':B,'build':{'context':'/tmp'}},'worker':{'image':B},
            'frontend':{'image':F},'postgres':{},'ingestion-gateway':{}}}
        with patch.object(m,'run',return_value=json.dumps(wrong)):
            with self.assertRaisesRegex(RuntimeError,'Unexpected'):m.config(('docker','compose'),{},B,F)
    def test_atomic_last_known_good(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'last.json';m.atomic(p,{'sha':'a'*40})
            self.assertEqual(json.loads(p.read_text())['sha'],'a'*40)
            self.assertEqual(p.stat().st_mode & 0o077,0)

if __name__=='__main__':unittest.main()

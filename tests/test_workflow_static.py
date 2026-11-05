from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class WorkflowTests(unittest.TestCase):
    def test_hosted_only(self):
        s=(ROOT/'.github/workflows/local-uat-auto-deploy.yml').read_text()
        self.assertNotIn('self-hosted',s)
        self.assertIn('runs-on: ubuntu-24.04',s)
        self.assertIn("github.ref == 'refs/heads/main'",s)
        self.assertIn('actions/attest@',s)
        self.assertIn('steps.backend.outputs.digest',s)
    def test_timer_not_enabled_by_default(self):
        s=(ROOT/'deploy/uat/opscontrol-uat-pull.service').read_text()
        self.assertIn('LOCAL_UAT_PULL_ENABLED=false',s)

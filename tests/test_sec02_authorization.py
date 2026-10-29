import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

P = Path(__file__).resolve().parents[1] / 'scripts/uat/pull_release.py'
spec = importlib.util.spec_from_file_location('sec02_controller', P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
SHA = 'a' * 40
HEAD = 'b' * 40
TRUST = {n: '.github/workflows/validation.yml' for n in m.CHECKS}

class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.protection = {'enforce_admins': {'enabled': True},
            'required_pull_request_reviews': {'required_approving_review_count': 1,
                'dismiss_stale_reviews': True, 'require_last_push_approval': True},
            'required_status_checks': {'strict': True}}
        self.pr = {'number': 75, 'merged_at': '2026-10-29',
            'base': {'ref': 'main', 'repo': {'full_name': m.REPO}},
            'merge_commit_sha': SHA}
        self.detail = dict(self.pr, merged=True, head={'sha': HEAD}, user={'login': 'author'})
        self.reviews = [{'user': {'login': 'reviewer'}, 'state': 'APPROVED', 'commit_id': HEAD}]
        self.checks = [{'name': n, 'head_sha': HEAD, 'status': 'completed',
            'conclusion': 'success', 'app': {'id': m.ACTIONS_APP_ID},
            'check_suite': {'id': i+1}} for i,n in enumerate(sorted(m.CHECKS))]
        self.responses = [self.protection, [], [self.pr], self.detail, self.reviews,
                          {'total_count': len(self.checks), 'check_runs': self.checks}]
        for i in range(len(self.checks)):
            self.responses.extend([{'head_sha': HEAD, 'app': {'id': m.ACTIONS_APP_ID},
                                     'workflow_run': {'id': i+101}},
                                   {'head_sha': HEAD, 'event': 'pull_request',
                                    'path': '.github/workflows/validation.yml',
                                    'status': 'completed', 'conclusion': 'success',
                                    'repository': {'full_name': m.REPO}}])
    def evaluate(self, responses=None, trust=TRUST):
        with patch.object(m, 'api', side_effect=responses or self.responses):
            return m.check_ci(SHA, trusted_workflows=trust)
    def test_valid_fixture(self): self.assertEqual(self.evaluate(), 75)
    def test_unapproved_mapping(self):
        with self.assertRaisesRegex(m.Rejected, 'mapping'): self.evaluate(trust={})
    def test_admin_bypass(self):
        self.protection['enforce_admins']['enabled'] = False
        with self.assertRaisesRegex(m.Rejected, 'administrators'): self.evaluate()
    def test_stale_reviews_allowed(self):
        self.protection['required_pull_request_reviews']['dismiss_stale_reviews'] = False
        with self.assertRaisesRegex(m.Rejected, 'review protection'): self.evaluate()
    def test_last_push_approval_not_required(self):
        self.protection['required_pull_request_reviews']['require_last_push_approval'] = False
        with self.assertRaisesRegex(m.Rejected, 'review protection'): self.evaluate()
    def test_ruleset_requires_audit(self):
        self.responses[1] = [{'id': 42}]
        with self.assertRaisesRegex(m.Rejected, 'Ruleset'): self.evaluate()
    def test_stale_review_commit(self):
        self.reviews[0]['commit_id'] = 'c'*40
        with self.assertRaisesRegex(m.Rejected, 'approving'): self.evaluate()
    def test_self_approval(self):
        self.reviews[0]['user']['login'] = 'author'
        with self.assertRaisesRegex(m.Rejected, 'approving'): self.evaluate()
    def test_requested_changes(self):
        self.reviews.append({'user': {'login': 'other'}, 'state': 'CHANGES_REQUESTED', 'commit_id': HEAD})
        with self.assertRaisesRegex(m.Rejected, 'changes requested'): self.evaluate()
    def test_failed_check(self):
        self.checks[0]['conclusion'] = 'failure'
        with self.assertRaisesRegex(m.Rejected, 'Failed or untrusted'): self.evaluate()
    def test_wrong_check_sha(self):
        self.checks[0]['head_sha'] = 'c'*40
        with self.assertRaisesRegex(m.Rejected, 'Failed or untrusted'): self.evaluate()
    def test_fake_actions_app(self):
        self.checks[0]['app']['id'] = 999
        with self.assertRaisesRegex(m.Rejected, 'Failed or untrusted'): self.evaluate()
    def test_duplicate_check(self):
        self.checks.append(dict(self.checks[0])); self.responses[5]['total_count'] += 1
        with self.assertRaisesRegex(m.Rejected, 'ambiguous'): self.evaluate()
    def test_incomplete_check_pagination(self):
        self.responses[5]['total_count'] += 1
        with self.assertRaisesRegex(m.Rejected, 'pagination'): self.evaluate()
    def test_wrong_workflow(self):
        self.responses[7]['path'] = '.github/workflows/untrusted.yml'
        with self.assertRaisesRegex(m.Rejected, 'provenance'): self.evaluate()
    def test_wrong_workflow_event(self):
        self.responses[7]['event'] = 'workflow_dispatch'
        with self.assertRaisesRegex(m.Rejected, 'provenance'): self.evaluate()
    def test_missing_protection(self):
        self.responses[0] = {}
        with self.assertRaises(m.Rejected): self.evaluate()
    def test_ambiguous_pr(self):
        self.responses[2] = [self.pr, dict(self.pr)]
        with self.assertRaisesRegex(m.Rejected, 'unique'): self.evaluate()

if __name__ == '__main__': unittest.main()

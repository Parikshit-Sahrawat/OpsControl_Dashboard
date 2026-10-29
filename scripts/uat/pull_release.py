#!/usr/bin/env python3
"""Fail-closed, disabled-by-default UAT release discovery and authorization.

Requires gh >= 2.63 with attestation support, authenticated read-only GHCR/GitHub
access, and a separately reviewed, protected local deployment configuration.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

REPO = 'Parikshit-Sahrawat/OpsControl_Dashboard'
WORKFLOW = '.github/workflows/local-uat-auto-deploy.yml'
CHECKS = frozenset(('frontend-build', 'frontend-dependency-audit', 'image-validation',
    'contracts', 'python-dependency-audit', 'secret-history-scan', 'staging-smoke',
    'private-https', 'verification', 'pipeline-contracts', 'restore-retention-tls',
    'access-rbac', 'noc'))
SHA = re.compile(r'[a-f0-9]{40}\Z')
DIGEST = re.compile(r'ghcr\.io/parikshit-sahrawat/opscontrol_dashboard-(backend|frontend)@sha256:[a-f0-9]{64}\Z')

class Rejected(RuntimeError):
    pass

def command(*args, timeout=90):
    p = subprocess.run(args, text=True, capture_output=True, timeout=timeout, check=False)
    if p.returncode:
        raise Rejected(f'Command failed ({args[0]} {args[1] if len(args)>1 else ""}): exit {p.returncode}')
    return p.stdout

def api(path):
    if not path.startswith(f'repos/{REPO}/'):
        raise Rejected('Unexpected GitHub API route')
    return json.loads(command('gh', 'api', path, '--method', 'GET'))

def require(condition, reason):
    if not condition:
        raise Rejected(reason)

def check_manifest(m, main_sha, last):
    require(isinstance(m, dict) and m.get('schema') == 1, 'Unsupported manifest')
    require(m.get('repository') == REPO and m.get('ref') == 'refs/heads/main', 'Wrong repository/ref')
    sha = m.get('sha')
    require(isinstance(sha, str) and SHA.fullmatch(sha) and sha == main_sha, 'Release is not current main')
    require(m.get('workflow') == WORKFLOW and m.get('policy') == 'uat-pull-v1', 'Wrong workflow/policy')
    require(isinstance(m.get('run_id'), int) and m['run_id'] > 0, 'Invalid run')
    require(isinstance(m.get('run_attempt'), int) and m['run_attempt'] > 0, 'Invalid attempt')
    require(isinstance(m.get('migration_hash'), str) and re.fullmatch('[a-f0-9]{64}', m['migration_hash']), 'Invalid migration hash')
    images = m.get('images')
    require(isinstance(images, dict) and set(images) == {'backend','frontend'}, 'Unexpected image set')
    for key, image in images.items():
        require(isinstance(image, str) and DIGEST.fullmatch(image) and f'-{key}@' in image, 'Invalid image digest')
    require(last is None or last.get('sha') != sha, 'Already deployed (replay)')
    return sha

# SECURITY POLICY: reviewed check-name -> GitHub Actions workflow-path mapping.
# Deliberately empty until repository owners approve exact job/workflow identities.
# Never infer trusted workflow identity from the check name or a user-controlled URL.
TRUSTED_CHECK_WORKFLOWS = {}
ACTIONS_APP_ID = 15368


def check_ci(sha, trusted_workflows=None):
    """Fail closed on branch protections, effective approvals, and check provenance.

    Requires an owner-reviewed mapping of each required job to its workflow path.
    Repository rulesets and bypass permissions require a separate approval audit.
    """
    trusted = TRUSTED_CHECK_WORKFLOWS if trusted_workflows is None else trusted_workflows
    require(isinstance(trusted, dict) and set(trusted) == CHECKS and
            all(isinstance(v, str) and v.startswith('.github/workflows/') and
                v.endswith(('.yml', '.yaml')) for v in trusted.values()),
            'Trusted workflow mapping not approved or incomplete')
    protection = api(f'repos/{REPO}/branches/main/protection')
    reviews_rule = protection.get('required_pull_request_reviews') or {}
    require(protection.get('enforce_admins', {}).get('enabled') is True,
            'Branch protection must apply to administrators')
    require(reviews_rule.get('required_approving_review_count', 0) >= 1 and
            reviews_rule.get('dismiss_stale_reviews') is True and
            reviews_rule.get('require_last_push_approval') is True,
            'Effective review protection is insufficient')
    require(protection.get('required_status_checks', {}).get('strict') is True,
            'Up-to-date required checks must be enforced')
    # GitHub protection API does not establish the absence of ruleset bypasses.
    # Until an independent ruleset/bypass audit is implemented, reject if rulesets
    # exist rather than assume protection settings alone prove authorization.
    rulesets = api(f'repos/{REPO}/rulesets?includes_parents=true')
    require(isinstance(rulesets, list) and not rulesets,
            'Ruleset authorization/bypass audit required')

    prs = api(f'repos/{REPO}/commits/{sha}/pulls')
    require(isinstance(prs, list), 'Invalid merged PR response')
    prs = [p for p in prs if p.get('merged_at') and
           p.get('base', {}).get('ref') == 'main' and
           p.get('base', {}).get('repo', {}).get('full_name', REPO).lower() == REPO.lower() and
           p.get('merge_commit_sha') == sha]
    require(len(prs) == 1, 'No unique merged PR for main SHA')
    pr = prs[0]
    number = pr['number']
    detail = api(f'repos/{REPO}/pulls/{number}')
    require(detail.get('merged') is True and detail.get('merge_commit_sha') == sha and
            detail.get('base', {}).get('ref') == 'main', 'Merged PR detail mismatch')
    head = detail.get('head', {}).get('sha')
    require(isinstance(head, str) and SHA.fullmatch(head), 'Invalid PR head SHA')
    author = (detail.get('user') or {}).get('login', '').lower()
    require(bool(author), 'Missing PR author')
    reviews = api(f'repos/{REPO}/pulls/{number}/reviews?per_page=100')
    require(isinstance(reviews, list) and len(reviews) < 100,
            'Review pagination incomplete')
    latest = {}
    for review in reviews:
        user = (review.get('user') or {}).get('login', '').lower()
        if user and review.get('state') in ('APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'):
            latest[user] = review
    approvals = [r for user, r in latest.items() if user != author and
                 r.get('state') == 'APPROVED' and r.get('commit_id') == head]
    require(len(approvals) >= reviews_rule['required_approving_review_count'],
            'Missing current independent approving reviews for PR head')
    require(not any(r.get('state') == 'CHANGES_REQUESTED' for r in latest.values()),
            'Unresolved changes requested')

    checks = api(f'repos/{REPO}/commits/{head}/check-runs?per_page=100')
    runs = checks.get('check_runs', [])
    require(checks.get('total_count') == len(runs) and len(runs) < 100,
            'Check-run pagination incomplete')
    for name in CHECKS:
        matches = [r for r in runs if r.get('name') == name]
        require(len(matches) == 1, f'Missing or ambiguous required check: {name}')
        check = matches[0]
        require(check.get('head_sha') == head and check.get('status') == 'completed' and
                check.get('conclusion') == 'success' and
                (check.get('app') or {}).get('id') == ACTIONS_APP_ID,
                f'Failed or untrusted check: {name}')
        suite_id = check.get('check_suite', {}).get('id')
        require(isinstance(suite_id, int), f'Missing check suite: {name}')
        suite = api(f'repos/{REPO}/check-suites/{suite_id}')
        require(suite.get('head_sha') == head and
                (suite.get('app') or {}).get('id') == ACTIONS_APP_ID,
                f'Untrusted check suite: {name}')
        run_id = suite.get('workflow_run', {}).get('id')
        require(isinstance(run_id, int), f'No workflow run for check: {name}')
        workflow_run = api(f'repos/{REPO}/actions/runs/{run_id}')
        require(workflow_run.get('head_sha') == head and
                workflow_run.get('event') == 'pull_request' and
                workflow_run.get('path') == trusted[name] and
                workflow_run.get('status') == 'completed' and
                workflow_run.get('conclusion') == 'success' and
                workflow_run.get('repository', {}).get('full_name', '').lower() == REPO.lower(),
                f'Wrong workflow provenance: {name}')
    return number


def check_attestation(manifest_path, manifest, verified):
    """Bind exact release bytes to certificate-authenticated workflow invocation.

    Deliberately fail closed if GitHub changes the verified JSON certificate shape.
    Never use predicate-provided run IDs as authentication evidence.
    """
    require(isinstance(verified, list) and verified, 'No verified attestations')
    digest = hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest()
    run_id, attempt = manifest['run_id'], manifest['run_attempt']
    expected_invocation = f'https://github.com/{REPO}/actions/runs/{run_id}/attempts/{attempt}'
    for entry in verified:
        result = entry.get('verificationResult', {}) if isinstance(entry, dict) else {}
        statement = result.get('statement', {})
        subjects = statement.get('subject', [])
        subject_ok = any(isinstance(subject, dict) and
                         subject.get('digest', {}).get('sha256') == digest
                         for subject in subjects)
        if not subject_ok or statement.get('predicateType') != 'https://slsa.dev/provenance/v1':
            continue
        certificate = result.get('signature', {}).get('certificate', {})
        # Only verified certificate metadata can bind the run. The workflow
        # predicate and release.json are not trusted for this purpose.
        def cert_values(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in ('workflowRunInvocationURI', 'workflow_run_invocation_uri',
                               'runInvocationURI') and isinstance(value, str):
                        yield value
                    if isinstance(value, (dict, list)):
                        yield from cert_values(value)
            elif isinstance(node, list):
                for value in node:
                    yield from cert_values(value)
        if expected_invocation in set(cert_values(certificate)):
            return digest
    raise Rejected('Attestation subject or certificate run invocation mismatch')


def check_workflow_run(manifest):
    """Check GitHub's authoritative run and exact attempt, not a workflow name."""
    run_id, attempt = manifest['run_id'], manifest['run_attempt']
    run = api(f'repos/{REPO}/actions/runs/{run_id}')
    require(run.get('id') == run_id and run.get('run_attempt') == attempt,
            'Workflow run ID/attempt mismatch')
    require(run.get('head_sha') == manifest['sha'] and
            run.get('head_branch') == 'main' and run.get('event') == 'push',
            'Workflow run source mismatch')
    require(run.get('path') == WORKFLOW and
            run.get('repository', {}).get('full_name', '').lower() == REPO.lower(),
            'Workflow run identity mismatch')
    require(run.get('status') == 'completed' and run.get('conclusion') == 'success',
            'Workflow run not successful')
    exact = api(f'repos/{REPO}/actions/runs/{run_id}/attempts/{attempt}')
    require(exact.get('id') == run_id and exact.get('run_attempt') == attempt and
            exact.get('head_sha') == manifest['sha'] and
            exact.get('status') == 'completed' and exact.get('conclusion') == 'success',
            'Workflow attempt not successful')
    return run_id

def atomic_json(path, data):
    path = Path(path)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='.release-', delete=False) as f:
        tmp = Path(f.name)
        os.chmod(tmp, 0o600)
        json.dump(data, f, sort_keys=True)
        f.write('\n')
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)

def audit(state, event):
    record = dict(event, time=int(time.time()))
    with (state / 'pull-audit.jsonl').open('a', encoding='utf-8') as f:
        os.chmod(f.name, 0o600)
        f.write(json.dumps(record, sort_keys=True) + '\n')
        f.flush(); os.fsync(f.fileno())

def discover(state, dry_run=True):
    require(os.environ.get('LOCAL_UAT_PULL_ENABLED') == 'true' or dry_run,
            'Pull controller not enabled')
    require(state.is_dir() and not state.is_symlink() and not state.stat().st_mode & 0o077,
            'Private state directory required')
    approved = state / 'approved-migration-hash'
    require(approved.is_file() and not approved.is_symlink(), 'Missing independent migration approval')
    main_sha = api(f'repos/{REPO}/branches/main')['commit']['sha']
    require(isinstance(main_sha, str) and SHA.fullmatch(main_sha), 'Invalid main SHA')
    tag = f'uat-{main_sha}'
    with tempfile.TemporaryDirectory(prefix='opscontrol-pull-') as td:
        command('gh', 'release', 'download', tag, '--repo', REPO,
                '--pattern', 'release.json', '--dir', td)
        manifest_path = Path(td) / 'release.json'
        require(manifest_path.is_file() and manifest_path.stat().st_size < 32768, 'Missing/oversized manifest')
        # Verifies Sigstore attestation for exact release.json bytes, expected repo
        # and signer workflow. No unsigned fallback is permitted.
        m = json.loads(manifest_path.read_text())
        # Verify source identity in the signed certificate, not just the manifest.
        verified = json.loads(command('gh', 'attestation', 'verify', str(manifest_path),
            '--repo', REPO, '--signer-workflow', REPO + '/' + WORKFLOW,
            '--source-digest', main_sha, '--source-ref', 'refs/heads/main',
            '--deny-self-hosted-runners', '--format', 'json'))
        check_attestation(manifest_path, m, verified)
    last_path = state / 'last-deployment.json'
    last = json.loads(last_path.read_text()) if last_path.exists() else None
    sha = check_manifest(m, main_sha, last)
    require(approved.read_text().strip() == m['migration_hash'], 'Migration baseline changed')
    check_workflow_run(m)
    pr_number = check_ci(sha)
    require(api(f'repos/{REPO}/branches/main')['commit']['sha'] == sha, 'Main moved during verification')
    if dry_run:
        audit(state, {'outcome':'ELIGIBLE_DRY_RUN','sha':sha,'pr':pr_number})
        return m
    require(os.environ.get('LOCAL_UAT_LIVE_APPROVED') == 'true', 'Initial live deployment not approved')
    # Release identity travels only through an authenticated one-use inherited FD.
    # SEC-04 must provision the private handoff.key before any activation.
    from release_handoff import create
    handoff = create(state, m)
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, handoff)
    finally:
        os.close(write_fd)
    env = os.environ.copy()
    for name in ('SOURCE_SHA', 'BACKEND_IMAGE', 'FRONTEND_IMAGE'):
        env.pop(name, None)
    env['LOCAL_UAT_HANDOFF_FD'] = str(read_fd)
    env['LOCAL_UAT_STATE_DIR'] = str(state)
    script = Path(__file__).with_name('local_auto_deploy.py')
    try:
        p = subprocess.run(['python3', str(script)], env=env, pass_fds=(read_fd,),
                           check=False, timeout=900)
    finally:
        os.close(read_fd)
    require(p.returncode == 0, 'Deployment or rollback failed')
    audit(state, {'outcome':'DEPLOYED','sha':sha,'pr':pr_number})
    return m

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', required=True, type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    require(not args.state_dir.is_symlink(), 'Symlink state directory rejected')
    state = args.state_dir.resolve(strict=True)
    with (state / 'pull-controller.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            m = discover(state, args.dry_run)
            print(json.dumps({'status':'ELIGIBLE_DRY_RUN','sha':m['sha']}))
        except Exception as e:
            audit(state, {'outcome':'REJECTED','reason':str(e)})
            raise

if __name__ == '__main__':
    main()

"""Bounded documentation/evidence checks; never grants runtime/release acceptance."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def validate(verify_manifest=True):
    checks = {}
    files = [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    for p in files:
        if p.suffix == '.json':
            json.loads(p.read_text())
    checks['json_validity'] = True
    for p in HERE.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', p.read_text()):
            if '://' in target or target.startswith('#'):
                continue
            assert (p.parent / target.split('#')[0]).exists(), (p.name, target)
    checks['markdown_links'] = True
    sources = json.loads((HERE / 'SOURCE_SHA256.json').read_text())
    for path, expected in sources['files'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    checks['exact_source_file_hashes'] = True
    results = json.loads((HERE / 'TEST_RESULTS.json').read_text())
    assert results['broad_backend']['passed'] + results['broad_backend']['skipped'] == results['broad_backend']['run'] == 564
    assert results['gates'] == {'CHK-001': 'FAIL', 'CHK-002': 'BLOCKED', 'SECURITY': 'BLOCKED', 'RELEASE': 'NO-GO', 'UAT': 'PENDING', 'owner_selections': '9_PENDING'}
    for folder in ['final', 'final-visual', 'final-workspace']:
        for filename, count in [('api.json', 15), ('workspace-ui.json', 9), ('resource-security.json', 7)]:
            data = json.loads((HERE / 'evidence' / folder / filename).read_text())
            assert data['status'] == 'PASS' and len(data['checks']) == count
        cleanup = json.loads((HERE / 'evidence' / folder / 'cleanup.json').read_text())
        assert all(cleanup[k] for k in ['container_removed', 'api_stopped', 'ui_stopped', 'private_fixtures_removed'])
    assert 'Ran 564 tests' in (HERE / results['broad_backend']['evidence']).read_text()
    assert 'OK (skipped=2)' in (HERE / results['broad_backend']['evidence']).read_text()
    assert 'tests 44' in (HERE / 'evidence/frontend-final-workspace-tests.log').read_text()
    assert not list(HERE.rglob('*.dump'))
    checks['result_counts_cleanup_and_gate_consistency'] = True
    workflow = yaml.load((ROOT / '.github/workflows/resource-workspace.yml').read_text(), Loader=yaml.BaseLoader)
    assert workflow['permissions'] == {'contents': 'read'}
    assert 'pull_request' in workflow['on'] and 'workflow_dispatch' in workflow['on']
    for step in workflow['jobs']['authenticated-workspace']['steps']:
        if 'run' in step:
            subprocess.run(['bash', '-n'], input=step['run'], text=True, check=True)
    checks['workflow_yaml_and_embedded_shell_syntax'] = True
    tracked = json.loads((HERE / 'CHANGED_FILES.json').read_text())
    assert len(tracked) == len(set(tracked)) and all((ROOT / p).is_file() for p in tracked)
    checks['changed_file_inventory'] = True
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    checks['diff_whitespace'] = True
    manifest = HERE / 'ARTIFACT_SHA256.json'
    if verify_manifest and manifest.exists():
        records = json.loads(manifest.read_text())
        inventory = {str(p.relative_to(HERE)): p for p in files if p != manifest}
        assert records.keys() == inventory.keys(), 'Manifest incomplete'
        for name, p in inventory.items():
            assert hashlib.sha256(p.read_bytes()).hexdigest() == records[name], name
        checks['artifact_manifest'] = True
    return {'status': 'PASS', 'checks': checks, 'source_commit': sources['application_source_commit'], 'limitations': ['Documentation checks, not acceptance/security/provider certification', 'Hosted CI result pending under Trigger-and-Exit', 'Two actual collector runtime tests remain skipped; audit and unrestricted lint failures retained']}


if __name__ == '__main__':
    print(json.dumps(validate(), indent=2))

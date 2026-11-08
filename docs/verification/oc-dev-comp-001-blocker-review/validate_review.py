"""Evidence/traceability validation, not owner acceptance or release certification."""
from pathlib import Path
import csv
import hashlib
import json
import re
import subprocess
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VISUAL = HERE.parent / 'oc-dev-comp-001-visual-correction'


def validate(manifests=True):
    checks = {}
    for directory in [HERE, VISUAL]:
        for p in directory.rglob('*.json'):
            json.loads(p.read_text())
        for p in directory.glob('*.md'):
            for target in re.findall(r'\]\(([^)]+)\)', p.read_text()):
                if '://' not in target and not target.startswith('#'):
                    assert (p.parent / target.split('#')[0]).exists(), (p, target)
    checks['json_and_markdown_links'] = True
    records = json.loads((HERE / 'REMAINING_WORK_REGISTER.json').read_text())
    with (HERE / 'REMAINING_WORK_REGISTER.csv').open() as f:
        assert list(csv.DictReader(f)) == records
    allowed = {'IMPLEMENTED_VERIFIED', 'IMPLEMENTED_UNVERIFIED', 'PARTIAL', 'NOT_IMPLEMENTED', 'BLOCKED_DECISION', 'BLOCKED_DEPENDENCY', 'BLOCKED_TESTING'}
    assert len({r['review_id'] for r in records}) == len(records) == 23
    assert all(r['current_state'] in allowed and all(r.values()) for r in records)
    checks['register_uniqueness_status_fields_and_csv_json_agreement'] = True
    source = json.loads((HERE / 'SOURCE_REFERENCES.json').read_text())
    for r in source['references']:
        assert hashlib.sha256((ROOT / r['path']).read_bytes()).hexdigest() == r['sha256']
        data = subprocess.check_output(['git', 'show', source['review_baseline'] + ':' + r['path']], cwd=ROOT)
        assert hashlib.sha256(data).hexdigest() == r['sha256']
    checks['review_source_provenance'] = True
    ids = json.loads((VISUAL / 'SOURCE_IDENTITIES.json').read_text())
    for p, sha in ids['source_files'].items():
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == sha, p
    assert not ids['backend_and_agent_changes']
    assert not subprocess.check_output(['git', 'diff', '--name-only', ids['baseline'], 'HEAD', '--', 'backend', 'agent', '.github/workflows', 'docs/verification/oc-dev-comp-001', 'docs/verification/oc-dev-comp-000'], cwd=ROOT).strip()
    checks['protected_backend_runtime_workflows_and_prior_evidence_unchanged'] = True
    for role in ['admin', 'operator']:
        for w, h in [(1920,1080),(1440,900),(1366,768)]:
            with Image.open(VISUAL / f'evidence/final-roles-02/{role}-desktop-{w}x{h}.png') as im:
                assert im.size == (w,h)
    checks['exact_desktop_screenshot_dimensions'] = True
    for folder in ['final', 'final-roles-02', 'legacy-navigation']:
        clean = json.loads((VISUAL / f'evidence/{folder}/cleanup.json').read_text())
        assert all(clean[k] for k in ['container_removed','api_stopped','ui_stopped','private_fixtures_removed'])
    assert not list(VISUAL.rglob('*.dump'))
    ws = json.loads((VISUAL / 'evidence/final-roles-02/workspace-ui.json').read_text())
    assert ws['status'] == 'PASS' and len(ws['checks']) == 12
    a11y = json.loads((VISUAL / 'evidence/final-roles-02/accessibility-checks.json').read_text())
    assert a11y['checkedControls'] >= 20 and not a11y['duplicateIds'] and not a11y['unnamedControls'] and not a11y['brokenControls']
    for width in [1366,1440,1920]:
        geometry = json.loads((VISUAL / f'evidence/final-roles-02/admin-geometry-{width}.json').read_text())
        assert not geometry['overflow'] and max(geometry['fields']) - min(geometry['fields']) < 2
    results = json.loads((VISUAL / 'TEST_RESULTS.json').read_text())
    assert results['gates'] == {'CHK-001':'FAIL','CHK-002':'BLOCKED','SECURITY':'BLOCKED','RELEASE':'NO-GO'}
    assert results['previous_visual_acceptance'] == 'REJECTED' and not results['sprint_complete']
    assert 'Ran 68 tests' in (VISUAL / 'evidence/final/ownership.txt').read_text()
    assert 'tests 46' in (VISUAL / 'evidence/final-frontend-tests.log').read_text()
    checks['runtime_evidence_counts_geometry_accessibility_cleanup_and_gate_consistency'] = True
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    checks['diff_whitespace'] = True
    if manifests:
        for directory in [HERE,VISUAL]:
            manifest = directory / 'ARTIFACT_SHA256.json'
            actual = {str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.rglob('*')) if p.is_file() and p != manifest and '__pycache__' not in p.parts}
            assert json.loads(manifest.read_text()) == actual
        checks['artifact_manifests'] = True
    return {'status':'PASS','checks':checks,'review_items':len(records),'source_commit':ids['implementation_and_test_head'],'limits':['Assessment only for backend/database work','Prior owner visual acceptance REJECTED; revised candidate pending owner review','Hosted CI result pending under Trigger-and-Exit','No formal UAT, provider or release certification']}


if __name__ == '__main__':
    print(json.dumps(validate(),indent=2))

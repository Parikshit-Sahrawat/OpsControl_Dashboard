"""Audit-only validation; no provider/runtime/DB actions or product edits."""
from pathlib import Path
import csv
import hashlib
import json
import re
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
MAIN = 'ffe5ac285ab8aef33a1139bce6f3da79be3d6d33'
PR = '958193f266c89302b2f1919e3703faece591e0af'

def load(name):
    return json.loads((OUT / name).read_text())

def source(sha, path):
    return subprocess.check_output(['git', 'show', sha + ':' + path], cwd=ROOT)

for path in OUT.rglob('*.json'):
    json.loads(path.read_text())
rows = load('REQUIREMENTS_GAP_MATRIX.json')
coverage = load('AUTOMATED_TEST_COVERAGE_MATRIX.json')
backlog = load('MASTER_DEVELOPMENT_BACKLOG.json')
prior = json.loads(source(MAIN, 'docs/verification/stage-2a-full-development-closure/requirements.json'))
ci = json.loads(source(PR, 'docs/verification/ci-roadmap-alignment/CI_REQUIREMENTS_MATRIX.json'))
expected = {r['id'] for r in prior} | {r['id'] for r in ci['requirements']}
assert len(rows) == 158 and {r['requirement_id'] for r in rows} == expected
assert len({r['requirement_id'] for r in rows}) == len(rows)
assert {r['requirement_id'] for r in coverage} == expected
valid = set('IMPLEMENTED_AUTOMATED_VERIFIED IMPLEMENTED_TEST_GAP PARTIALLY_IMPLEMENTED NOT_IMPLEMENTED BLOCKED_EXTERNAL_DEPENDENCY REQUIREMENT_AUTHORITY_PENDING SOURCE_NOT_RECOVERED SUPERSEDED_OR_EXCLUDED'.split())
assert all(r['classification'] in valid and r['module'] and r['evidence'] for r in rows)
for filename, objects in [('REQUIREMENTS_GAP_MATRIX.csv', rows), ('AUTOMATED_TEST_COVERAGE_MATRIX.csv', coverage), ('MASTER_DEVELOPMENT_BACKLOG.csv', backlog)]:
    with (OUT / filename).open(newline='') as file:
        actual = list(csv.DictReader(file))
    assert len(actual) == len(objects), filename
    for a, obj in zip(actual, objects):
        assert set(a) == set(obj), filename
        assert a == {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v) for k, v in obj.items()}, filename
ids = {b['id'] for b in backlog}
assert len(ids) == len(backlog) == 55
required = set('id task_type module requirements current_state gap priority dependencies coding_scope automated_tests acceptance_criteria risk estimate evidence source_sha'.split())
for b in backlog:
    assert required <= set(b) and all(b[k] for k in required - {'dependencies'}), b['id']
    assert set(b['requirements']) <= expected
    assert set(b['dependencies']) <= ids
    assert b['priority'] in {'P0', 'P1', 'P2'}
    if b['task_type'] in {'EXTERNAL_QUALIFICATION', 'FORMAL_UAT'}:
        assert b['estimate'] == 'UNESTIMATED'
for r in rows:
    assert set(r['backlog_ids']) <= ids
    for id in r['backlog_ids']:
        assert r['requirement_id'] in next(b for b in backlog if b['id'] == id)['requirements'], (r['requirement_id'], id)
done = set()
def visit(id, chain=()):
    assert id not in chain, ('cycle', chain, id)
    if id not in done:
        for dep in next(b for b in backlog if b['id'] == id)['dependencies']:
            visit(dep, chain + (id,))
        done.add(id)
for id in ids:
    visit(id)
journeys = load('JOURNEY_SCOPE.json')
assert sum(j['scope'] == 'INCLUDED' for j in journeys) == 31
assert sum(j['source'] == 'SOURCE_NOT_RECOVERED' for j in journeys) == 30
assert journeys[19]['scope'] == 'EXCLUDED' and journeys[31]['scope'] == 'SKIPPED'
assert sum(r['classification'] == 'SOURCE_NOT_RECOVERED' for r in rows) == 62
assert len(load('HISTORICAL_DEFECT_DISPOSITION.json')) == 39
nine = set('RM-01 RM-04 RM-05 AM-01 CMP-01 CMP-02 API-01 OPS-03 UI-010'.split())
assert {r['id'] for r in ci['requirements'] if r['owner'] == 'OWNER_APPROVED_CONTROLLED_SCOPE — INDEPENDENT_UAT_PENDING'} == nine
assert all(r['owner_acceptance_selection'] == 'Pending' for r in rows if r['requirement_id'] in nine)
assert b'RUNTIME_VERSION = "0.123.0"' in source(PR, 'agent/opscontrol_agent.py')
for path in ['agent/opscontrol_agent.py', 'backend/app/telemetry/configuration.py']:
    assert source(MAIN, path) == source(PR, path)
refs = load('EVIDENCE_REFERENCES.json')
for ref in refs:
    assert hashlib.sha256(source(ref['sha'], ref['path'])).hexdigest() == ref['sha256'], ref
required_outputs = ['BASELINE_AND_BRANCH_RECONCILIATION.md','FULL_FEATURE_INVENTORY.md','REQUIREMENTS_GAP_MATRIX.csv','AUTOMATED_TEST_COVERAGE_MATRIX.csv','DEVELOPMENT_DEPENDENCY_GRAPH.md','MASTER_DEVELOPMENT_BACKLOG.csv','NEXT_FIVE_SPRINTS.md','RISKS_AND_EXTERNAL_BLOCKERS.md','REPORT.md']
assert all((OUT / p).is_file() for p in required_outputs)
for p in OUT.glob('*.md'):
    for link in re.findall(r'\]\(([^)]+)\)', p.read_text()):
        if '://' not in link and not link.startswith('#'):
            assert (p.parent / link.split('#')[0]).exists(), (p, link)
changed = subprocess.check_output(['git','diff','--name-only',MAIN,'--'],cwd=ROOT,text=True).splitlines()
assert all(p.startswith('docs/verification/oc-dev-001/') for p in changed), changed
assert subprocess.check_output(['git','merge-base',MAIN,PR],cwd=ROOT,text=True).strip() == MAIN
print('PASS: 158 unique IDs, 55 complete backlog records, 39 historical defects, acyclic dependencies, CSV/JSON equality, immutable source references, journey/approval/pin preservation, local links and documentation-only scope')

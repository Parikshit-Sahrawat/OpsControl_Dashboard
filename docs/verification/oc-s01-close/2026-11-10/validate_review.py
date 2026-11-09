"""Validate review traceability without promoting acceptance or release gates."""
from pathlib import Path
import collections
import hashlib
import json
import re
import subprocess

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
SHA = 'ecfdff2cf3f9d1a7b7b284e79a7f708d1baea8ce'
REQUIRED = {'SPRINT0_CLOSURE_REGISTER','SPRINT1_ACCEPTANCE_MATRIX','PR89_INTEGRATION_RECONCILIATION','CI_TIER_ALIGNMENT_REPORT','OPEN_PR_DISPOSITION_MATRIX','SPRINT2_ENTRY_READINESS_REPORT','REMAINING_OWNER_DECISIONS'}

def check():
    for name in REQUIRED:
        assert (BASE/(name+'.md')).is_file(), name
    for p in BASE.rglob('*.json'):
        json.loads(p.read_text())
    for p in BASE.glob('*.md'):
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',p.read_text()):
            if not target.startswith(('https:','http:','#')):
                assert (p.parent/target.split('#')[0]).exists(), (p.name,target)
    r=json.loads((BASE/'SPRINT0_CLOSURE_REGISTER.json').read_text())
    rows=r['requirements'];assert len(rows)==len({x['requirement_id'] for x in rows})==158
    assert dict(collections.Counter(x['review_disposition'] for x in rows))==r['counts']
    assert set(r['counts'])=={'RESOLVED','APPROVED_DEFERRED','AWAITING_OWNER_DECISION','BLOCKED'}
    assert sum(x['source_recovery']=='SOURCE_NOT_RECOVERED' for x in rows)==62
    assert next(x for x in rows if x['requirement_id']=='UI-021')['review_disposition']=='RESOLVED'
    assert all(x['release_eligible'] is False and x['independent_uat']=='PENDING' for x in rows)
    for ref in json.loads((BASE/'SOURCE_REFERENCES.json').read_text()):
        assert ref['commit']==SHA
        assert hashlib.sha256((ROOT/ref['path']).read_bytes()).hexdigest()==ref['sha256'],ref['path']
    journey=json.loads((BASE/'JOURNEY_AND_STEP_RECONCILIATION.json').read_text())
    j=journey['journeys'];assert len(j)==33
    assert sum(x['scope_status']=='INCLUDED' for x in j)==31
    assert next(x for x in j if x['journey_id']=='20')['scope_status']!='INCLUDED'
    assert next(x for x in j if x['journey_id']=='32')['scope_status']!='INCLUDED'
    assert len(journey['closure_checklist']['steps'])==14
    models=json.loads((BASE/'MODEL_MIGRATION_CONSERVATION.json').read_text());assert not models['missing_model_classes']
    assert len(models['migrations'])==41 and all(x['unchanged'] for x in models['migrations'])
    matrix=json.loads((BASE/'SPRINT1_ACCEPTANCE_MATRIX.json').read_text())['contracts'];assert len(matrix)==len({r['id'] for r in matrix})==20
    assert sum(r['status']=='PASS_CONTROLLED' for r in matrix)==15
    scans=json.loads((BASE/'raw/EXACT_HEAD_SCAN_RECONCILIATION.json').read_text())
    assert len(scans)==7 and sum(x['raw_matches'] for x in scans)==984
    assert all(x['baseline_comparison']=='SAME_FINDING_MULTISET' and x['licence_reviewer'] is None for x in scans)
    merge=json.loads((BASE/'raw/hosted-image-merge-commit.json').read_text())
    head_tree=subprocess.check_output(['git','rev-parse',SHA+'^{tree}'],cwd=ROOT,text=True).strip()
    assert merge['commit']['tree']['sha']==head_tree
    assert all(x['source_sha']==merge['sha'] for x in scans)
    rules=json.loads((BASE/'raw/ruleset26082467.json').read_text())
    checks=next(x['parameters']['required_status_checks'] for x in rules['rules'] if x['type']=='required_status_checks')
    assert len(checks)==13 and all(x['integration_id']==15368 for x in checks)
    assert json.loads((BASE/'CI_WORKFLOW_ALIGNMENT.json').read_text())['workflow_count']==28
    cl=json.loads((BASE/'CLEANUP.json').read_text());assert cl['remaining_task_docker_containers']==0 and not cl['broad_cleanup']
    tests=json.loads((BASE/'TEST_RECONCILIATION.json').read_text());assert tests['pg_contract_distinct_test_identities_excluding_unit_modules']==177
    return {'status':'PASS_DOCUMENTATION_RECONCILIATION_ONLY','requirements':158,'journeys_included':31,'unrecovered_numbered_included_definitions':30,'closure_steps':14,'contracts':20,'controlled_pass_contracts':15,'workflows':28,'required_checks_preserved':13,'manual_review':'PENDING','sprint1':'NOT COMPLETE','security':'BLOCKED','chk001':'FAIL','chk002':'BLOCKED','release':'NO-GO','collector':'0.123.0 unchanged'}

if __name__=='__main__':
    print(json.dumps(check(),indent=2))

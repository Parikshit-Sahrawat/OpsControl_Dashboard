"""Read-only reproducible Stage 2A documentation/provenance checks."""
from pathlib import Path
import collections,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
baseline='a2f7460904fbab2a99c258616516054f21689687'
rows=json.loads((HERE/'requirements.json').read_text())
old=json.loads((ROOT/'docs/verification/sdlc/stage-02-development-reconciliation/requirements.json').read_text())
assert len(rows)==len({r['id'] for r in rows})==134
assert {r['id']:r['owner'] for r in rows}=={r['id']:r['owner'] for r in old}
allowed={'ACCEPTED','VERIFIED_PENDING_OWNER','IMPLEMENTED_UNVERIFIED','PARTIALLY_IMPLEMENTED','NOT_IMPLEMENTED','BLOCKED_ARCHITECTURE','BLOCKED_SECURITY','BLOCKED_RELIABILITY','SOURCE_NOT_RECOVERED','REMOVED_FROM_SCOPE','SUPERSEDED'}
for r in rows:
 assert r['status'] in allowed and r['baseline']==baseline
 for k in ('wording','scope','implementation','verification','source_paths','test_paths','ci_evidence','owner_acceptance','blocker','next'):assert k in r,(r['id'],k)
 if r['id'].startswith('IMP-'):assert r['status']=='SOURCE_NOT_RECOVERED'
 if r['id'].startswith('OC-IMP') and r['id']!='OC-IMP-017':assert r['approval']=='PROPOSED_OWNER_REVIEW' and r['status']=='BLOCKED_ARCHITECTURE'
 if r['id'] in ('K8S-01','K8S-02'):assert r['status']=='REMOVED_FROM_SCOPE'
 assert r['release_readiness']=='NO-GO'
for p in HERE.rglob('*.json'):json.loads(p.read_text())
for p in HERE.glob('*.md'):
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' not in target:assert (p.parent/target.split('#')[0]).exists(),(p,target)
prov=json.loads((HERE/'SOURCE_PROVENANCE.json').read_text())
for group in ('source_and_test_sha256','reused_source_hashes_verified'):
 for p,h in prov[group].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
assert not subprocess.check_output(['git','diff',prov['equivalent_evidence_tree'],baseline],cwd=ROOT)
for name in ('README.md','BASELINE_RECONCILIATION.md','CANONICAL_REQUIREMENTS_MATRIX.md','IMPLEMENTATION_EVIDENCE_MATRIX.md','KUBERNETES_SCOPE_RECONCILIATION.md','DEVELOPMENT_ACCEPTANCE_REPORT.md','SECURITY_RELIABILITY_GATES.md','UAT_GAP_REGISTER.md','STAGE_3_ENTRY_ASSESSMENT.md','OPEN_RISKS_AND_DEPENDENCIES.md','VALIDATION.json'):assert (HERE/name).is_file()
v=json.loads((HERE/'VALIDATION.json').read_text());assert v['classification_counts']==dict(collections.Counter(r['status'] for r in rows));assert not v['stage3_authorized'];assert v['gates']=={'CHK-001':'FAIL','CHK-002':'BLOCKED','SECURITY':'BLOCKED'}
manifest=HERE/'EVIDENCE_MANIFEST_SHA256.json'
if manifest.exists():
 m=json.loads(manifest.read_text());actual={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.rglob('*') if p.is_file() and p!=manifest}
 assert m==actual,'Manifest content/hash inventory mismatch'
print('PASS: IDs, ownership, statuses, proposal authority, baseline tree, source hashes, JSON, local links, required files, gates and manifest')

"""Documentation-only structure, identity, source-link and hash validation."""
from pathlib import Path
import json, hashlib, re
p=Path(__file__).resolve().parent
root=p.parents[2]
required=['JOURNEY_01_33_REQUIREMENTS_MATRIX.md','ETL_ARCHITECTURE_IMPLEMENTATION_MATRIX.md','UNIFIED_IMPLEMENTATION_BACKLOG.md','ARCHITECTURE_CONFLICT_REGISTER.md','TEST_AND_OWNER_ACCEPTANCE_MATRIX.md','IMPLEMENTATION_EXECUTION_PLAN.md']
errors=[]
for name in required:
 if not (p/name).is_file():errors.append('Missing '+name)
t=json.loads((p/'REQUIREMENT_TRACE.json').read_text())
if [x['number'] for x in t['journeys']]!=list(range(1,34)):errors.append('Journey coverage')
if t['journeys'][19]['status']!='EXCLUDED' or t['journeys'][31]['status']!='SKIPPED':errors.append('Excluded scope changed')
if len({x['id'] for x in t['etl']})!=16 or len({x['id'] for x in t['licensing']})!=8:errors.append('Trace IDs')
for f in p.rglob('*.json'):
 try:json.loads(f.read_text())
 except ValueError:errors.append('Invalid JSON '+f.name)
for f in p.glob('*.md'):
 for name in re.findall(r'(?:backend|frontend|scripts)/[A-Za-z0-9_./-]+\.(?:py|jsx|mjs)',f.read_text()):
  if not (root/name).is_file() and not (name == 'scripts/etl_filters.test.mjs' and (root/'frontend'/name).is_file()):errors.append('Missing source '+name)
report={'status':'FAIL' if errors else 'PASS','errors':sorted(set(errors)),'journey_slots':33,'included':31,'excluded':1,'skipped':1,'numbered_definition_gaps':30,'etl_requirements':16,'licensing_design_statements':8,'checks':['required documents','unique trace IDs','excluded scope','JSON validity','explicit code paths','artifact SHA-256 inventory'],'limitations':['Source hashes describe inspected baseline; later implementation deltas require separate evidence','No human approval or runtime certification inferred','No HTTP/provider testing in architecture baseline']}
(p/'VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n')
(p/'ARTIFACT_SHA256.json').write_text(json.dumps({str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(p.rglob('*')) if f.is_file() and f.name!='ARTIFACT_SHA256.json'},indent=2)+'\n')
print(json.dumps(report));raise SystemExit(bool(errors))

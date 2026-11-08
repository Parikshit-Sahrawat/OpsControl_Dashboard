from pathlib import Path
import json,hashlib,re,subprocess
r=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],text=True).strip());o=r/'docs/verification/oc-dev-comp-ci-001/implementation'
if not (o/'ARTIFACT_SHA256.json').exists():(o/'ARTIFACT_SHA256.json').write_text('{}\n')
json_files=list(o.rglob('*.json'))
for p in json_files:json.loads(p.read_text())
links=[]
for p in o.rglob('*.md'):
 for label,target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)',p.read_text()):
  if target.startswith(('http:','https:','#','mailto:')):continue
  target=target.split('#')[0]
  if not (p.parent/target).exists():links.append({'file':str(p.relative_to(o)),'target':target})
assert not links,links
source=json.loads((o/'IMPLEMENTATION_SOURCE_SHA256.json').read_text())
assert all(hashlib.sha256((r/f).read_bytes()).hexdigest()==sha for f,sha in source['files'].items())
manifest=json.loads((r/'.ci/scope-manifest.json').read_text())
rows=json.loads((o/'SCOPE_TO_EXECUTION_MATRIX.json').read_text());assert len(rows)==len(manifest['tests']);assert len({v['test'] for v in rows})==len(rows)
assert all((r/v['workflow']).is_file() and (r/v['test'].split('::')[0]).is_file() for v in rows)
commands=json.loads((o/'VALIDATION.json').read_text())['local_checks'];assert set(v['tested_implementation_sha']for v in commands.values())=={source['commit']}
assert json.loads((o/'integration-committed/backup-restore.json').read_text())['status']=='PASS'
assert json.loads((o/'integration-committed/ci-scope.json').read_text())['status']=='FAIL'
validation=json.loads((o/'VALIDATION.json').read_text());validation['documentation_validation']={'status':'PASS','json_files_parsed':len(json_files),'markdown_relative_links':'PASS','source_hashes':'PASS','scope_execution_rows':len(rows),'scope_id_uniqueness':'PASS','source_and_workflow_paths':'PASS','command_sha_consistency':'PASS','preserved_failure_statuses':'PASS','limitations':'Checks do not validate recovered requirement authority, full assertion equivalence, hosted CI or release eligibility.'};(o/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n')
# All evidence files except the self-referential manifest are checksum-bound.
files=sorted(p for p in o.rglob('*')if p.is_file() and p.name!='ARTIFACT_SHA256.json')
(o/'ARTIFACT_SHA256.json').write_text(json.dumps({'schema':1,'algorithm':'SHA-256','excluded_self':'ARTIFACT_SHA256.json','files':{str(p.relative_to(o)):hashlib.sha256(p.read_bytes()).hexdigest()for p in files}},indent=2)+'\n')
print(json.dumps(validation['documentation_validation']))

check=json.loads((o/'ARTIFACT_SHA256.json').read_text())
assert all(hashlib.sha256((o/f).read_bytes()).hexdigest()==sha for f,sha in check['files'].items())

"""Validate the closure package without executing product/runtime tests."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

package = Path(__file__).resolve().parent
root = package.parents[2]
errors = []
rows = json.loads((package / 'requirements.json').read_text())
ids = [row['id'] for row in rows]
if len(ids) != 134 or len(set(ids)) != len(ids):
    errors.append('134 unique canonical tracking IDs required')
allowed = {'ACCEPTED', 'VERIFIED_PENDING_OWNER', 'IMPLEMENTED_UNVERIFIED',
           'PARTIALLY_IMPLEMENTED', 'NOT_IMPLEMENTED', 'BLOCKED_ARCHITECTURE',
           'BLOCKED_SECURITY', 'BLOCKED_RELIABILITY', 'SOURCE_NOT_RECOVERED',
           'REMOVED_FROM_SCOPE', 'SUPERSEDED'}
for row in rows:
    if row['status'] not in allowed:
        errors.append(row['id'] + ': invalid classification')
    if row['status'] == 'ACCEPTED':
        errors.append(row['id'] + ': unexpected owner acceptance promotion')
    for name in row['source_paths'] + row['test_paths']:
        if not (root / name).is_file():
            errors.append(row['id'] + ': missing source/test ' + name)
for path in package.rglob('*.json'):
    try:
        json.loads(path.read_text())
    except (ValueError, UnicodeError) as exc:
        errors.append(str(path.relative_to(package)) + ': ' + str(exc))
for path in package.glob('*.md'):
    for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
        if target.startswith(('https://', 'http://', '#')):
            continue
        if not (path.parent / target.split('#')[0]).exists():
            errors.append(str(path.name) + ': broken link ' + target)
report = {'status': 'FAIL' if errors else 'PASS', 'errors': errors,
          'requirements': len(rows), 'counts': dict(Counter(row['status'] for row in rows)),
          'checks': ['JSON parsing', 'canonical ID uniqueness', 'classification allowlist',
                     'no unsupported ACCEPTED promotion', 'source/test file existence',
                     'local Markdown links', 'SHA-256 inventory generation'],
          'limitations': ['Remote document URLs not fetched by this validator',
                         'Human authority/acceptance is not established by syntax checks',
                         'Raw .json.raw.txt preserves invalid historical probe serialization'],
          'gates': {'CHK-001':'FAIL','CHK-002':'BLOCKED','SECURITY':'BLOCKED','RELEASE':'NO-GO'}}
(package / 'VALIDATION.json').write_text(json.dumps(report, indent=2) + '\n')
manifest = {str(path.relative_to(package)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(package.rglob('*'))
            if path.is_file() and path.name != 'EVIDENCE_MANIFEST_SHA256.json'}
(package / 'EVIDENCE_MANIFEST_SHA256.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(report, indent=2))
raise SystemExit(bool(errors))

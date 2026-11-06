#!/usr/bin/env python3
"""Validate traceability structure, never infer product acceptance from CI."""
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
data = json.loads((root / 'docs/verification/ci-roadmap-alignment/CI_REQUIREMENTS_MATRIX.json').read_text())
rows = data['requirements']
ids = [row['id'] for row in rows]
assert len(ids) == len(set(ids)), 'Duplicate canonical requirement'
canonical = set(re.findall(r'^\| ([A-Z][A-Z0-9]*-\d+) \|', (root / 'docs/planning/DEVELOPMENT_COMPLETION_REGISTER.md').read_text(), re.MULTILINE))
assert canonical <= set(ids), 'Canonical requirements missing from CI traceability'
approved = {row['id'] for row in rows if row['owner'] == 'OWNER_APPROVED_CONTROLLED_SCOPE — INDEPENDENT_UAT_PENDING'}
assert approved == set('RM-01 RM-04 RM-05 AM-01 CMP-01 CMP-02 API-01 OPS-03 UI-010'.split())
journeys = data['journeys']
assert [j['journey'] for j in journeys] == list(range(1, 34))
assert sum(j['scope'] == 'INCLUDED' for j in journeys) == 31
assert sum(j['source'] == 'SOURCE_NOT_RECOVERED' for j in journeys) == 30
assert journeys[19]['scope'] == 'EXCLUDED' and journeys[31]['scope'] == 'SKIPPED'
for row in rows:
    for path in [row['authority'], row['workflow'], *row['code'], *row['tests']]:
        assert (root / path).is_file(), (row['id'], path)
    assert row['gate'] == 'CHK-001 FAIL; CHK-002 BLOCKED; SECURITY BLOCKED; RELEASE NO-GO'
    assert row['uat'].startswith('N/A' if row['id'].startswith('K8S-') else 'PENDING')
    assert 'NOT CERTIFIED' in row['provider']
    if row['id'].startswith('LIC-'):
        assert row['journey'] == '33' and not row['tests']
print(f'CI roadmap traceability PASS: {len(rows)} requirements, 31 included journeys, nine owner decisions; no UAT/provider promotion')

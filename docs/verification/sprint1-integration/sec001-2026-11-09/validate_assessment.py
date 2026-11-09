"""Offline evidence/count/aggregation checks, not scan or legal certification."""
import copy
import csv
import hashlib
import json
from pathlib import Path
from analyze_evidence import aggregate, BASE


def main():
    match = {'vulnerability': {'id': 'GO-FIXTURE', 'severity': 'Medium', 'namespace': 'vendor-a', 'fix': {'state': 'fixed', 'versions': ['2.0']}}, 'relatedVulnerabilities': [{'id': 'CVE-2099-0001'}], 'artifact': {'type': 'go-module', 'name': 'fixture', 'version': '1.0'}}
    duplicate = copy.deepcopy(match)
    duplicate['vulnerability'].update(id='GHSA-FIXTURE', severity='Critical', namespace='vendor-b')
    rows = aggregate('role', 'image-a', [match, duplicate])
    assert len(rows) == 1 and rows[0]['severity'] == 'Critical' and len(rows[0]['raw_match_indices']) == 2
    assert rows[0]['advisory_namespaces'] == ['vendor-a', 'vendor-b']
    different = copy.deepcopy(match); different['artifact']['version'] = '1.1'
    assert len(aggregate('role', 'image-a', [match, different])) == 2
    different = copy.deepcopy(match); different['artifact']['name'] = 'other'
    assert len(aggregate('role', 'image-a', [match, different])) == 2
    assert aggregate('role', 'image-b', [match])[0]['image_id'] != rows[0]['image_id']
    ambiguous = copy.deepcopy(match); ambiguous['relatedVulnerabilities'].append({'id': 'CVE-2099-0002'})
    assert aggregate('role', 'image-a', [ambiguous])[0]['vulnerability'] == 'GO-FIXTURE'
    unknown = copy.deepcopy(match); unknown['vulnerability']['severity'] = 'Unknown'
    assert aggregate('role', 'image-a', [unknown, match])[0]['blocked_by_severity'] is True
    summary = json.loads((BASE / 'SUMMARY.json').read_text())
    findings = json.loads((BASE / 'FINDINGS_BY_IMAGE.json').read_text())
    licenses = json.loads((BASE / 'LICENSE_COMPONENT_REVIEW.json').read_text())
    assert summary['raw_matches'] == summary['image_scoped_unique'] == len(findings) == 984
    assert summary['cross_image_work_groups'] == 428
    assert len({(r['image_role'], r['image_id'], r['vulnerability'], r['package_type'], r['package'], r['installed_version']) for r in findings}) == len(findings)
    assert len(summary['roles']) == 7
    assert all(r['disposition'] == 'UNRESOLVED' and r['reviewer'] is None for r in findings)
    assert all(r['status'] == 'PENDING_ACCOUNTABLE_LEGAL_REVIEW' and r['reviewer'] is None for r in licenses)
    assert len(list(csv.DictReader((BASE / 'FINDINGS_BY_IMAGE.csv').open()))) == len(findings)
    assert len(list(csv.DictReader((BASE / 'LICENSE_COMPONENT_REVIEW.csv').open()))) == len(licenses)
    downloads = json.loads((BASE / 'DOWNLOAD_VERIFICATION.json').read_text())
    assert len(downloads) == 7 and all(r['github_hash_verified'] for r in downloads)
    for role in summary['roles']:
        directory = BASE / 'raw' / ('image-evidence-' + role['role'])
        provenance = json.loads((directory / 'provenance.json').read_text())
        for name, expected in provenance['sha256'].items(): assert hashlib.sha256((directory/name).read_bytes()).hexdigest() == expected
    print('PASS: 6 aggregation boundary fixtures; 7 archive/provenance packages; 984 image findings; 428 cross-image groups; 2451 pending component reviews; CSV/JSON consistency. Not release/legal clearance.')


if __name__ == '__main__': main()

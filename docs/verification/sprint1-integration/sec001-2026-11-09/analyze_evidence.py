"""Offline assessment of retained exact-head artifacts. Does not change gates."""
import collections
import csv
import hashlib
import gzip
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

BASE = Path(__file__).resolve().parent
EXPECTED_SOURCE = 'b1e645f342be5bc84141f314a12a81d3c38f621b'
SEVERITIES = {'Unknown': 0, 'Negligible': 1, 'Low': 2, 'Medium': 3, 'High': 4, 'Critical': 5}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(match):
    primary = match['vulnerability']['id']
    cves = {v['id'] for v in match.get('relatedVulnerabilities', []) if v['id'].startswith('CVE-')}
    return primary if primary.startswith('CVE-') or len(cves) != 1 else next(iter(cves))


def key(role, identity, match):
    artifact = match['artifact']
    return (role, identity, canonical(match), artifact['type'], artifact['name'], artifact['version'])


def aggregate(role, identity, matches):
    groups = {}
    for index, match in enumerate(matches):
        k = key(role, identity, match)
        v, a = match['vulnerability'], match['artifact']
        row = groups.setdefault(k, {
            'image_role': role, 'image_id': identity, 'vulnerability': k[2],
            'package_type': a['type'], 'package': a['name'], 'installed_version': a['version'],
            'primary_ids': set(), 'aliases': set(), 'severities': set(), 'advisory_namespaces': set(),
            'fix_states': set(), 'reported_fix_versions': set(), 'advisory_urls': set(),
            'locations': set(), 'purls': set(), 'raw_match_indices': [], 'known_exploited_metadata': [],
        })
        row['primary_ids'].add(v['id'])
        row['aliases'].update(x['id'] for x in match.get('relatedVulnerabilities', []))
        row['severities'].add(v.get('severity', 'Unknown'))
        row['advisory_namespaces'].add(v.get('namespace', ''))
        row['fix_states'].add(v.get('fix', {}).get('state') or 'UNSPECIFIED')
        row['reported_fix_versions'].update(v.get('fix', {}).get('versions', []))
        row['advisory_urls'].update(v.get('urls', []) + [v.get('dataSource', '')])
        row['locations'].update(x['path'] for x in a.get('locations', []))
        row['purls'].add(a.get('purl', ''))
        row['raw_match_indices'].append(index)
        row['known_exploited_metadata'].extend(v.get('knownExploited', []))
    for row in groups.values():
        for name, value in list(row.items()):
            if isinstance(value, set): row[name] = sorted(value)
        row['severity'] = max(row['severities'], key=lambda v: SEVERITIES.get(v, 0))
        row['blocked_by_severity'] = bool(set(row['severities']) & {'Critical', 'High', 'Unknown'})
        row['applicability'] = 'PENDING_ACCOUNTABLE_REACHABILITY_REVIEW'
        row['disposition'] = 'UNRESOLVED'
        row['reviewer'] = None
        row['work_item'] = 'SEC001-R03' if role in ('backend-runtime', 'backend-migration') else 'SEC001-R02' if role == 'postgres' else 'SEC001-R05' if role in ('otel-contrib', 'uat-backend') else 'SEC001-R04'
    return list(groups.values())


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(key for row in rows for key in row)))
        writer.writeheader()
        writer.writerows({k: json.dumps(v, sort_keys=True) if isinstance(v, (list, dict)) else v for k, v in row.items()} for row in rows)


def main():
    artifacts = json.loads((BASE / 'artifacts.json').read_text())['artifacts']
    downloads, inventories, findings, licenses = [], [], [], []
    for artifact in sorted(artifacts, key=lambda a: a['name']):
        role = artifact['name'].removeprefix('image-evidence-')
        path = BASE / 'raw' / artifact['name']
        assert artifact['workflow_run']['head_sha'] == EXPECTED_SOURCE
        archive = path.with_suffix('.zip')
        assert 'sha256:' + digest(archive) == artifact['digest']
        p = json.loads((path / 'provenance.json').read_text())
        assert p['source_sha'] == EXPECTED_SOURCE
        for name, expected in p['sha256'].items(): assert digest(path / name) == expected, (role, name)
        syft = json.loads((path / 'sbom.syft.json').read_text())
        grype = json.loads((path / 'grype.json').read_text())
        assert syft['source']['metadata']['imageID'] == p['image_id']
        assert grype['source']['target']['imageID'] == p['image_id']
        cdx = json.loads((path / 'sbom.cdx.json').read_text())
        assert cdx['bomFormat'] == 'CycloneDX' and cdx['components']
        db = json.loads((path / 'grype-db.json').read_text())
        review = json.loads((path / 'licenses.json').read_text())
        matches = grype['matches']
        dedup = aggregate(role, p['image_id'], matches)
        for row in dedup:
            row['raw_evidence'] = [str((path / 'grype.json').relative_to(BASE)) + '#/matches/' + str(i) for i in row['raw_match_indices']]
        findings.extend(dedup)
        downloads.append({'role': role, 'artifact_id': artifact['id'], 'bytes': archive.stat().st_size, 'sha256': artifact['digest'], 'github_hash_verified': True, 'source_sha': p['source_sha']})
        inventories.append({'role': role, 'source_sha': p['source_sha'], 'image_id': p['image_id'], 'architecture': p['architecture'], 'created_utc': p['created_utc'], 'raw_matches': len(matches), 'image_deduplicated_findings': len(dedup), 'severities': dict(collections.Counter(x['severity'] for x in dedup)), 'db_built': db['built'], 'db_valid_at_scan': db['valid'], 'license_components': len(review['components']), 'license_status': review['status'], 'legal_reviewer': review.get('reviewer'), 'final_registry_manifest_digest': None})
        for index, component in enumerate(review['components']):
            declarations = component.get('licenses', [])
            expressions = sorted({x.get('spdxExpression') or x.get('value') or 'UNKNOWN' for x in declarations})
            unknown = not expressions or any(x.upper() in ('UNKNOWN', 'NOASSERTION', 'NONE') for x in expressions)
            copyleft = any(any(t in e.upper() for t in ('GPL', 'LGPL', 'AGPL', 'MPL', 'CDDL', 'EPL')) for e in expressions)
            licenses.append({'image_role': role, 'image_id': p['image_id'], 'component': component['name'], 'version': component['version'], 'declared_expressions': expressions, 'unknown_or_empty': unknown, 'copyleft_or_weak_copyleft_review_flag': copyleft, 'complex_expression_review': any(t in e for e in expressions for t in (' OR ', ' AND ', ' WITH ')), 'required_review': 'Validate exact terms/ownership; attribution and NOTICE; corresponding source/source offer/relink obligations if applicable; bundle/linkage/distribution assessment', 'status': 'PENDING_ACCOUNTABLE_LEGAL_REVIEW', 'reviewer': None, 'evidence': str((path / 'licenses.json').relative_to(BASE)) + '#/components/' + str(index)})
    findings.sort(key=lambda r: (-SEVERITIES[r['severity']], r['image_role'], r['vulnerability'], r['package'], r['installed_version']))
    for number, row in enumerate(findings, 1): row['finding_id'] = f'SEC001-F{number:04}'
    # Cross-image work groups preserve every affected role/identity; never count
    # one remediation group as one affected image or one exploitability decision.
    shared = {}
    for row in findings:
        k = (row['vulnerability'], row['package_type'], row['package'], row['installed_version'])
        g = shared.setdefault(k, {'vulnerability': k[0], 'package_type': k[1], 'package': k[2], 'installed_version': k[3], 'affected_images': [], 'finding_ids': [], 'reported_fix_versions': set(), 'fix_states': set()})
        g['affected_images'].append({'role': row['image_role'], 'image_id': row['image_id']})
        g['finding_ids'].append(row['finding_id'])
        g['reported_fix_versions'].update(row['reported_fix_versions'])
        g['fix_states'].update(row['fix_states'])
    for group in shared.values():
        group['reported_fix_versions'] = sorted(group['reported_fix_versions']); group['fix_states'] = sorted(group['fix_states'])
    # Current Debian source-package status is recorded alongside scan metadata;
    # "no DSA"/ignored/not-affected is not an automatic security exception.
    vendor = json.loads(gzip.decompress((BASE / 'upstream/debian-security.json.gz').read_bytes()))
    for row in findings:
        if row['package_type'] != 'deb': continue
        sources = {s for purl in row['purls'] for s in parse_qs(urlsplit(purl).query).get('upstream', [])}
        row['debian_source_package_candidates'] = sorted(sources)
        row['vendor_trixie'] = {s: vendor[s][row['vulnerability']].get('releases', {}).get('trixie', {}) for s in sources if s in vendor and row['vulnerability'] in vendor[s]}
        row['vendor_bookworm_comparison_only'] = {s: vendor[s][row['vulnerability']].get('releases', {}).get('bookworm', {}) for s in sources if s in vendor and row['vulnerability'] in vendor[s]}
    patch_groups = {}
    for row in findings:
        k = (row['image_role'], row['package_type'], row['package'], row['installed_version'])
        group = patch_groups.setdefault(k, {'image_role': k[0], 'package_type': k[1], 'package': k[2], 'installed_version': k[3], 'finding_ids': [], 'vulnerabilities': [], 'fix_states': set(), 'scanner_reported_versions': set(), 'owner': 'Component engineering + security lead; named assignees PENDING', 'proposal_status': 'PROPOSED_NOT_IMPLEMENTED', 'compatibility': 'Requires exact candidate build, fresh immutable scan and applicable runtime/security regression; no automatic severity/approval change'})
        group['finding_ids'].append(row['finding_id']); group['vulnerabilities'].append(row['vulnerability'])
        group['fix_states'].update(row['fix_states']); group['scanner_reported_versions'].update(row['reported_fix_versions'])
    for group in patch_groups.values():
        group['fix_states'] = sorted(group['fix_states']); group['scanner_reported_versions'] = sorted(group['scanner_reported_versions'])
        if group['package_type'] == 'go-module':
            group['proposal'] = 'Upstream compiled-binary rebuild/release required; installing runtime packages cannot change embedded Go dependencies. Collector0.123.0 pin remains unchanged; no custom build/transition authorized.'
        elif group['package_type'] == 'deb':
            group['proposal'] = 'Review distro/source advisory, affected code path and fixed repository availability; qualify supported pinned base candidate only after approval. Do not remove essential libraries.'
        else:
            group['proposal'] = 'Review exact distro/advisory patch status; qualify a supported pinned base refresh only after approval. Missing fix metadata remains unresolved.'
    (BASE / 'PATCH_CANDIDATES.json').write_text(json.dumps(list(patch_groups.values()), indent=2) + '\n')
    write_csv(BASE / 'PATCH_CANDIDATES.csv', list(patch_groups.values()))
    outputs = {'IMAGE_INVENTORY.json': inventories, 'DOWNLOAD_VERIFICATION.json': downloads, 'FINDINGS_BY_IMAGE.json': findings, 'CROSS_IMAGE_WORK_GROUPS.json': list(shared.values()), 'LICENSE_COMPONENT_REVIEW.json': licenses}
    for name, data in outputs.items(): (BASE / name).write_text(json.dumps(data, indent=2) + '\n')
    write_csv(BASE / 'FINDINGS_BY_IMAGE.csv', findings)
    write_csv(BASE / 'CROSS_IMAGE_WORK_GROUPS.csv', list(shared.values()))
    write_csv(BASE / 'LICENSE_COMPONENT_REVIEW.csv', licenses)
    summary = {'raw_matches': sum(x['raw_matches'] for x in inventories), 'image_scoped_unique': len(findings), 'cross_image_work_groups': len(shared), 'primary_advisory_ids': len({x for row in findings for x in row['primary_ids']}), 'canonical_vulnerabilities': len({r['vulnerability'] for r in findings}), 'severity': dict(collections.Counter(r['severity'] for r in findings)), 'license_component_records': len(licenses), 'license_unknown_empty_records': sum(r['unknown_or_empty'] for r in licenses), 'copyleft_review_flag_records': sum(r['copyleft_or_weak_copyleft_review_flag'] for r in licenses), 'roles': inventories}
    (BASE / 'SUMMARY.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='roles'}, indent=2))


if __name__ == '__main__': main()

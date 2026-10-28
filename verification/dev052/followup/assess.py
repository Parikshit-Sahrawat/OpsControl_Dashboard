"""Derive inventories from retained raw scans; never assign release approval."""

import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/verification/dev052/security/2026-10-25-followup"
PRIOR = OUT.parent / "2026-10-25-remediation"


def read(path):
    return json.loads(path.read_text())


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


images = read(OUT / "image-inventory.json")
summary, bindings, licenses, findings = [], [], [], []
for image in images:
    key = image["name"]
    scanpath, bompath = OUT / f"{key}.scan.json", OUT / f"{key}.sbom.json"
    scan, bom = read(scanpath), read(bompath)
    source = scan["source"]["target"]
    assert source["imageID"] == image["id"]
    assert bom["metadata"]["component"]["version"] == source["manifestDigest"]
    bindings.append(
        {
            "image": key,
            "image_config_digest": image["id"],
            "archive_sha256": image["archive_sha256"],
            "archive_manifest_digest": source["manifestDigest"],
            "registry_release_manifest_digest": None,
            "sbom_sha256": sha(bompath),
            "scan_sha256": sha(scanpath),
            "binding": "docker save config SHA checked before scanning; Grype imageID and Syft archive manifest agree",
            "warning": "Archive manifest identity is NOT an approved published registry manifest",
        }
    )
    counts = dict(
        collections.Counter(m["vulnerability"]["severity"] for m in scan["matches"])
    )
    priorpath = PRIOR / f"{key}.scan.json"
    before = (
        dict(
            collections.Counter(
                m["vulnerability"]["severity"] for m in read(priorpath)["matches"]
            )
        )
        if priorpath.exists()
        else None
    )
    summary.append(
        {
            "image": key,
            "image_config_digest": image["id"],
            "matches_by_severity": counts,
            "previous_matches_by_severity": before,
            "components": len(bom.get("components", [])),
            "db": scan["descriptor"]["db"],
            "scan_time": scan["descriptor"]["timestamp"],
        }
    )
    for match in scan["matches"]:
        findings.append(
            {
                "image": key,
                "image_config_digest": image["id"],
                "artifact": match["artifact"],
                "vulnerability": match["vulnerability"],
                "disposition": "UNRESOLVED; no waiver",
                "reviewer": "Owner assignment pending",
            }
        )
    for component in bom.get("components", []):
        declared = component.get("licenses", [])
        text = json.dumps(declared)
        obligations = [
            "Retain actual copyright/license text; verify version-specific upstream terms and distribution contents"
        ]
        if "Apache" in text:
            obligations.append(
                "Review upstream NOTICE; include applicable attribution and modification notices"
            )
        if any(x in text for x in ("GPL", "LGPL", "MPL", "CDDL", "EPL")):
            obligations.append(
                "Review copyleft scope/linking/modifications; assemble corresponding source or valid source offer where required; verify relinking obligations for LGPL"
            )
        if not declared:
            obligations.append(
                "UNKNOWN license: obtain authoritative source/license identification before approval"
            )
        licenses.append(
            {
                "image": key,
                "image_config_digest": image["id"],
                "name": component["name"],
                "version": component.get("version"),
                "purl": component.get("purl"),
                "licenses_as_cataloged": declared,
                "source_metadata": component.get("externalReferences", []),
                "license_evidence": f"{key}.sbom.json#{component.get('bom-ref', '')}",
                "required_review": obligations,
                "notice_packaged_for_redistribution": "NOT VERIFIED per component",
                "corresponding_source_or_offer": "NOT ASSEMBLED / human applicability review required",
                "status": "BLOCKED pending accountable human review",
                "reviewer": None,
            }
        )

write("scan-summary.json", summary)
write("subject-bindings.json", bindings)
write("all-findings.json", findings)
write("component-license-assessment.json", licenses)

advisories = read(PRIOR / "nine-advisory-dispositions.json")
paths = {
    "PYSEC-2026-196": "Malicious entry-point paths during package installation; patched installer still requires trusted package inputs.",
    "PYSEC-2026-1795": "Malicious tar symlinks on data-filter fallback paths; Python 3.12 supports data_filter, but that does not certify every operator platform.",
    "PYSEC-2026-1796": "Wheel extraction of malicious paths; verified 26.2 wheel executes before any dependency install in patched paths.",
    "PYSEC-2026-2875": "Ambiguous archives during resolution/extraction; pinned wheel bootstrap uses no resolver/index; subsequent installs use 26.2.",
    "PYSEC-2026-2876": "Self-update import path; old pip installer is not invoked, verified wheel runs under -I. Python site/OS startup remain trusted inputs.",
    "PYSEC-2026-3721": "Doubly encoded index URLs; bootstrap has a fixed HTTPS URL and hash; downstream dependency installs use patched 26.2.",
}
for row in advisories:
    if row["package"] != "pip":
        row["current_evidence"] = (
            "Prior remediation evidence unchanged; no new Black implementation change"
        )
        continue
    row.update(
        previous_disposition=row["disposition"],
        disposition="UNRESOLVED",
        reachable_path=paths[row["advisory"]],
        applicability=paths[row["advisory"]],
        remediation="stdlib HTTPS + SHA-256 pinned pip 26.2 wheel; execute verified wheel, not old installed pip; remove pip/ensurepip from final Python stages without running old uninstall code",
        scope="Patched production builder, 13 declared CI workflows, demo/UAT/test Dockerfiles, generated golden-path build, Kubernetes installer and Windows packager. No blanket clearance of operator/historical/platform paths.",
        remaining="Native Windows packaging, full legacy demo/UAT/browser harness and Kubernetes installer not executed here; manual operator instructions and archived historical scripts require accountable review. No owner exception.",
        test_evidence=[
            "bootstrap.log",
            "bootstrap-offline.log",
            "targeted-tests.log",
            "candidate-tests.log",
            "backend-build.log",
            "migration-build.log",
            "pip-surface-inventory.txt",
        ],
        installed_version="25.0.1 originally observed; 26.2 in patched install paths; absent from final Python candidates",
        runtime_present=False,
        reviewer="Codex automated technical assessment; accountable owner pending",
        review_date="2026-10-25",
    )
write("nine-advisory-dispositions.json", advisories)

reachability = {
    "CVE-2025-69720": "Requires infocmp analyzing attacker-controlled terminal data; tool is installed but no direct application invocation found. See runtime-components.json. No proof that all transitive/operator paths are absent.",
    "CVE-2026-82560": "Requires Perl Pod::Text formatting malicious nested POD; API and migration are Python, no direct POD rendering found. No full transitive call-graph proof.",
    "CVE-2026-9538": "Requires Perl Archive::Tar handling attacker-controlled oversized tar entry; no direct Perl archive path found in API/worker. Operator/build tool use not globally excluded.",
    "CVE-2026-5435": "Requires deprecated glibc DNS-print routines with TSIG input. Normal HTTPS DNS resolution alone does not establish that path. glibc is essential and loaded; transitive native calls not exhaustively proven absent.",
    "CVE-2026-85091": "Requires specific nonblocking gzwrite stall then gzprintf/gzvprintf with stale pointers. Python gzip/HTTP use is not proof of this native path; zlib is essential, no direct call found, native dependencies remain to review.",
    "CVE-2026-95619": "Requires aligned C++ operator new with overflow-sized input. No direct app C++ allocation found; libstdc++/native extension linkage and input propagation need review, not a package-name exemption.",
    "CVE-2026-19499": "Requires glibc strfmon/right-justified monetary padding with insufficient buffer; glibc version is in upstream range. No direct format path found; native callers not exhaustively audited.",
    "CVE-2026-102010": "Requires libstdc++ binary-heap erase_if call and attacker-triggerable queue operations. No direct application call found; native extension review incomplete.",
    "CVE-2026-76642": "Requires privileged mount helpers/post-hooks and X-mount owner/idmap options. Candidate UID10001/CapEff0, fstab unconfigured, but mount is SUID and NoNewPrivs=0; no claim privilege path is impossible.",
    "CVE-2026-78408": "Requires privileged nsenter --join-cgroup into attacker-controlled target then inherited FD. No direct app invocation; UID10001/CapEff0 constrain ordinary runtime, operator privilege overrides remain outside evidence.",
    "CVE-2026-78409": "Requires Linux>=6.15 plus fstab-authorized X-mount.subdir and intermediate symlink. Image fstab unconfigured; host kernel/runtime/volume overrides not certified. SUID mount retained.",
    "CVE-2026-78410": "Requires writable source/ancestor in authorized fstab bind mount plus privileged owner/group/mode update. No candidate fstab authorization found; production operator configuration unknown.",
    "CVE-2026-54369": "Requires privileged libacl pathname operations over attacker-controlled symlinks. Runtime UID10001/CapEff0 limits privileges; no direct ACL application call found. Operator mounts/native callers remain unreviewed.",
    "CVE-2026-54370": "Requires privileged ACL utility/path traversal race. No direct utility calls found; read-only/network-none probe constrains probe only, not unknown production runtime.",
}
unique = read(OUT / "unique-high-findings.json")
for entry in unique["entries"]:
    entry.update(
        runtime_reachability=reachability[entry["cve"]],
        vendor_fix_assessment="Retained Debian trixie records open with no fixed_version; fresh apt-upgraded candidates still match. wont-fix/nodsa is not a waiver. Source-package variants retained; no false N/A from different source names.",
        supported_alternative="Official Python 3.12 Bookworm built and 36 contracts passed, but scan has 3 Critical/79 High, worse than selected Trixie 0/55. REJECTED, not promoted. Alpine/musl would require native dependency/provider compatibility work: NOT TESTED.",
        evidence=[
            "runtime-components.json",
            "runtime-paths.json",
            "source-reachability.log",
            "scan-summary.json",
            "bookworm-tests.log",
        ],
        disposition="UNRESOLVED",
        owner_disposition="PENDING accountable security/release owner; no exception granted",
    )
write("unique-high-findings.json", unique)

# JS dependencies in static bundles are not necessarily discoverable by image
# package catalogers. Keep a separate lockfile inventory, never claim image SBOM
# coverage implies complete bundle/license attribution.
package = read(ROOT / "frontend/package.json")
lock = read(ROOT / "frontend/package-lock.json")
npm = []
for path, item in lock.get("packages", {}).items():
    if not path:
        continue
    name = path.rsplit("node_modules/", 1)[-1]
    npm.append(
        {
            "name": name,
            "version": item.get("version"),
            "licenses_as_declared": item.get("license"),
            "direct": name in package.get("dependencies", {})
            or name in package.get("devDependencies", {}),
            "dev_only_as_lockfile": item.get("dev", False),
            "bundle_inclusion": "NOT MAPPED to immutable frontend bundle",
            "obligation": "Verify upstream license/NOTICE and actual shipped bundle inclusion; retain applicable texts, inspect copyleft/source obligations",
            "status": "BLOCKED pending human component review",
            "reviewer": None,
        }
    )
write("frontend-lock-license-assessment.json", npm)

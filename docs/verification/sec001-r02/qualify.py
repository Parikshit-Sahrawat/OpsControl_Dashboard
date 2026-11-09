"""Reconcile the exact 35 reviewed C/H records with static byte-equivalent evidence."""

import csv
import hashlib
import json
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
ASSESS = REPO / "docs/verification/sprint1-integration/sec001-2026-11-09"
RAW = ASSESS / "raw/image-evidence-postgres"


def h(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(name):
    return (
        name.replace("(*", "")
        .replace(")", "")
        .replace("(", "")
        .replace("*", "")
        .removesuffix(".abi0")
    )


def main():
    scan = json.loads((RAW / "grype.json").read_text())
    provenance = json.loads((RAW / "provenance.json").read_text())
    assert (
        provenance["image_id"]
        == "sha256:a7d2ca3526ce25d3036f8c403504a77af1d05448708074dfaf2817f4f3be54e8"
    )
    assert h(RAW / "grype.json") == provenance["sha256"]["grype.json"]
    sbom = json.loads((RAW / "sbom.syft.json").read_text())
    binary = json.loads((BASE / "raw/binary-inspection.json").read_text())
    gosu = next(
        f
        for f in sbom["files"]
        if f.get("location", {}).get("path") == "/usr/local/bin/gosu"
    )
    assert (
        next(d["value"] for d in gosu["digests"] if d["algorithm"] == "sha256")
        == binary["sha256"]
    )
    assert (
        binary["go_version"] == "go1.24.6"
        and "CGO_ENABLED=0" in binary["module_build_info"]
    )
    reviewed = json.loads((ASSESS / "FINDINGS_BY_IMAGE.json").read_text())
    names = {normalize(n) for n in binary["function_names"]}
    rows = []
    for index, m in enumerate(scan["matches"]):
        v = m["vulnerability"]
        a = m["artifact"]
        if v["severity"] not in ["High", "Critical"]:
            continue
        assert a["name"] == "stdlib" and a["version"] == "go1.24.6"
        advisory_file = BASE / "raw/go-advisories" / (v["id"] + ".json")
        advisory = json.loads(advisory_file.read_text())
        assert advisory["id"] == v["id"]
        aliases = {r["id"] for r in m.get("relatedVulnerabilities", [])}
        assert not {x for x in aliases if x.startswith("CVE-")} - set(
            advisory.get("aliases", [])
        )
        affected = [x for x in advisory["affected"] if x["package"]["name"] == "stdlib"]
        assert affected
        imports = [
            i
            for x in affected
            for i in x.get("ecosystem_specific", {}).get("imports", [])
        ]
        paths = sorted({i["path"] for i in imports})
        symbols = sorted(
            {
                normalize(i["path"] + "." + s)
                for i in imports
                for s in i.get("symbols", [])
            }
        )
        observed = sorted(names & set(symbols))
        packages_observed = sorted(
            {p for p in paths if any(n.startswith(p + ".") for n in names)}
        )
        windows_only = bool(imports) and all(
            i.get("goos") and "linux" not in i["goos"] for i in imports
        )
        fixed = sorted(
            {
                e["fixed"]
                for x in affected
                for r in x.get("ranges", [])
                for e in r["events"]
                if "fixed" in e
            }
        )
        original = next(
            r
            for r in reviewed
            if r["image_role"] == "postgres"
            and v["id"] in r["primary_ids"]
            and r["installed_version"] == a["version"]
        )
        rows.append(
            {
                "finding_id": original["finding_id"],
                "advisory": v["id"],
                "cves": sorted(x for x in aliases if x.startswith("CVE-")),
                "severity_unchanged": v["severity"],
                "image_config_digest": provenance["image_id"],
                "approved_registry_manifest_digest": None,
                "component": "/usr/local/bin/gosu",
                "gosu_module_version": "v1.19.0 (embedded metadata)",
                "binary_sha256": binary["sha256"],
                "package_or_module": a["name"],
                "installed_version": a["version"],
                "scanner_fixed_versions": v.get("fix", {}).get("versions", []),
                "authoritative_stdlib_fixed_events": fixed,
                "affected_stdlib_paths": paths,
                "upstream_import_constraints": imports,
                "final_image_presence": "VERIFIED_DIGEST_BOUND_SBOM_AND_EQUIVALENT_SIGNED_RELEASE_BYTES",
                "pclntab_matching_listed_symbols": observed,
                "observed_affected_packages": packages_observed,
                "platform_comparison": (
                    "WINDOWS_ONLY_ADVISORY_VS_LINUX_AMD64_BINARY"
                    if windows_only
                    else "No exclusive platform mismatch established"
                ),
                "reachability": (
                    "INCONCLUSIVE; listed symbol observed but callers/input/control-flow not qualified"
                    if observed
                    else "INCONCLUSIVE; no listed symbol observed in pclntab, but inlining/dynamic/compiler paths not ruled out"
                ),
                "proposed_mitigation": (
                    "Independent security review of explicit platform discrepancy; no suppression applied"
                    if windows_only
                    else "Evaluate an official supported PG17 image with a demonstrably fixed compiled gosu; do not substitute latest tag or custom binary"
                ),
                "compatibility_risk": "Preserve PG17 format, entrypoint/UID/GID, locale/ICU/extensions, TLS/auth, existing volumes/migrations/restore; candidate not qualified",
                "qualification_status": "PARTIAL_STATIC_EVIDENCE; BLOCKED_FIXED_CANDIDATE; PENDING_ACCOUNTABLE_REVIEW",
                "finding_disposition": "UNRESOLVED",
                "reviewer": None,
                "evidence": [
                    str((RAW / "grype.json").relative_to(REPO))
                    + "#/matches/"
                    + str(index),
                    str(advisory_file.relative_to(REPO)),
                    str((BASE / "raw/binary-inspection.json").relative_to(REPO)),
                    str((BASE / "raw/gpg-verification.log").relative_to(REPO)),
                ],
            }
        )
    assert (
        len(rows) == 35
        and sum(r["severity_unchanged"] == "Critical" for r in rows) == 3
    )
    (BASE / "QUALIFICATION_MATRIX.json").write_text(json.dumps(rows, indent=2) + "\n")
    with (BASE / "QUALIFICATION_MATRIX.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(
            {
                k: json.dumps(v) if isinstance(v, (list, dict)) else v
                for k, v in r.items()
            }
            for r in rows
        )
    print(
        "35 records reconciled; component presence verified; listed-symbol hits",
        sum(bool(r["pclntab_matching_listed_symbols"]) for r in rows),
        "platform discrepancies",
        sum(r["platform_comparison"].startswith("WINDOWS") for r in rows),
        "no findings closed",
    )


if __name__ == "__main__":
    main()

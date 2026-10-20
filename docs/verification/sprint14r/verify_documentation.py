"""Bounded reproducible documentation, source-preservation and register checks."""

from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parent
BASELINE = "59344c97401340e222627063f7c89bb5e2e89ead"
FILES = list(PACKAGE.glob("*.md")) + [
    ROOT / "docs/architecture/PRODUCT_ALIGNMENT_ADDENDUM.md",
    ROOT / "docs/architecture/OPS_DEPLOY_001.md",
    ROOT / "docs/engineering/ENG_001.md",
]
checks = []
for path in FILES:
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
        if target.startswith(("https:", "http:", "#")):
            continue
        target = target.split("#")[0]
        assert (path.parent / target).exists(), (str(path), target)
checks.append("All new Markdown local link paths exist")
register = (PACKAGE / "IMPROVEMENT_REGISTER.md").read_text()
ids = re.findall(r"^\| (OC-IMP-\d{3}) \|", register, re.M)
assert ids == [f"OC-IMP-{n:03}" for n in range(1, 19)]
checks.append("Exactly18 unique OC-IMP rows; historical definitions not invented")
historical = (
    ROOT / "docs/verification/arch-etl-001-v16-r1/sprint11/IMPROVEMENT_REGISTER.md"
).read_text()
assert re.findall(r"^\| (IMP-\d{3}) \|", historical, re.M) == [
    f"IMP-{n:03}" for n in range(1, 63)
]
assert all(
    "SOURCE_NOT_RECOVERED" in row
    for row in historical.splitlines()
    if row.startswith("| IMP-")
)
candidates = (
    ROOT
    / "docs/verification/arch-etl-001-v16-r1/sprint11/NEW_IMPROVEMENT_RECONCILIATION.md"
).read_text()
assert re.findall(r"^\| (NEW-\d{2}) \|", candidates, re.M) == [
    f"NEW-{n:02}" for n in range(1, 17)
]
checks.append("Historical62 source-unrecovered IMPs and16 NEW candidates retained")
ready = (PACKAGE / "PRODUCTION_READINESS.md").read_text()
gaps = re.findall(r"^\| (P[012]-\d{2}) ", ready, re.M)
assert len(gaps) == len(set(gaps)) == 16
assert {x for x in gaps if x.startswith("P0-")} == {f"P0-{n:02}" for n in range(1, 7)}
assert {x for x in gaps if x.startswith("P1-")} == {f"P1-{n:02}" for n in range(1, 9)}
assert {x for x in gaps if x.startswith("P2-")} == {"P2-01", "P2-02"}
checks.append("All16 readiness gaps:6P0/8P1/2P2")
roadmap = (PACKAGE / "ROADMAP_RECONCILIATION.md").read_text()
assert re.findall(r"^\| (\d+) \|", roadmap, re.M) == [str(n) for n in range(12, 43)]
checks.append("Every Sprint12–42 has dependency and evidence exit")
protected = [
    "docs/ARCH_001_V16.md",
    "docs/architecture/ARCH_ETL_001_V16.md",
    "backend",
    "agent",
    "tests/fixtures/pentaho/native-evidence",
    ".github",
    "scripts",
    "docs/verification/arch-etl-001-v16-r1",
    "docs/verification/p0-p1-remediation-2026-10-20",
]
changed = subprocess.check_output(
    ["git", "diff", "--name-only", BASELINE, "--", *protected], cwd=ROOT, text=True
).strip()
assert not changed, changed
checks.append(
    "Original architecture/backend/migrations/Agent/native fixtures/prior evidence unchanged"
)
manifest = {}
for rel in ("docs/ARCH_001_V16.md", "docs/architecture/ARCH_ETL_001_V16.md"):
    manifest[rel] = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
checks.append("Git whitespace check")
print(
    json.dumps(
        {
            "status": "PASS",
            "baseline": BASELINE,
            "checks": checks,
            "protected_architecture_sha256": manifest,
        },
        indent=2,
    )
)

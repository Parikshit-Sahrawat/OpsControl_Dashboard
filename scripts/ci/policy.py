"""Always-on verification policy; unknown tests are retained, never skipped."""

import ast
import json
from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[2]
CLASSES = {
    "INCLUDED_POSITIVE",
    "EXCLUDED_NEGATIVE",
    "LEGACY_PRESERVATION",
    "SHARED_SECURITY",
    "UNKNOWN",
}
ALWAYS_PR = [
    "access-architecture.yml",
    "arch001-native-monitoring.yml",
    "ci-policy.yml",
    "development-gates.yml",
    "egress-firewall-smoke.yml",
    "live-http-alert-recovery.yml",
    "local-uat-image-validation.yml",
    "operational-acceptance.yml",
    "phase1-staging.yml",
    "pipeline-v16.yml",
    "private-https-acceptance.yml",
    "release-reliability.yml",
    "security-artifacts.yml",
    "security-validation.yml",
    "stage-b-validation.yml",
    "v15-quality.yml",
    "validation.yml",
]
REQUIRED = {
    "frontend-build",
    "frontend-dependency-audit",
    "image-validation",
    "contracts",
    "python-dependency-audit",
    "secret-history-scan",
    "staging-smoke",
    "private-https",
    "verification",
    "pipeline-contracts",
    "restore-retention-tls",
    "access-rbac",
    "noc",
}


def test_inventory(root):
    result = {}
    for directory in ["backend/tests", "tests", "frontend/scripts"]:
        for p in sorted((root / directory).glob("*")):
            if p.suffix == ".py":
                tree = ast.parse(p.read_text())
                for node in ast.walk(tree):
                    if isinstance(
                        node, (ast.FunctionDef, ast.AsyncFunctionDef)
                    ) and node.name.startswith("test_"):
                        key = str(p.relative_to(root)) + "::" + node.name
                        # Duplicate names in separate classes get class-independent line identity.
                        if key in result:
                            key += ":" + str(node.lineno)
                        result[key] = {
                            "classification": "UNKNOWN",
                            "disposition": "RUN",
                            "reason": "Retain until assertion-level review; no filename exclusions",
                        }
            elif p.name.endswith(".test.mjs"):
                for name in re.findall(
                    r"\btest\([\s]*[\"\x27]([^\"\x27]+)", p.read_text()
                ):
                    result[str(p.relative_to(root)) + "::" + name] = {
                        "classification": "UNKNOWN",
                        "disposition": "RUN",
                        "reason": "Existing Node test remains mandatory",
                    }
    return result


def validate(root=ROOT):
    lock = json.loads((root / "scripts/ci/action-lock.json").read_text())
    pins = {(k.split("@")[0], v) for k, v in lock.items()}
    manifest = json.loads((root / ".ci/scope-manifest.json").read_text())
    if manifest.get("schema") != 1 or set(manifest["tests"]) != set(
        test_inventory(root)
    ):
        raise ValueError(
            "Test scope inventory changed: review and regenerate manifest, never silently omit tests"
        )
    for key, row in manifest["tests"].items():
        if row["classification"] not in CLASSES or row["disposition"] != "RUN":
            raise ValueError(
                "Unapproved omission or excluded-positive classification: " + key
            )
    protected = manifest["protected_assertions"]
    for path, needles in protected.items():
        text = (root / path).read_text()
        if not all(needle in text for needle in needles):
            raise ValueError("Protective assertion removed: " + path)
    jobs = set()
    files = []
    for p in sorted((root / ".github/workflows").glob("*")):
        if p.suffix not in (".yml", ".yaml"):
            continue
        files.append(str(p.relative_to(root)))
        d = yaml.load(p.read_text(), Loader=yaml.BaseLoader)
        if d.get("permissions") != {"contents": "read"}:
            raise ValueError("Explicit read-only workflow default required: " + p.name)
        triggers = d.get("on", {})
        if p.name in ALWAYS_PR and "pull_request" not in triggers:
            raise ValueError("Mandatory PR verification trigger removed: " + p.name)
        if "pull_request_target" in triggers:
            raise ValueError("Untrusted privileged PR trigger prohibited")
        if "pull_request" in triggers and triggers["pull_request"] not in (
            "",
            None,
            {},
        ):
            raise ValueError(
                "PR verification must instantiate for every branch/path: " + p.name
            )
        for jid, j in d.get("jobs", {}).items():
            jobs.add(j.get("name", jid))
            if j.get("continue-on-error") == "true":
                raise ValueError("Mandatory jobs cannot hide errors")
            if "pull_request" in triggers and j.get("if", "") not in (
                "",
                "always()",
                "${{ always() }}",
            ):
                raise ValueError(
                    "Mandatory PR jobs cannot filter target/event or silently skip"
                )
            privileged = any(
                v == "write" for v in j.get("permissions", {}).values()
            ) or "self-hosted" in str(j.get("runs-on", ""))
            if privileged and "pull_request" in triggers:
                raise ValueError("Privileged job cannot consume PR code")
            if "self-hosted" in str(j.get("runs-on", "")) and (
                "SPRINT10_APPROVED" not in j.get("if", "")
                or "authorize" not in j.get("needs", [])
            ):
                raise ValueError("Self-hosted scheduling needs prior authorization")
            for s in j.get("steps", []):
                if s.get("continue-on-error") == "true":
                    raise ValueError("No hidden failing verification steps")
                uses = s.get("uses", "")
                if (
                    uses.startswith("actions/checkout@")
                    and s.get("with", {}).get("persist-credentials") != "false"
                ):
                    raise ValueError("Checkout credentials must not persist")
                if uses and not uses.startswith("./"):
                    repo, ref = uses.split("@")
                    if not re.fullmatch("[a-f0-9]{40}", ref) or (repo, ref) not in pins:
                        raise ValueError("Unreviewed action ref: " + uses)
        if p.name in ("local-uat-auto-deploy.yml", "stage-b-uat.yml"):
            if set(triggers) != {"workflow_dispatch"}:
                raise ValueError("Publication/UAT must remain manual-only")
    if not REQUIRED <= jobs:
        raise ValueError("Stable required contexts removed: " + str(REQUIRED - jobs))
    return {
        "status": "PASS",
        "workflow_count": len(files),
        "test_count": len(manifest["tests"]),
        "unknown_tests_run": sum(
            r["classification"] == "UNKNOWN" for r in manifest["tests"].values()
        ),
        "required_contexts_preserved": sorted(REQUIRED),
        "scope": "CI policy only; not release certification",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2))

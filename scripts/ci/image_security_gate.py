"""Fail-closed aggregate image policy: every scanned role remains mandatory.

Evidence completeness/identity is validated first; this separate required check
enforces the UNCHANGED zero High/Critical/Unknown and accountable licence rules.
No findings or legal statuses are rewritten by this gate.
"""

import argparse
import json
from pathlib import Path

from image_coverage import ROOT, contract, coverage
from security_manifest import validate


def evaluate(directory, source, root=ROOT):
    # Never accept a partial, swapped, stale or mismatched image inventory.
    coverage(directory, source, root)
    results = []
    for role in contract(root):
        name = role["role"]
        try:
            verdict = validate(directory / ("image-evidence-" + name))
        except (ValueError, KeyError, OSError, TypeError) as error:
            results.append(
                {"role": name, "status": "BLOCKED", "reason": str(error)}
            )
        else:
            results.append(
                {
                    "role": name,
                    "status": "POLICY_PASS",
                    "image_id": verdict["image_id"],
                }
            )
    blocked = [r for r in results if r["status"] != "POLICY_PASS"]
    return {
        "schema": 1,
        "status": "BLOCKED" if blocked else "POLICY_PASS",
        "exact_candidate_coverage": "PASS",
        "policy": "UNMODIFIED_ZERO_SEVERE_AND_ACCOUNTABLE_LICENSE_REVIEW",
        "blocked_roles": len(blocked),
        "images": results,
        "release_approved": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(args.directory, args.source)
    except (ValueError, KeyError, OSError, TypeError) as error:
        result = {
            "schema": 1,
            "status": "FAIL_EVIDENCE_INTEGRITY",
            "error": str(error),
            "release_approved": False,
        }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if result["status"] != "POLICY_PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

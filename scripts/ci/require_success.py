"""Aggregate required jobs without treating skipped/cancelled/missing as green."""

import json
import os


def validate(needs):
    if not isinstance(needs, dict) or not needs:
        raise ValueError("Required jobs missing")
    bad = {
        name: job.get("result")
        for name, job in needs.items()
        if job.get("result") != "success"
    }
    if bad:
        raise ValueError("Required verification did not succeed: " + str(bad))
    return True


if __name__ == "__main__":
    validate(json.loads(os.environ["NEEDS_JSON"]))
    print("Required job results verified; no acceptance or release promotion")

"""Recompute phase losses/duplicates from independently exported PostgreSQL rows."""

import argparse
import collections
from datetime import datetime, timezone
import json
from pathlib import Path


def reconcile(directory):
    scenario = json.loads((directory / "e2e.json").read_text())
    events = json.loads((directory / "db-events.json").read_text())
    results = []
    for phase in scenario["phases"]:
        cut = datetime.fromisoformat(phase["cut_utc"])
        counts = collections.Counter()
        for row in events:
            created = datetime.fromisoformat(row["created_at"])
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created <= cut:
                counts[row["event_id"]] += 1
        missing = sorted(set(phase["expected"]) - set(counts))
        assert (
            missing == phase["missing"]
        ), "API ledger and DB missing-ID evidence disagree"
        results.append(
            {
                "phase": phase["name"],
                "cut_utc": phase["cut_utc"],
                "expected": len(phase["expected"]),
                "api_missing_ids": phase["missing"],
                "db_missing_ids": missing,
                "db_rows_at_cut": sum(counts.values()),
                "db_distinct_at_cut": len(counts),
                "db_duplicates_at_cut": sum(counts.values()) - len(counts),
                "api_db_missing_ids_agree": True,
            }
        )
    assert not results[-1]["db_missing_ids"]
    (directory / "phase-db-reconciliation.json").write_text(
        json.dumps(results, indent=2) + "\n"
    )
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    print(json.dumps(reconcile(parser.parse_args().run), indent=2))

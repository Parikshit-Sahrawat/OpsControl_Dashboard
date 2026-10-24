"""Read-only, disposable PostgreSQL parity timing for topology views."""

import json
import statistics
import time

from app.unified.api import dependency_history, details
from scripts.topology_gate_probe import identifier, principal_session

org_ids = [identifier("org", n) for n in range(2)]
resource_id = identifier("resource-0", 479)


def sample(function):
    times = []
    with principal_session(org_ids) as db:
        for i in range(110):
            db.rollback()
            started = time.perf_counter()
            function(resource_id, db)
            duration = (time.perf_counter() - started) * 1000
            if i >= 10:
                times.append(duration)
    ordered = sorted(times)
    return {
        "samples": len(times),
        "p50_ms": round(ordered[49], 3),
        "p95_ms": round(ordered[94], 3),
        "p99_ms": round(ordered[98], 3),
        "mean_ms": round(statistics.mean(times), 3),
        "max_ms": round(max(times), 3),
    }


def main():
    print(
        json.dumps(
            {
                "details": sample(lambda rid, db: details(rid, db=db)),
                "history": sample(
                    lambda rid, db: dependency_history(rid, limit=200, offset=0, db=db)
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

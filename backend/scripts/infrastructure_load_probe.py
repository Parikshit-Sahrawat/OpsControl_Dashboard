"""Read-only infrastructure pagination and sustained request latency probe."""
import json
import os
import statistics
import time
import urllib.parse
import urllib.request

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TOKEN = os.environ["AUTH_TOKEN"]
ITERATIONS = max(1, min(100, int(os.environ.get("ITERATIONS", "30"))))
LIMIT = max(1, min(500, int(os.environ.get("PAGE_LIMIT", "10"))))

def request(offset):
    query = urllib.parse.urlencode({"limit": LIMIT, "offset": offset})
    req = urllib.request.Request(
        f"{BASE}/api/v1/infrastructure/resources?{query}",
        headers={"Authorization": "Bearer " + TOKEN},
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
        assert response.status == 200
    elapsed = (time.perf_counter() - start) * 1000
    data = json.loads(raw)
    assert data["offset"] == offset and data["limit"] == LIMIT
    assert len(data["resources"]) <= LIMIT
    assert data["has_more"] == (offset + len(data["resources"]) < data["total"])
    return data, elapsed, len(raw)

def main():
    timings, sizes = [], []
    first, elapsed, size = request(0)
    timings.append(elapsed)
    sizes.append(size)
    if first["has_more"]:
        second, elapsed, size = request(LIMIT)
        timings.append(elapsed)
        sizes.append(size)
        assert not ({r["id"] for r in first["resources"]} &
                    {r["id"] for r in second["resources"]}), "Overlapping pages"
    for _ in range(ITERATIONS):
        _, elapsed, size = request(0)
        timings.append(elapsed)
        sizes.append(size)
        time.sleep(1)
    ordered = sorted(timings)
    p95 = ordered[min(len(ordered)-1, int(0.95 * len(ordered)))]
    print(json.dumps({
        "result": "PASS", "requests": len(timings), "total": first["total"],
        "page_limit": LIMIT, "median_ms": round(statistics.median(timings), 1),
        "p95_ms": round(p95, 1), "max_ms": round(max(timings), 1),
        "max_response_bytes": max(sizes),
    }, indent=2))

if __name__ == "__main__":
    main()

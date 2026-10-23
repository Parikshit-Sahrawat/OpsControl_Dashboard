"""Disposable TOP-01 verification/benchmark; never run against shared data."""

import json
import os
import random
import secrets
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import Event, Lock, Thread, get_ident

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event, func, insert, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

import app.main  # noqa: F401 - register models and security hooks
from app.db.session import SessionLocal, engine
from app.models import Organization, VM
from app.security.access_control import request_permissions
from app.security.boundaries import selected_customers
from app.security.models import OrganizationMembership, User
from app.security.passwords import hash_password
from app.security.permission_catalog import PROVIDER_ID
from app.security.scope import Principal, current_principal
from app.unified.api import DependencyInput, add_dependency
from app.unified.models import MonitoringResource, ResourceDependency

SEED = 420042
URL = make_url(os.environ["DATABASE_URL"])
if (
    os.getenv("ENVIRONMENT") != "test"
    or os.getenv("OPSCONTROL_V16_ACCEPTANCE") != "1"
    or URL.host != "127.0.0.1"
    or URL.database != "opscontrol"
    or URL.username != "opscontrol"
):
    raise SystemExit("Owned loopback test PostgreSQL required")


def identifier(kind, number):
    return uuid.uuid5(uuid.NAMESPACE_URL, f"opscontrol-topology-{SEED}-{kind}-{number}")


def check(condition, label):
    if not condition:
        raise AssertionError(label)


def seed():
    rng = random.Random(SEED)
    org_ids = [identifier("org", n) for n in range(2)]
    all_ids = []
    password = secrets.token_urlsafe(32)
    with Session(engine) as db:
        for org, oid in enumerate(org_ids):
            db.add(
                Organization(
                    id=oid, name=f"TOP gate customer {org}", code=f"TOP-GATE-{org}"
                )
            )
        db.flush()
        for org, oid in enumerate(org_ids):
            ids = [identifier(f"resource-{org}", n) for n in range(500)]
            all_ids.append(ids)
            db.execute(
                insert(VM),
                [
                    {
                        "id": identifier(f"vm-{org}", n),
                        "organization_id": oid,
                        "hostname": f"overlap-{n}.invalid",
                        "environment": "TEST",
                        "os": "Linux" if n % 2 else "Windows",
                    }
                    for n in range(500)
                ],
            )
            db.execute(
                insert(MonitoringResource),
                [
                    {
                        "id": rid,
                        "organization_id": oid,
                        "domain": "VM",
                        "name": f"overlap-{n}",
                        "environment": "TEST",
                        "vm_id": identifier(f"vm-{org}", n),
                        "configuration": {},
                        "revision": 1,
                        "active": True,
                        "activation_status": "CONFIGURED",
                    }
                    for n, rid in enumerate(ids)
                ],
            )
        for org, oid in enumerate(org_ids):
            # Every edge points to a smaller index: valid, acyclic and scoped.
            edges = {(n, n - 1) for n in range(1, 480)}
            edges.update((n, 0) for n in range(2, 480))
            edges.update((479, n) for n in range(1, 251))
            while len(edges) < 1500:
                upper = rng.randrange(2, 480)
                edges.add((upper, rng.randrange(upper)))
            check(len(edges) == 1500, "edge seed count")
            db.execute(
                insert(ResourceDependency),
                [
                    {
                        "id": identifier(f"edge-{org}", n),
                        "organization_id": oid,
                        "resource_id": all_ids[org][child],
                        "depends_on_id": all_ids[org][parent],
                        "relationship_type": "DEPENDS_ON",
                        "service_identity": "",
                        "valid_from": datetime(2026, 1, 1, tzinfo=timezone.utc),
                    }
                    for n, (child, parent) in enumerate(sorted(edges))
                ],
            )
        for name, admin, memberships in (
            ("top-gate-admin", True, ()),
            ("top-gate-a", False, ((org_ids[0], "org_admin"),)),
            ("top-gate-b", False, ((org_ids[1], "viewer"),)),
        ):
            user = User(
                id=identifier("user", name),
                username=name,
                full_name=name,
                password_hash=hash_password(password),
                active=True,
                platform_admin=admin,
                service_provider_id=PROVIDER_ID,
            )
            db.add(user)
            db.flush()
            for org_id, role in memberships:
                db.add(
                    OrganizationMembership(
                        user_id=user.id, organization_id=org_id, role=role
                    )
                )
        db.commit()
    return org_ids, all_ids, password


@contextmanager
def principal_session(org_ids):
    principal = Principal(
        user_id=identifier("user", "top-gate-admin"),
        username="top-gate-admin",
        platform_admin=True,
        roles={},
        service_provider_id=PROVIDER_ID,
        customer_directory_ids=frozenset(org_ids),
    )
    p = current_principal.set(principal)
    c = selected_customers.set(frozenset({org_ids[0]}))
    k = request_permissions.set(("resources.update",))
    db = SessionLocal()
    db.info["opscontrol_principal"] = principal
    try:
        yield db
    finally:
        db.close()
        request_permissions.reset(k)
        selected_customers.reset(c)
        current_principal.reset(p)


def summary(values):
    ordered = sorted(values)

    def pct(p):
        return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * p))]

    return {
        "samples": len(values),
        "min_ms": round(ordered[0], 3),
        "p50_ms": round(pct(0.50), 3),
        "p95_ms": round(pct(0.95), 3),
        "p99_ms": round(pct(0.99), 3),
        "max_ms": round(ordered[-1], 3),
        "mean_ms": round(statistics.mean(values), 3),
    }


def main():
    org_ids, ids, password = seed()
    results = {"seed": SEED, "base_counts": {"resources": 1000, "relationships": 3000}}
    with Session(engine) as db:
        results["postgresql_version"] = db.scalar(text("SHOW server_version"))
        results["revision"] = db.scalar(text("SELECT version_num FROM alembic_version"))
        check(
            db.scalar(
                select(func.count())
                .select_from(MonitoringResource)
                .where(MonitoringResource.organization_id.in_(org_ids))
            )
            == 1000,
            "resource count",
        )
        check(
            db.scalar(
                select(func.count())
                .select_from(ResourceDependency)
                .where(ResourceDependency.organization_id.in_(org_ids))
            )
            == 3000,
            "edge count",
        )

    client = TestClient(app.main.app, raise_server_exceptions=False)
    headers = {}
    for name in ("admin", "a", "b"):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": f"top-gate-{name}", "password": password},
        )
        check(response.status_code == 200, f"login {name}: {response.status_code}")
        headers[name] = {"Authorization": f"Bearer {response.json()['access_token']}"}
    a, b = ids
    scoped_a = {**headers["a"], "X-OpsControl-Customers": str(org_ids[0])}
    forged_b = {**headers["a"], "X-OpsControl-Customers": str(org_ids[1])}
    path = f"/api/v1/unified/resources/{a[479]}"
    first = client.get(path, headers=scoped_a)
    check(first.status_code == 200, f"authorized detail {first.status_code}")
    check(len(first.json()["dependencies"]) == 50, "50-edge preview")
    check(first.json()["dependency_has_more"], "preview truncation")
    check(first.json()["dependency_total"] >= 251, "preview total")
    hidden = client.get(f"/api/v1/unified/resources/{b[479]}", headers=scoped_a)
    forged = client.get(f"/api/v1/unified/resources/{b[479]}", headers=forged_b)
    check(hidden.status_code == forged.status_code == 404, "foreign detail isolation")
    check(hidden.json() == forged.json(), "foreign ID error detail leak")
    denied_history = client.get(
        f"/api/v1/unified/resources/{b[479]}/dependencies", headers=scoped_a
    )
    check(denied_history.status_code == 404, "foreign history isolation")
    denied_write = client.post(
        f"/api/v1/unified/resources/{b[479]}/dependencies",
        json={"depends_on_id": str(b[2])},
        headers=scoped_a,
    )
    check(denied_write.status_code in (403, 404), "foreign mutation isolation")
    denied_edge = client.post(
        path + "/dependencies", json={"depends_on_id": str(b[2])}, headers=scoped_a
    )
    check(denied_edge.status_code in (403, 404), "cross-customer edge denial")
    bad_type = client.post(
        path + "/dependencies",
        json={"depends_on_id": str(a[2]), "relationship_type": "FORGED"},
        headers=scoped_a,
    )
    check(bad_type.status_code == 422, "invalid type denial")
    self_edge = client.post(
        path + "/dependencies", json={"depends_on_id": str(a[479])}, headers=scoped_a
    )
    check(self_edge.status_code == 422, "self cycle denial")
    deep_cycle = client.post(
        f"/api/v1/unified/resources/{a[0]}/dependencies",
        json={"depends_on_id": str(a[479])},
        headers=scoped_a,
    )
    check(deep_cycle.status_code == 409, f"deep cycle denial: {deep_cycle.status_code}")
    two_cycle = client.post(
        f"/api/v1/unified/resources/{a[0]}/dependencies",
        json={"depends_on_id": str(a[1])},
        headers=scoped_a,
    )
    multi_cycle = client.post(
        f"/api/v1/unified/resources/{a[0]}/dependencies",
        json={"depends_on_id": str(a[3])},
        headers=scoped_a,
    )
    check(two_cycle.status_code == multi_cycle.status_code == 409, "short cycle denial")
    duplicate = client.post(
        path + "/dependencies", json={"depends_on_id": str(a[478])}, headers=scoped_a
    )
    check(duplicate.status_code == 409, "duplicate active edge denial")
    limits = {
        str(n): client.get(
            path + f"/dependencies?limit={n}", headers=scoped_a
        ).status_code
        for n in (0, 1, 200, 201)
    }
    check(
        limits == {"0": 422, "1": 200, "200": 200, "201": 422}, "history limit contract"
    )
    total = first.json()["dependency_total"]
    history_ids = []
    for offset in range(0, total, 200):
        page = client.get(
            path + f"/dependencies?limit=200&offset={offset}", headers=scoped_a
        )
        check(
            page.status_code == 200 and page.json()["total"] == total,
            "stable history page",
        )
        history_ids.extend(row["id"] for row in page.json()["items"])
    check(
        len(history_ids) == total == len(set(history_ids)), "history page completeness"
    )
    empty = client.get(f"/api/v1/unified/resources/{a[499]}", headers=scoped_a)
    check(
        empty.status_code == 200 and empty.json()["dependency_total"] == 0,
        "empty preview",
    )
    inventory = client.get(
        "/api/v1/unified/resources?domain=VM&limit=1", headers=scoped_a
    )
    check(
        inventory.status_code == 200 and inventory.json()["total"] == 500,
        "scoped inventory total",
    )
    created = client.post(
        path + "/dependencies", json={"depends_on_id": str(a[276])}, headers=scoped_a
    )
    check(created.status_code == 201, f"authorized API creation: {created.status_code}")
    created_id = created.json()["id"]
    fetched = client.get(path + "/dependencies?limit=200", headers=scoped_a)
    check(
        any(row["id"] == created_id for row in fetched.json()["items"]),
        "created edge retrieval",
    )
    results["api"] = {
        "authorized_detail": first.status_code,
        "foreign_detail": hidden.status_code,
        "forged_scope": forged.status_code,
        "foreign_history": denied_history.status_code,
        "foreign_write": denied_write.status_code,
        "cross_customer_edge": denied_edge.status_code,
        "invalid_type": bad_type.status_code,
        "self_cycle": self_edge.status_code,
        "two_cycle": two_cycle.status_code,
        "multi_cycle": multi_cycle.status_code,
        "deep_cycle": deep_cycle.status_code,
        "duplicate": duplicate.status_code,
        "created_edge": created.status_code,
        "inventory_total_a": inventory.json()["total"],
        "empty_preview_total": empty.json()["dependency_total"],
        "history_limits": limits,
        "history_total": total,
        "history_unique_ids": len(history_ids),
    }

    def measure_api(url):
        sql_count = [0]

        def count_request(conn, cursor, statement, parameters, context, executemany):
            sql_count[0] += 1

        samples, query_counts = [], []
        client.get(url, headers=scoped_a)  # separate warm-up
        event.listen(engine, "before_cursor_execute", count_request)
        try:
            for _ in range(20):
                before = sql_count[0]
                started = time.perf_counter()
                response = client.get(url, headers=scoped_a)
                samples.append((time.perf_counter() - started) * 1000)
                query_counts.append(sql_count[0] - before)
                check(response.status_code == 200, "measured read response")
        finally:
            event.remove(engine, "before_cursor_execute", count_request)
        return {**summary(samples), "query_counts": query_counts}

    results["read_benchmark"] = {
        "graph_preview": measure_api(path),
        "history_200": measure_api(path + "/dependencies?limit=200"),
    }

    # Time the actual handler while counting every SQL statement per caller thread.
    counts = {}
    count_lock = Lock()

    def count_sql(conn, cursor, statement, parameters, context, executemany):
        ident = get_ident()
        with count_lock:
            if ident in counts:
                counts[ident] += 1

    event.listen(engine, "before_cursor_execute", count_sql)

    def operation(child, parent):
        ident = get_ident()
        with count_lock:
            counts[ident] = 0
        started = time.perf_counter()
        with principal_session(org_ids) as db:
            transaction_started = time.perf_counter()
            try:
                add_dependency(a[child], DependencyInput(depends_on_id=a[parent]), db)
                status = 201
            except HTTPException as error:
                status = error.status_code
                db.rollback()
            transaction_ms = (time.perf_counter() - transaction_started) * 1000
        elapsed = (time.perf_counter() - started) * 1000
        with count_lock:
            queries = counts.pop(ident)
        return {
            "status": status,
            "ms": round(elapsed, 3),
            "transaction_ms": round(transaction_ms, 3),
            "queries": queries,
        }

    try:
        # Warm-up is excluded. A high-index child points only to lower indices.
        warm = operation(479, 251)
        check(warm["status"] == 201, f"warm-up creation: {warm}")
        samples = [operation(479, n) for n in range(252, 272)]
        check(all(item["status"] == 201 for item in samples), "measured creation")
        rejects = [operation(0, 479) for _ in range(20)]
        check(
            all(item["status"] == 409 for item in rejects), "measured cycle rejection"
        )
        tasks = [(479, n) for n in range(272, 276)] + [(n, 479) for n in range(4)]
        stop_sampling = Event()
        waits = []

        def sample_locks():
            with Session(engine) as observer:
                while not stop_sampling.is_set():
                    rows = (
                        observer.execute(
                            text(
                                "SELECT wait_event FROM pg_stat_activity "
                                "WHERE datname=current_database() AND pid<>pg_backend_pid() "
                                "AND wait_event_type='Lock'"
                            )
                        )
                        .scalars()
                        .all()
                    )
                    waits.append(rows)
                    observer.rollback()
                    stop_sampling.wait(0.02)

        sampler = Thread(target=sample_locks, daemon=True)
        sampler.start()
        with ThreadPoolExecutor(max_workers=8) as pool:
            concurrent = list(pool.map(lambda pair: operation(*pair), tasks))
        stop_sampling.set()
        sampler.join(timeout=5)
        check(
            [r["status"] for r in concurrent] == [201] * 4 + [409] * 4,
            f"concurrent outcomes: {concurrent}",
        )
    finally:
        event.remove(engine, "before_cursor_execute", count_sql)
    with Session(engine) as db:
        active = db.scalars(
            select(ResourceDependency).where(
                ResourceDependency.organization_id == org_ids[0],
                ResourceDependency.valid_to.is_(None),
            )
        ).all()
        adjacency = {}
        for edge in active:
            adjacency.setdefault(edge.resource_id, []).append(edge.depends_on_id)
        visiting, visited = set(), set()

        def visit(node):
            if node in visiting:
                return False
            if node in visited:
                return True
            visiting.add(node)
            for parent in adjacency.get(node, ()):
                if not visit(parent):
                    return False
            visiting.remove(node)
            visited.add(node)
            return True

        check(all(visit(node) for node in a), "committed cycle detected")
        check(len(active) == 1500 + 1 + 1 + 20 + 4, "concurrent edge count")
        plan = db.execute(
            text(
                "EXPLAIN (FORMAT JSON) SELECT depends_on_id FROM resource_dependencies WHERE resource_id=:id AND valid_to IS NULL"
            ),
            {"id": a[479]},
        ).scalar()
        results["query_plan"] = plan[0]["Plan"] if isinstance(plan, list) else plan
    results["benchmark"] = {
        "create": {
            **summary([r["ms"] for r in samples]),
            "query_counts": [r["queries"] for r in samples],
            "transaction_ms": summary([r["transaction_ms"] for r in samples]),
        },
        "cycle_rejection": {
            **summary([r["ms"] for r in rejects]),
            "query_counts": [r["queries"] for r in rejects],
            "transaction_ms": summary([r["transaction_ms"] for r in rejects]),
        },
        "concurrent_eight": concurrent,
        "committed_active_edges_customer_a": len(active),
        "committed_cycle": False,
        "lock_sample_count": len(waits),
        "lock_wait_samples": sum(bool(row) for row in waits),
        "max_concurrent_lock_waiters": max((len(row) for row in waits), default=0),
        "lock_wait_events": sorted({event for row in waits for event in row}),
    }
    retired = client.delete(path + f"/dependencies/{created_id}", headers=scoped_a)
    check(retired.status_code == 204, "history retirement")
    with Session(engine) as db:
        row = db.get(ResourceDependency, uuid.UUID(created_id))
        check(row.valid_to is not None, "retired edge remains in history")
    results["api"]["retired_edge"] = retired.status_code
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()

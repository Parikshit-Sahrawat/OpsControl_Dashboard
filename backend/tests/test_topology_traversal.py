"""Disposable PostgreSQL regressions for bounded dependency traversal and locking."""

import hashlib
import os
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import Barrier, Event, get_ident

from fastapi import HTTPException
from sqlalchemy import event, func, insert, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

import app.main  # noqa: F401 - register security and model hooks
from app.db.session import SessionLocal, engine
from app.models import Organization, VM
from app.security.access_control import request_permissions
from app.security.boundaries import selected_customers, specification
from app.security.models import User
from app.security.permission_catalog import PROVIDER_ID
from app.security.scope import Principal, current_principal
from app.unified.api import DependencyInput, add_dependency
from app.unified.models import MonitoringResource, ResourceDependency


@unittest.skipUnless(
    os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1",
    "Owned disposable PostgreSQL required",
)
class TopologyTraversalTests(unittest.TestCase):
    def setUp(self):
        self.org_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.ids = [uuid.uuid4() for _ in range(20)]
        suffix = uuid.uuid4().hex[:12]
        with SessionLocal() as db:
            db.info["unified_manual_binding"] = True
            db.add(
                Organization(id=self.org_id, name="Traversal " + suffix, code=suffix)
            )
            db.add(
                User(
                    id=self.user_id,
                    username="traversal-" + suffix,
                    full_name="Traversal test",
                    password_hash="not-a-login",
                    service_provider_id=PROVIDER_ID,
                )
            )
            db.flush()
            vms = [
                VM(
                    organization_id=self.org_id,
                    hostname=f"traversal-{suffix}-{i}.invalid",
                    environment="TEST",
                    os="Linux",
                )
                for i in range(len(self.ids))
            ]
            db.add_all(vms)
            db.flush()
            db.add_all(
                MonitoringResource(
                    id=rid,
                    organization_id=self.org_id,
                    domain="VM",
                    name=f"Traversal {i}",
                    environment="TEST",
                    vm_id=vms[i].id,
                    configuration={},
                    revision=1,
                    active=True,
                    activation_status="CONFIGURED",
                )
                for i, rid in enumerate(self.ids)
            )
            db.commit()

    @contextmanager
    def authority(self, db):
        principal = Principal(
            user_id=self.user_id,
            username="traversal-test",
            platform_admin=True,
            roles={},
            service_provider_id=PROVIDER_ID,
            customer_directory_ids=frozenset({self.org_id}),
        )
        p = current_principal.set(principal)
        c = selected_customers.set(frozenset({self.org_id}))
        k = request_permissions.set(("resources.update",))
        db.info["opscontrol_principal"] = principal
        try:
            yield
        finally:
            db.info["opscontrol_principal"] = None
            request_permissions.reset(k)
            selected_customers.reset(c)
            current_principal.reset(p)

    def add(self, child, parent):
        with SessionLocal() as db, self.authority(db):
            try:
                add_dependency(
                    self.ids[child],
                    DependencyInput(depends_on_id=self.ids[parent]),
                    db,
                )
                return 201
            except HTTPException as error:
                db.rollback()
                return error.status_code
            except IntegrityError:
                # Direct handler calls expose the current unique-index exception;
                # the authenticated HTTP contract is checked by the gate probe.
                db.rollback()
                return 409

    def active_edges(self):
        with SessionLocal() as db:
            return db.execute(
                select(
                    ResourceDependency.resource_id, ResourceDependency.depends_on_id
                ).where(
                    ResourceDependency.organization_id == self.org_id,
                    ResourceDependency.valid_to.is_(None),
                )
            ).all()

    def test_paths_duplicates_and_rollback(self):
        # Deep path, a second path, fan-in, fan-out, and a disconnected pair.
        for child, parent in [
            (5, 4),
            (4, 3),
            (3, 2),
            (2, 1),
            (1, 0),
            (5, 2),
            (6, 2),
            (7, 2),
            (8, 5),
            (8, 6),
            (10, 11),
        ]:
            self.assertEqual(self.add(child, parent), 201)
        before = set(self.active_edges())
        for child, parent, status in [
            (0, 0, 422),  # direct self-cycle
            (0, 1, 409),  # two-node cycle
            (0, 5, 409),  # deep and multi-path cycle
            (5, 4, 409),  # duplicate current edge
        ]:
            self.assertEqual(self.add(child, parent), status)
        self.assertEqual(set(self.active_edges()), before)
        self.assertEqual(self.add(12, 13), 201)  # separate component

    def test_eight_adversarial_concurrent_additions_remain_acyclic(self):
        barrier = Barrier(8)
        pairs = [(n, n + 1) for n in (0, 2, 4, 6)]
        tasks = pairs + [(parent, child) for child, parent in pairs]

        def attempt(pair):
            barrier.wait(timeout=10)
            return self.add(*pair)

        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(attempt, tasks))
        self.assertEqual(sorted(statuses), [201] * 4 + [409] * 4)
        edges = self.active_edges()
        self.assertEqual(len(edges), 4)
        self.assertFalse(
            any((parent, child) in edges for child, parent in edges),
            "Opposite edges committed across concurrent transactions",
        )

    def test_concurrent_duplicate_creates_one_current_edge(self):
        barrier = Barrier(8)

        def attempt(_):
            barrier.wait(timeout=10)
            return self.add(0, 1)

        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(attempt, range(8)))
        self.assertEqual(sorted(statuses), [201] + [409] * 7)
        self.assertEqual(self.active_edges(), [(self.ids[0], self.ids[1])])

    def test_lock_timeout_rolls_back_without_partial_edge(self):
        lock_key = int.from_bytes(
            hashlib.sha256(
                ("arch001-dependency:" + str(self.org_id)).encode()
            ).digest()[:8],
            "big",
            signed=True,
        )
        with SessionLocal() as holder, SessionLocal() as contender:
            holder.execute(select(func.pg_advisory_xact_lock(lock_key)))
            contender.execute(text("SET LOCAL lock_timeout = '75ms'"))
            with self.authority(contender):
                with self.assertRaises(DBAPIError):
                    add_dependency(
                        self.ids[0],
                        DependencyInput(depends_on_id=self.ids[1]),
                        contender,
                    )
            contender.rollback()
            holder.rollback()
        self.assertEqual(self.active_edges(), [])

    def test_deadlock_aborts_one_transaction_without_partial_edge(self):
        advisory_acquired = Event()
        worker_thread = {}

        def signal_advisory(conn, cursor, statement, parameters, context, executemany):
            if (
                "pg_advisory_xact_lock" in statement
                and get_ident() == worker_thread.get("id")
            ):
                advisory_acquired.set()

        def competing_add():
            worker_thread["id"] = get_ident()
            with SessionLocal() as db, self.authority(db):
                db.execute(text("SET LOCAL statement_timeout = '5s'"))
                try:
                    add_dependency(
                        self.ids[0], DependencyInput(depends_on_id=self.ids[1]), db
                    )
                    return "committed"
                except DBAPIError as error:
                    db.rollback()
                    return error.orig.sqlstate

        event.listen(engine, "after_cursor_execute", signal_advisory)
        try:
            with SessionLocal() as holder:
                holder.execute(text("SET LOCAL statement_timeout = '5s'"))
                holder.execute(
                    select(MonitoringResource)
                    .where(MonitoringResource.id == self.ids[0])
                    .with_for_update()
                )
                with ThreadPoolExecutor(max_workers=1) as pool:
                    pending = pool.submit(competing_add)
                    self.assertTrue(advisory_acquired.wait(timeout=5))
                    with self.authority(holder):
                        try:
                            add_dependency(
                                self.ids[0],
                                DependencyInput(depends_on_id=self.ids[2]),
                                holder,
                            )
                            holder_result = "committed"
                        except DBAPIError as error:
                            holder.rollback()
                            holder_result = error.orig.sqlstate
                    worker_result = pending.result(timeout=10)
        finally:
            event.remove(engine, "after_cursor_execute", signal_advisory)
        self.assertEqual(sorted((holder_result, worker_result)), ["40P01", "committed"])
        self.assertEqual(len(self.active_edges()), 1)

    def test_resource_limit_rejects_hidden_parent_without_exposing_edges(self):
        scope = specification(
            "LIMIT",
            {
                "permissions": ["resources.update"],
                "customers": [self.org_id],
                "resources": [self.ids[0], self.ids[2]],
            },
        )
        principal = Principal(
            user_id=self.user_id,
            username="restricted-operator",
            platform_admin=False,
            roles={self.org_id: "org_admin"},
            service_provider_id=PROVIDER_ID,
            boundaries=({"kind": "LIMIT", "specification": scope},),
        )
        with SessionLocal() as db:
            p = current_principal.set(principal)
            c = selected_customers.set(frozenset({self.org_id}))
            k = request_permissions.set(("resources.update",))
            db.info["opscontrol_principal"] = principal
            try:
                with self.assertRaises(HTTPException) as denied:
                    add_dependency(
                        self.ids[0],
                        DependencyInput(depends_on_id=self.ids[1]),
                        db,
                    )
                self.assertEqual(denied.exception.status_code, 404)
                db.rollback()
                add_dependency(
                    self.ids[0], DependencyInput(depends_on_id=self.ids[2]), db
                )
            finally:
                db.info["opscontrol_principal"] = None
                request_permissions.reset(k)
                selected_customers.reset(c)
                current_principal.reset(p)
        self.assertEqual(self.active_edges(), [(self.ids[0], self.ids[2])])

    def test_validation_bound_allows_999_reachable_nodes_but_rejects_1000(self):
        chain = [uuid.uuid4() for _ in range(1000)]
        vm_ids = [uuid.uuid4() for _ in chain]
        with SessionLocal() as db:
            db.execute(
                insert(VM),
                [
                    {
                        "id": vm_id,
                        "organization_id": self.org_id,
                        "hostname": f"bound-{vm_id}.invalid",
                        "environment": "TEST",
                        "os": "Linux",
                    }
                    for vm_id in vm_ids
                ],
            )
            db.execute(
                insert(MonitoringResource),
                [
                    {
                        "id": rid,
                        "organization_id": self.org_id,
                        "domain": "VM",
                        "name": f"Bound {i}",
                        "environment": "TEST",
                        "vm_id": vm_ids[i],
                        "configuration": {},
                        "revision": 1,
                        "active": True,
                        "activation_status": "CONFIGURED",
                    }
                    for i, rid in enumerate(chain)
                ],
            )
            db.execute(
                insert(ResourceDependency),
                [
                    {
                        "id": uuid.uuid4(),
                        "organization_id": self.org_id,
                        "resource_id": chain[i],
                        "depends_on_id": chain[i + 1],
                        "relationship_type": "DEPENDS_ON",
                        "service_identity": "",
                        "valid_from": datetime.now(timezone.utc),
                    }
                    for i in range(999)
                ],
            )
            db.commit()

        def connect(parent):
            with SessionLocal() as db, self.authority(db):
                try:
                    add_dependency(
                        self.ids[0], DependencyInput(depends_on_id=parent), db
                    )
                    return 201
                except HTTPException as error:
                    db.rollback()
                    return error.status_code

        self.assertEqual(connect(chain[0]), 409)
        self.assertEqual(connect(chain[1]), 201)


if __name__ == "__main__":
    unittest.main()

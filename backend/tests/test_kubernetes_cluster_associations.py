"""Controlled PostgreSQL checks for K8S-01; no live Kubernetes or AWS calls."""

import os
import unittest
import uuid
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

import app.main  # noqa: F401 - register models and security hooks
from app.api.discovery import ImportRequest, import_candidates
from app.api.resource_management import (
    ClusterAssociationChange,
    change_kubernetes_cluster_association,
    get_kubernetes_cluster,
    list_kubernetes_clusters,
)
from app.db.session import SessionLocal
from app.models import (
    DataSource,
    KubernetesClusterAssociation,
    KubernetesClusterAssociationDecision,
    Organization,
)
from app.security.access_control import request_permissions, route_permissions
from app.security.boundaries import selected_customers
from app.security.scope import Principal, current_principal
from app.security.models import User
from app.security.permission_catalog import PROVIDER_ID


@unittest.skipUnless(
    os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1",
    "Disposable PostgreSQL required",
)
class KubernetesClusterAssociationTests(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.addCleanup(self.db.close)
        suffix = uuid.uuid4().hex[:12]
        self.a = Organization(name="K8S A " + suffix, code="K8SA-" + suffix)
        self.b = Organization(name="K8S B " + suffix, code="K8SB-" + suffix)
        self.user = User(
            username="k8s-" + suffix,
            full_name="Controlled operator",
            password_hash="not-a-login",
            service_provider_id=PROVIDER_ID,
        )
        self.db.add_all([self.a, self.b, self.user])
        self.db.flush()
        self.sources = [
            DataSource(
                organization_id=org.id,
                name="EKS discovery " + suffix,
                source_type="AWS_EKS",
                connection_config={
                    "region": "ap-south-1",
                    "account_id": "123456789012",
                },
            )
            for org in (self.a, self.b)
        ]
        self.db.add_all(self.sources)
        self.db.commit()
        self.db.info["opscontrol_principal"] = None
        self.candidate = {
            "external_id": "aws:123456789012:ap-south-1:eks:sequence-eks",
            "resource_type": "EKS_CLUSTER",
            "cluster_name": "sequence-eks",
            "region": "ap-south-1",
            "account_id": "123456789012",
            "arn": "arn:aws:eks:ap-south-1:123456789012:cluster/sequence-eks",
            "provider_cluster_id": "verified-physical-cluster-1",
        }

    def principal(self, *customers, admin=False):
        return Principal(
            user_id=self.user.id,
            username=self.user.username,
            platform_admin=admin,
            roles={} if admin else {org.id: "viewer" for org in customers},
            customer_directory_ids=(
                frozenset({self.a.id, self.b.id}) if admin else frozenset()
            ),
        )

    def call(self, principal, customers, permission, function, *args, **kwargs):
        p = current_principal.set(principal)
        c = selected_customers.set(frozenset(customers))
        k = request_permissions.set((permission,))
        self.db.info["opscontrol_principal"] = principal
        try:
            return function(*args, db=self.db, **kwargs)
        finally:
            self.db.info["opscontrol_principal"] = None
            request_permissions.reset(k)
            selected_customers.reset(c)
            current_principal.reset(p)

    def import_for(self, source):
        # Seed legacy association history through the historical import handler
        # in this disposable test only; production source_access still rejects
        # new EKS imports. Authorization/revocation assertions remain unchanged.
        with patch("app.api.discovery.scan", return_value=[self.candidate]), patch(
            "app.api.discovery.source_access", return_value=source
        ):
            return self.call(
                self.principal(admin=True),
                [source.organization_id],
                "collectors.manage",
                import_candidates,
                source.id,
                ImportRequest(
                    approved_external_ids=[self.candidate["external_id"]], dry_run=False
                ),
            )["resources"][0]

    def test_two_customers_one_cluster_and_immediate_revocation(self):
        self.assertEqual(
            route_permissions("GET", "/api/v1/resource-management/kubernetes-clusters"),
            ("resources.view",),
        )
        self.assertEqual(
            route_permissions(
                "PATCH",
                "/api/v1/resource-management/kubernetes-clusters/cluster/associations/customer",
            ),
            ("resources.update",),
        )
        a_import = self.import_for(self.sources[0])
        b_import = self.import_for(self.sources[1])
        self.assertEqual(a_import["cluster_id"], b_import["cluster_id"])
        self.assertNotEqual(a_import["data_source_id"], b_import["data_source_id"])
        cluster_id = uuid.UUID(a_import["cluster_id"])

        def listing(principal, customers):
            return self.call(
                principal,
                customers,
                "resources.view",
                list_kubernetes_clusters,
                organization_id=[],
                limit=100,
                offset=0,
            )

        a = listing(self.principal(self.a), [self.a.id])
        b = listing(self.principal(self.b), [self.b.id])
        self.assertEqual(a["total"], 1)
        self.assertEqual(b["total"], 1)
        self.assertEqual(a["items"][0]["cluster_id"], b["items"][0]["cluster_id"])
        self.assertEqual(a["items"][0]["namespace_scope"], [])
        self.assertEqual(listing(self.principal(), [self.a.id])["total"], 0)
        self.assertEqual(listing(self.principal(self.a), [self.b.id])["total"], 0)
        self.assertEqual(
            len(
                self.call(
                    self.principal(self.a),
                    [self.a.id],
                    "resources.view",
                    get_kubernetes_cluster,
                    cluster_id,
                )["associations"]
            ),
            1,
        )

        with self.assertRaises(HTTPException) as denied:
            self.call(
                self.principal(self.a),
                [self.a.id],
                "resources.update",
                change_kubernetes_cluster_association,
                cluster_id,
                self.a.id,
                ClusterAssociationChange(
                    expected_revision=1, active=False, reason="Controlled revocation"
                ),
            )
        self.assertEqual(denied.exception.status_code, 403)
        result = self.call(
            self.principal(admin=True),
            [self.a.id],
            "resources.update",
            change_kubernetes_cluster_association,
            cluster_id,
            self.a.id,
            ClusterAssociationChange(
                expected_revision=1, active=False, reason="Controlled revocation"
            ),
        )
        self.assertEqual(result["association_revision"], 2)
        self.assertEqual(listing(self.principal(self.a), [self.a.id])["total"], 0)
        self.assertEqual(listing(self.principal(self.b), [self.b.id])["total"], 1)
        with self.assertRaises(HTTPException) as hidden:
            self.call(
                self.principal(self.a),
                [self.a.id],
                "resources.view",
                get_kubernetes_cluster,
                cluster_id,
            )
        self.assertEqual(hidden.exception.status_code, 404)
        with self.assertRaises(HTTPException) as stale:
            self.call(
                self.principal(admin=True),
                [self.a.id],
                "resources.update",
                change_kubernetes_cluster_association,
                cluster_id,
                self.a.id,
                ClusterAssociationChange(
                    expected_revision=1, active=False, reason="Stale revision"
                ),
            )
        self.assertEqual(stale.exception.status_code, 409)
        with self.assertRaises(ValidationError):
            ClusterAssociationChange(
                expected_revision=2, active=True, reason="Attempt stale reactivation"
            )
        again = self.import_for(self.sources[0])
        self.assertFalse(again["association_active"])
        self.assertEqual(again["association_revision"], 2)
        self.assertEqual(
            self.db.scalar(
                select(KubernetesClusterAssociation).where(
                    KubernetesClusterAssociation.organization_id == self.a.id
                )
            ).revision,
            2,
        )
        self.assertEqual(
            len(
                self.db.scalars(
                    select(KubernetesClusterAssociationDecision).where(
                        KubernetesClusterAssociationDecision.association_id
                        == self.db.scalar(
                            select(KubernetesClusterAssociation.id).where(
                                KubernetesClusterAssociation.organization_id
                                == self.a.id
                            )
                        )
                    )
                ).all()
            ),
            2,
        )
        self.assertEqual(
            [s.organization_id for s in self.sources], [self.a.id, self.b.id]
        )

    def test_forged_customer_boundary_and_immutable_history(self):
        imported = self.import_for(self.sources[0])
        cluster_id = uuid.UUID(imported["cluster_id"])
        viewer = self.principal(self.a)
        bounded = Principal(
            user_id=viewer.user_id,
            username=viewer.username,
            platform_admin=False,
            roles=viewer.roles,
            boundaries=(
                {
                    "kind": "DENY",
                    "specification": {
                        "customers": [str(self.a.id)],
                        "permissions": ["resources.view"],
                        "environments": [],
                        "resources": [str(cluster_id)],
                    },
                },
            ),
        )
        result = self.call(
            bounded,
            [self.a.id],
            "resources.view",
            list_kubernetes_clusters,
            organization_id=[],
            limit=100,
            offset=0,
        )
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["items"], [])
        with self.assertRaises(HTTPException) as hidden:
            self.call(
                bounded,
                [self.a.id],
                "resources.view",
                get_kubernetes_cluster,
                cluster_id,
            )
        self.assertEqual(hidden.exception.status_code, 404)
        limited = Principal(
            user_id=viewer.user_id,
            username=viewer.username,
            platform_admin=False,
            roles=viewer.roles,
            boundaries=(
                {
                    "kind": "LIMIT",
                    "specification": {
                        "customers": [str(self.a.id)],
                        "permissions": ["resources.view"],
                        "environments": [],
                        "resources": [str(cluster_id)],
                    },
                },
            ),
        )
        self.assertEqual(
            self.call(
                limited,
                [self.a.id],
                "resources.view",
                list_kubernetes_clusters,
                organization_id=[],
                limit=100,
                offset=0,
            )["total"],
            1,
        )
        self.assertEqual(
            self.call(
                viewer,
                [self.a.id],
                "resources.view",
                list_kubernetes_clusters,
                organization_id=[self.b.id],
                limit=100,
                offset=0,
            )["total"],
            0,
        )
        with self.assertRaises(HTTPException) as denied:
            self.call(
                self.principal(admin=True),
                [self.b.id],
                "resources.update",
                change_kubernetes_cluster_association,
                cluster_id,
                self.a.id,
                ClusterAssociationChange(
                    expected_revision=1,
                    active=False,
                    reason="Forged customer selection",
                ),
            )
        self.assertEqual(denied.exception.status_code, 403)
        decision = self.db.scalar(select(KubernetesClusterAssociationDecision))
        with self.assertRaises(DBAPIError):
            with self.db.begin_nested():
                self.db.execute(
                    text(
                        "UPDATE kubernetes_cluster_association_decisions SET reason = 'altered' WHERE id = :id"
                    ),
                    {"id": decision.id},
                )
        self.db.rollback()
        self.assertEqual(
            self.db.get(KubernetesClusterAssociationDecision, decision.id).reason,
            "Approved read-only EKS discovery import",
        )
        with self.assertRaises(DBAPIError):
            with self.db.begin_nested():
                self.db.execute(
                    text(
                        "UPDATE kubernetes_clusters SET provider_cluster_id = 'forged' WHERE id = :id"
                    ),
                    {"id": cluster_id},
                )
        self.db.rollback()
        with self.assertRaises(DBAPIError):
            with self.db.begin_nested():
                self.db.execute(
                    text(
                        "UPDATE kubernetes_cluster_associations SET revision = 9 WHERE cluster_id = :id"
                    ),
                    {"id": cluster_id},
                )
        self.db.rollback()

    def test_arn_without_physical_id_does_not_grant_shared_visibility(self):
        self.candidate.pop("provider_cluster_id")
        result = self.import_for(self.sources[0])
        self.assertEqual(result["cluster_identity_status"], "UNVERIFIED")
        self.assertNotIn("cluster_id", result)
        listing = self.call(
            self.principal(self.a),
            [self.a.id],
            "resources.view",
            list_kubernetes_clusters,
            organization_id=[],
            limit=100,
            offset=0,
        )
        self.assertEqual(listing["total"], 0)

    def test_non_admin_cannot_import_or_grant_cluster(self):
        customer_admin = Principal(
            user_id=self.user.id,
            username=self.user.username,
            platform_admin=False,
            roles={self.a.id: "org_admin"},
        )
        with patch("app.api.discovery.scan", return_value=[self.candidate]):
            with self.assertRaises(HTTPException) as denied:
                self.call(
                    customer_admin,
                    [self.a.id],
                    "collectors.manage",
                    import_candidates,
                    self.sources[0].id,
                    ImportRequest(
                        approved_external_ids=[self.candidate["external_id"]],
                        dry_run=False,
                    ),
                )
        self.assertEqual(denied.exception.status_code, 403)
        self.db.rollback()

    def test_same_arn_new_physical_id_is_quarantined(self):
        original = self.import_for(self.sources[0])
        self.candidate["provider_cluster_id"] = "different-physical-cluster"
        with self.assertRaises(HTTPException) as changed:
            self.import_for(self.sources[1])
        self.assertEqual(changed.exception.status_code, 409)
        self.db.rollback()
        associations = self.db.scalars(
            select(KubernetesClusterAssociation).where(
                KubernetesClusterAssociation.organization_id.in_([self.a.id, self.b.id])
            )
        ).all()
        self.assertEqual(len(associations), 1)
        self.assertEqual(str(associations[0].cluster_id), original["cluster_id"])

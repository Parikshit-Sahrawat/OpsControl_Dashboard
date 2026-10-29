"""Retained historical cluster data security after operational route removal.

Seed legacy records directly in a disposable database, never through a removed
import API. Preserve organization fences and immutable history assertions.
"""
import os
import unittest
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
import app.main  # register all security hooks
from app.db.session import SessionLocal
from app.models import (Organization, KubernetesCluster, KubernetesClusterAssociation,
                        KubernetesClusterAssociationDecision)
from app.security.models import User
from app.security.scope import Principal
from app.security.access_control import request_permissions
from app.security.permission_catalog import PROVIDER_ID

@unittest.skipUnless(os.getenv('OPSCONTROL_V16_ACCEPTANCE') == '1', 'Disposable PostgreSQL required')
class KubernetesClusterAssociationTests(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.addCleanup(self.db.close)
        self.addCleanup(self.db.rollback)
        suffix = uuid4().hex
        self.a = Organization(name='legacy a '+suffix, code='A'+suffix[:10])
        self.b = Organization(name='legacy b '+suffix, code='B'+suffix[:10])
        self.user = User(username='legacy-'+suffix, full_name='Synthetic operator',
                         password_hash='not-a-login', service_provider_id=PROVIDER_ID)
        self.db.add_all([self.a, self.b, self.user]); self.db.flush()
        self.cluster = KubernetesCluster(provider_identity='synthetic:'+suffix, provider_cluster_id=suffix)
        self.db.add(self.cluster); self.db.flush()
        self.associations = [KubernetesClusterAssociation(cluster_id=self.cluster.id,
            organization_id=o.id, revision=1, active=True) for o in (self.a, self.b)]
        self.db.add_all(self.associations); self.db.flush()
        self.decision = KubernetesClusterAssociationDecision(association_id=self.associations[0].id,
            actor_id=self.user.id, revision=1, active=True, reason='Synthetic legacy grant')
        self.db.add(self.decision); self.db.flush()

    def test_customer_isolation_and_forged_selection(self):
        token = request_permissions.set(('resources.view',))
        self.addCleanup(request_permissions.reset, token)
        for owner in (self.a, self.b):
            self.db.info['opscontrol_principal'] = Principal(self.user.id, self.user.username,
                                                          False, {owner.id:'viewer'})
            rows = self.db.scalars(select(KubernetesClusterAssociation)).all()
            self.assertEqual([r.organization_id for r in rows], [owner.id])
            other = self.b if owner == self.a else self.a
            self.assertEqual(self.db.scalars(select(KubernetesClusterAssociation).where(
                KubernetesClusterAssociation.organization_id == other.id)).all(), [])
        self.db.info['opscontrol_principal'] = Principal(self.user.id, self.user.username, False, {})
        self.assertEqual(self.db.scalars(select(KubernetesClusterAssociation)).all(), [])
        self.db.info['opscontrol_principal'] = None

    def test_legacy_resource_boundaries_and_foreign_write_denied(self):
        token = request_permissions.set(('resources.view',))
        self.addCleanup(request_permissions.reset, token)
        for kind, count in (('DENY', 0), ('LIMIT', 1)):
            principal = Principal(self.user.id, self.user.username, False, {self.a.id:'viewer'},
                boundaries=({'kind':kind, 'specification':{'customers':[str(self.a.id)],
                    'permissions':['resources.view'], 'resources':[str(self.cluster.id)],
                    'environments':[]}},))
            self.db.info['opscontrol_principal'] = principal
            self.assertEqual(len(self.db.scalars(select(KubernetesClusterAssociation)).all()), count)
        self.db.info['opscontrol_principal'] = Principal(self.user.id, self.user.username,
                                                        False, {self.a.id:'viewer'})
        with self.assertRaises(HTTPException):
            with self.db.begin_nested():
                self.associations[1].active = False
                self.associations[1].revision = 2
                self.db.flush()
        self.db.info['opscontrol_principal'] = None

    def test_legacy_history_identity_revision_and_delete_guards(self):
        for sql, identity in (
            ("UPDATE kubernetes_cluster_association_decisions SET reason='altered' WHERE id=:id", self.decision.id),
            ("DELETE FROM kubernetes_cluster_association_decisions WHERE id=:id", self.decision.id),
            ("UPDATE kubernetes_clusters SET provider_cluster_id='forged' WHERE id=:id", self.cluster.id),
            ("DELETE FROM kubernetes_clusters WHERE id=:id", self.cluster.id),
            ("UPDATE kubernetes_cluster_associations SET revision=9 WHERE id=:id", self.associations[0].id),
            ("DELETE FROM kubernetes_cluster_associations WHERE id=:id", self.associations[0].id),
        ):
            with self.subTest(sql=sql), self.assertRaises(DBAPIError):
                with self.db.begin_nested():
                    self.db.execute(text(sql), {'id':identity})
        self.db.expire_all()
        self.assertEqual(self.db.get(KubernetesClusterAssociationDecision,self.decision.id).reason,
                         'Synthetic legacy grant')
        self.assertEqual(len(self.db.scalars(select(KubernetesClusterAssociation)).all()),2)

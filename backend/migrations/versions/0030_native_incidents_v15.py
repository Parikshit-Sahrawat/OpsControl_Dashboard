"""Lossless native lifecycle and scoped alert evidence associations.

Legacy incident permission links were retired by 0026 but retained as history.
Mark those links inactive before restoring the catalog to prevent resurrecting
old privileges. No grants, role assignments or customer scopes are created;
all historical links remain recorded. Administrators must explicitly enable
new native permissions through the existing audited role editor.

Downgrade refuses populated extensions or new states; use a verified backup.
A downgrade also refuses new incident grants or inactive non-incident links,
which an old application could otherwise misinterpret. An empty downgrade
removes the active flag only for compatibility with the old
application, whose permission catalog ignores the retired incidents keys.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0030_native_incidents_v15"
down_revision = "0029_agent_v15"
branch_labels = depends_on = None
STATES = "'OPEN','ACKNOWLEDGED','INVESTIGATING','RECOVERY_IN_PROGRESS','MONITORING','RESOLVED','CLOSED'"


def upgrade():
    # Preserve retired links as inert records rather than granting or deleting.
    op.add_column(
        "role_permissions",
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE role_permissions SET active=false WHERE permission_key LIKE 'incidents.%'"
        )
    )
    # Catalog definitions alone confer no capabilities. Identity assignments,
    # non-incident role permissions and customer grants remain unchanged.
    for key, description in (
        ("incidents.view", "View native incident evidence"),
        ("incidents.acknowledge", "Acknowledge native incidents"),
        ("incidents.manage", "Manage native incidents and verified recovery"),
    ):
        connection.execute(
            sa.text(
                "INSERT INTO permissions(key,description,delegable) VALUES (:key,:description,true) ON CONFLICT(key) DO UPDATE SET description=excluded.description"
            ),
            {"key": key, "description": description},
        )
    op.drop_constraint("ck_incident_status", "operational_incidents", type_="check")
    op.create_check_constraint(
        "ck_incident_status", "operational_incidents", "status IN (" + STATES + ")"
    )
    op.create_unique_constraint(
        "uq_operational_incident_org_id",
        "operational_incidents",
        ["organization_id", "id"],
    )
    op.create_unique_constraint(
        "uq_alert_state_org_id", "alert_states", ["organization_id", "id"]
    )
    op.create_table(
        "native_incident_details",
        sa.Column("incident_id", sa.UUID(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "assigned_user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("escalation_level", sa.Integer(), nullable=False),
        sa.Column("recovery_started_at", sa.DateTime(timezone=True)),
        sa.Column("monitoring_started_at", sa.DateTime(timezone=True)),
        sa.Column("monitoring_seconds", sa.Integer(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("evidence", JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id", "incident_id"],
            ["operational_incidents.organization_id", "operational_incidents.id"],
            name="fk_native_details_incident_scope",
        ),
        sa.CheckConstraint(
            "revision > 0 AND escalation_level >= 0 AND monitoring_seconds >= 60",
            name="ck_native_details_limits",
        ),
    )
    op.create_index(
        "ix_native_incident_details_organization_id",
        "native_incident_details",
        ["organization_id"],
    )
    op.create_table(
        "native_incident_alerts",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("incident_id", sa.UUID(), nullable=False),
        sa.Column("alert_state_id", sa.UUID(), nullable=False),
        sa.Column("evidence", JSONB(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id", "incident_id"],
            ["operational_incidents.organization_id", "operational_incidents.id"],
            name="fk_native_alert_incident_scope",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "alert_state_id"],
            ["alert_states.organization_id", "alert_states.id"],
            name="fk_native_alert_scope",
        ),
        sa.UniqueConstraint(
            "incident_id", "alert_state_id", name="uq_native_incident_alert"
        ),
    )
    for key in ("organization_id", "incident_id", "alert_state_id"):
        op.create_index(
            "ix_native_incident_alerts_" + key, "native_incident_alerts", [key]
        )


def downgrade():
    populated = op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM native_incident_details) OR EXISTS (SELECT 1 FROM native_incident_alerts) OR EXISTS (SELECT 1 FROM operational_incidents WHERE status NOT IN ('OPEN','ACKNOWLEDGED','INVESTIGATING','RESOLVED')) OR EXISTS (SELECT 1 FROM role_permissions WHERE (active AND permission_key LIKE 'incidents.%') OR (NOT active AND permission_key NOT LIKE 'incidents.%'))"
        )
    )
    if populated:
        raise RuntimeError(
            "Native incident history or permission activation changes exist; restore a verified backup instead of destructive downgrade"
        )
    # Keep capability catalog definitions; removal could break explicit admin-created assignments.
    op.drop_table("native_incident_alerts")
    op.drop_table("native_incident_details")
    op.drop_constraint("uq_alert_state_org_id", "alert_states", type_="unique")
    op.drop_constraint(
        "uq_operational_incident_org_id", "operational_incidents", type_="unique"
    )
    op.drop_constraint("ck_incident_status", "operational_incidents", type_="check")
    op.create_check_constraint(
        "ck_incident_status",
        "operational_incidents",
        "status IN ('OPEN','ACKNOWLEDGED','INVESTIGATING','RESOLVED')",
    )
    op.drop_column("role_permissions", "active")

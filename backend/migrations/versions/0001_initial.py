"""initial opscontrol schema"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0001_initial"
down_revision=None
branch_labels=None
depends_on=None
execution_type = sa.Enum(
    "SCHEDULED",
    "MANUAL",
    name="executiontype",
    create_type=False,
)

execution_status = sa.Enum(
    "SUCCESS",
    "FAILED",
    "RUNNING",
    "LONG_RUNNING",
    "NO_RUN",
    "NO_RESPONSE",
    name="executionstatus",
    create_type=False,
)

investigation_status = sa.Enum(
    "NEW",
    "ACKNOWLEDGED",
    "INVESTIGATING",
    "ROOT_CAUSE_IDENTIFIED",
    "RECOVERY_IN_PROGRESS",
    "MONITORING",
    "RESOLVED",
    name="investigationstatus",
    create_type=False,
)
def upgrade():
    bind=op.get_bind()
    execution_type.create(bind, checkfirst=True)
    execution_status.create(bind, checkfirst=True)
    investigation_status.create(bind, checkfirst=True)
    op.create_table("organizations",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("name",sa.String(200),nullable=False,unique=True),sa.Column("code",sa.String(50),nullable=F[...]
    op.create_table("vms",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("organization_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("organizations.id"),nullable=False),sa.[...]
    op.create_index("ix_vms_organization_id","vms",["organization_id"])
    op.create_table("applications",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("vm_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("vms.id"),nullable=False),sa.Column("nam[...]
    op.create_table("pentaho_instances",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("vm_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("vms.id"),nullable=False),sa.Column[...]
    op.create_table("job_orders",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("organization_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("organizations.id"),nullable=Fal[...]
    op.create_table("job_order_histories",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("job_order_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("job_orders.id"),nullable=[...]
    op.create_index("ix_job_order_histories_job_order_id","job_order_histories",["job_order_id"])
    op.create_table("job_step_executions",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("history_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("job_order_histories.id"),nu[...]
    op.create_index("ix_job_step_executions_history_id","job_step_executions",["history_id"])
    op.create_table("investigations",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("history_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("job_order_histories.id"),nullabl[...]
    op.create_table("investigation_transitions",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("investigation_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("investigations.[...]
    op.create_index("ix_investigation_transitions_investigation_id","investigation_transitions",["investigation_id"])
    op.create_table("operator_notes",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("investigation_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("investigations.id"),nullab[...]
    op.create_index("ix_operator_notes_investigation_id","operator_notes",["investigation_id"])
    op.create_table("alert_incident_events",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("history_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("job_order_histories.id"),[...]
    op.create_index("ix_alert_incident_events_history_id","alert_incident_events",["history_id"])
def downgrade():
    for table in ["alert_incident_events","operator_notes","investigation_transitions","investigations","job_step_executions","job_order_histories","job_orders","pentaho_instances","applications","vms[...]
    bind=op.get_bind();investigation_status.drop(bind,checkfirst=True);execution_status.drop(bind,checkfirst=True);execution_type.drop(bind,checkfirst=True)

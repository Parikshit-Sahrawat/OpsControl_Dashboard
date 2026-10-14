"""Durable recipient-scoped in-app delivery; preserve existing notifications."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0031_in_app_notifications"
down_revision = "0030_native_incidents_v15"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "notification_preferences",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
    )
    op.create_table(
        "in_app_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "delivery_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alert_notification_deliveries.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("delivery_id", "user_id", name="uq_in_app_delivery_user"),
    )
    op.create_index(
        "ix_in_app_notifications_organization_id",
        "in_app_notifications",
        ["organization_id"],
    )
    op.create_index(
        "ix_in_app_notifications_user_id", "in_app_notifications", ["user_id"]
    )


def downgrade():
    db = op.get_bind()
    if db.scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM in_app_notifications) OR EXISTS(SELECT 1 FROM users WHERE notification_preferences <> '{}'::jsonb)"
        )
    ):
        raise RuntimeError(
            "Recipient history/preferences exist; retain additive schema or restore verified backup"
        )
    op.drop_table("in_app_notifications")
    op.drop_column("users", "notification_preferences")

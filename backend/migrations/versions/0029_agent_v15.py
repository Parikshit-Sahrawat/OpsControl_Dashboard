"""Agent credential renewal and evidence-backed reconciliation.

All columns are additive; existing identity hashes and revisions are retained.
Downgrade removes only reconciliation metadata, never telemetry or credentials.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0029_agent_v15"
down_revision = "0028_attribute_registry"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "managed_agents",
        sa.Column(
            "method_health",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    for name in ("downloaded_revision", "verified_revision", "last_working_revision"):
        op.add_column("managed_agents", sa.Column(name, sa.Integer(), nullable=True))
    op.add_column(
        "managed_agents",
        sa.Column("configuration_sha256", sa.String(64), nullable=True),
    )
    op.add_column(
        "managed_agents", sa.Column("previous_token_hash", sa.String(64), nullable=True)
    )
    op.add_column(
        "managed_agents",
        sa.Column(
            "previous_token_expires_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    for name in ("applied_at", "verified_at", "credential_renewed_at"):
        op.add_column(
            "managed_agents", sa.Column(name, sa.DateTime(timezone=True), nullable=True)
        )


def downgrade():
    op.drop_column("managed_agents", "method_health")
    for name in (
        "previous_token_expires_at",
        "previous_token_hash",
        "credential_renewed_at",
        "verified_at",
        "applied_at",
        "configuration_sha256",
        "last_working_revision",
        "verified_revision",
        "downloaded_revision",
    ):
        op.drop_column("managed_agents", name)

"""phase 1 resource management hardening

Revision ID: 0011_phase1_resource_management
Revises: 0010_template_attachments
"""
from alembic import op

revision = "0011_phase1_resource_management"
down_revision = "0010_template_attachments"
branch_labels = None
depends_on = None


def upgrade():
    # Organization CRUD/isolation reuses the existing organizations table.
    # This revision is an explicit Phase 1 architecture checkpoint.
    pass


def downgrade():
    pass

"""Drop legacy read_audit table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-08 19:10:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove the unused legacy audit table."""
    op.drop_table("read_audit")


def downgrade() -> None:
    """Recreate the legacy audit table for downgrade compatibility."""
    op.create_table(
        "read_audit",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_key", sa.String(length=500), nullable=False),
        sa.Column("change_type", sa.String(length=20), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("sync_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_read_audit_entity", "read_audit", ["entity_type", "entity_id"])
    op.create_index("ix_read_audit_session", "read_audit", ["sync_session_id"])
    op.create_index("ix_read_audit_changed_at", "read_audit", ["changed_at"])
    op.create_index("ix_read_audit_change_type", "read_audit", ["change_type"])

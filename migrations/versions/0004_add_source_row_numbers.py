"""Add Excel source row numbers to read models.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-24 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add nullable source row metadata and non-unique lookup indexes."""
    op.add_column(
        "read_deals",
        sa.Column("source_row_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "read_positions",
        sa.Column("source_row_number", sa.Integer(), nullable=True),
    )

    op.create_index(
        "ix_read_deals_period_source_row",
        "read_deals",
        ["period_year", "period_month", "source_row_number"],
        unique=False,
    )
    op.create_index(
        "ix_read_positions_deal_source_row",
        "read_positions",
        ["deal_id", "source_row_number"],
        unique=False,
    )
    op.create_index(
        "ix_read_positions_period_deal_position",
        "read_positions",
        ["period_year", "period_month", "deal_key", "position_number"],
        unique=False,
    )


def downgrade() -> None:
    """Remove source row metadata."""
    op.drop_index("ix_read_positions_period_deal_position", table_name="read_positions")
    op.drop_index("ix_read_positions_deal_source_row", table_name="read_positions")
    op.drop_index("ix_read_deals_period_source_row", table_name="read_deals")

    op.drop_column("read_positions", "source_row_number")
    op.drop_column("read_deals", "source_row_number")

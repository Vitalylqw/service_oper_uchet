"""Change purchase_price_amount and margin_amount precision to 5 decimal places.

Revision ID: 0003
Revises: 0002
Create Date: 2025-01-XX 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Change purchase_price_amount and margin_amount precision to 5 decimal places."""
    # Change purchase_price_amount from Numeric(15, 2) to Numeric(18, 5)
    op.alter_column(
        "read_positions",
        "purchase_price_amount",
        existing_type=sa.Numeric(precision=15, scale=2),
        type_=sa.Numeric(precision=18, scale=5),
        existing_nullable=True,
    )

    # Change margin_amount from Numeric(15, 2) to Numeric(18, 5)
    op.alter_column(
        "read_positions",
        "margin_amount",
        existing_type=sa.Numeric(precision=15, scale=2),
        type_=sa.Numeric(precision=18, scale=5),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Revert purchase_price_amount and margin_amount precision to 2 decimal places."""
    # Revert margin_amount from Numeric(18, 5) to Numeric(15, 2)
    op.alter_column(
        "read_positions",
        "margin_amount",
        existing_type=sa.Numeric(precision=18, scale=5),
        type_=sa.Numeric(precision=15, scale=2),
        existing_nullable=True,
    )

    # Revert purchase_price_amount from Numeric(18, 5) to Numeric(15, 2)
    op.alter_column(
        "read_positions",
        "purchase_price_amount",
        existing_type=sa.Numeric(precision=18, scale=5),
        type_=sa.Numeric(precision=15, scale=2),
        existing_nullable=True,
    )






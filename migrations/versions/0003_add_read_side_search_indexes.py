"""Add read-side search indexes for PostgreSQL.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-02 20:30:00.000000
"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add structural and full-text indexes for read-side search."""
    op.create_index(
        "ix_read_deals_invoice_number",
        "read_deals",
        ["invoice_number"],
        unique=False,
    )
    op.create_index(
        "ix_read_deals_invoice_date",
        "read_deals",
        ["invoice_date"],
        unique=False,
    )
    op.create_index(
        "ix_read_deals_client_invoice_number",
        "read_deals",
        ["client_name", "invoice_number"],
        unique=False,
    )
    op.create_index(
        "ix_read_deals_seller_invoice_number",
        "read_deals",
        ["seller", "invoice_number"],
        unique=False,
    )

    op.execute(
        """
        CREATE INDEX ix_read_deals_fts
        ON read_deals
        USING gin (
            (
                setweight(to_tsvector('russian', coalesce(client_name, '')), 'A') ||
                setweight(to_tsvector('russian', coalesce(seller, '')), 'A') ||
                setweight(to_tsvector('russian', coalesce(invoice_info, '')), 'B')
            )
        )
        """
    )

    op.create_index(
        "ix_read_positions_supplier_product",
        "read_positions",
        ["supplier_name", "product_name"],
        unique=False,
    )
    op.create_index(
        "ix_read_positions_client_product",
        "read_positions",
        ["client_name", "product_name"],
        unique=False,
    )

    op.execute(
        """
        CREATE INDEX ix_read_positions_fts
        ON read_positions
        USING gin (
            (
                setweight(to_tsvector('russian', coalesce(product_name, '')), 'A') ||
                setweight(to_tsvector('russian', coalesce(supplier_name, '')), 'B') ||
                setweight(to_tsvector('russian', coalesce(client_name, '')), 'B')
            )
        )
        """
    )


def downgrade() -> None:
    """Drop read-side search indexes."""
    op.execute("DROP INDEX IF EXISTS ix_read_positions_fts")
    op.drop_index("ix_read_positions_client_product", table_name="read_positions")
    op.drop_index("ix_read_positions_supplier_product", table_name="read_positions")

    op.execute("DROP INDEX IF EXISTS ix_read_deals_fts")
    op.drop_index("ix_read_deals_seller_invoice_number", table_name="read_deals")
    op.drop_index("ix_read_deals_client_invoice_number", table_name="read_deals")
    op.drop_index("ix_read_deals_invoice_date", table_name="read_deals")
    op.drop_index("ix_read_deals_invoice_number", table_name="read_deals")

"""Recreate read tables with new structure (read_deals v2, cascade FK).

Revision ID: 0003
Revises: 0002
Create Date: 2025-08-26 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Recreate read tables according to new specification."""
    # Drop dependent table first due to FK
    op.drop_table('read_positions', if_exists=True)
    op.drop_table('read_deals', if_exists=True)

    # Create read_deals table (v2)
    op.create_table(
        'read_deals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('deal_key', sa.String(length=255), nullable=False),
        sa.Column('hash_key', sa.String(length=32), nullable=False),
        sa.Column('client_name', sa.String(length=500), nullable=False),
        sa.Column('invoice_info', sa.String(length=500), nullable=False),
        sa.Column('invoice_number', sa.String(length=100), nullable=True),
        sa.Column('invoice_date', sa.String(length=20), nullable=True),
        sa.Column('period_month', sa.String(length=20), nullable=False),
        sa.Column('period_year', sa.String(length=4), nullable=False),
        sa.Column('period_full_name', sa.String(length=100), nullable=False),
        sa.Column('is_shipped', sa.String(length=20), nullable=True),
        sa.Column('is_paid', sa.String(length=20), nullable=True),
        sa.Column('upd_number', sa.String(length=100), nullable=True),
        sa.Column('seller', sa.String(length=300), nullable=True),
        sa.Column('total_revenue_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_margin_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_cost_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('kickback_amount_value', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('calc_revenue_amount', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('calc_margin_amount', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('calc_cost_amount', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('has_totals_error', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('items_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_quantity', sa.Numeric(precision=15, scale=3), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('deal_key'),
    )

    # Indexes
    op.create_index('ix_read_deals_client_name', 'read_deals', ['client_name'])
    op.create_index('ix_read_deals_period', 'read_deals', ['period_year', 'period_month'])
    op.create_index('ix_read_deals_period_full_name', 'read_deals', ['period_full_name'])
    op.create_index('ix_read_deals_status', 'read_deals', ['is_shipped', 'is_paid'])
    op.create_index('ix_read_deals_seller', 'read_deals', ['seller'])
    op.create_index('ix_read_deals_created_at', 'read_deals', ['created_at'])
    op.create_index('ix_read_deals_hash_key', 'read_deals', ['hash_key'])
    op.create_index('ix_read_deals_search', 'read_deals', ['client_name', 'invoice_info', 'seller'])

    # Create read_positions with FK cascade
    op.create_table(
        'read_positions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('deal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('deal_key', sa.String(length=255), nullable=False),
        sa.Column('position_number', sa.Integer(), nullable=False),
        sa.Column('hash_key', sa.String(length=32), nullable=False),
        sa.Column('product_name', sa.String(length=1000), nullable=False),
        sa.Column('supplier_name', sa.String(length=500), nullable=True),
        sa.Column('pickup_date', sa.String(length=50), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=15, scale=3), nullable=True),
        sa.Column('purchase_price_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('sale_price_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('revenue_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('margin_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('cost_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('client_name', sa.String(length=500), nullable=False),
        sa.Column('period_month', sa.String(length=20), nullable=False),
        sa.Column('period_year', sa.String(length=4), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['deal_id'], ['read_deals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Indexes for read_positions
    op.create_index('ix_read_positions_deal_id', 'read_positions', ['deal_id'])
    op.create_index('ix_read_positions_position_number', 'read_positions', ['position_number'])
    op.create_index('ix_read_positions_product_name', 'read_positions', ['product_name'])
    op.create_index('ix_read_positions_supplier', 'read_positions', ['supplier_name'])
    op.create_index('ix_read_positions_client', 'read_positions', ['client_name'])
    op.create_index('ix_read_positions_period', 'read_positions', ['period_year', 'period_month'])
    op.create_index('ix_read_positions_hash_key', 'read_positions', ['hash_key'])
    op.create_index('ix_read_positions_deal_product', 'read_positions', ['deal_id', 'product_name'])
    op.create_index('ix_read_positions_deal_position', 'read_positions', ['deal_id', 'position_number'])


def downgrade() -> None:
    """Revert to previous schema (drops and re-creates old tables)."""
    op.drop_table('read_positions', if_exists=True)
    op.drop_table('read_deals', if_exists=True)


# if __name__ == '__main__':
#     upgrade()

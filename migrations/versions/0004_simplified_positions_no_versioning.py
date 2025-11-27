"""Simplified positions: remove versioning, expand hash_key logic.

Revision ID: 0004
Revises: 0003
Create Date: 2025-01-21 00:00:00.000000

This migration implements the new architecture:
1. Remove version, is_active fields (no more soft deletes)
2. Use simple hash_key as unique identifier  
3. read_positions table holds current state only
4. Full history preserved in event_store

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Simplify positions table - remove versioning fields."""
    
    # Drop dependent table first due to FK
    op.drop_table('read_positions', if_exists=True)

    # Recreate read_positions with simplified structure
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
        # REMOVED: is_active, version - no more versioning!
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['deal_id'], ['read_deals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Simplified indexes for read_positions
    op.create_index('ix_read_positions_deal_id', 'read_positions', ['deal_id'])
    op.create_index('ix_read_positions_position_number', 'read_positions', ['position_number'])
    op.create_index('ix_read_positions_product_name', 'read_positions', ['product_name'])
    op.create_index('ix_read_positions_supplier', 'read_positions', ['supplier_name'])
    op.create_index('ix_read_positions_client', 'read_positions', ['client_name'])
    op.create_index('ix_read_positions_period', 'read_positions', ['period_year', 'period_month'])
    
    # NEW: Simple unique constraint on hash_key (no versioning complexity)
    op.create_index('ix_read_positions_hash_key', 'read_positions', ['hash_key'], unique=True)
    
    # Composite indexes for performance
    op.create_index('ix_read_positions_deal_product', 'read_positions', ['deal_id', 'product_name'])
    op.create_index('ix_read_positions_deal_position', 'read_positions', ['deal_id', 'position_number'])
    op.create_index('ix_read_positions_deal_hash', 'read_positions', ['deal_id', 'hash_key'])

    print("✅ Migration 0004 completed: Simplified positions without versioning")


def downgrade() -> None:
    """Revert to previous schema with versioning."""
    # Drop simplified table
    op.drop_table('read_positions', if_exists=True)
    
    # Recreate the versioned table (from migration 0003)
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
    
    print("❌ Migration 0004 reverted: Restored versioning")

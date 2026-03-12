"""Initial database schema creation for PostgreSQL.

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema for PostgreSQL."""

    # Create event_store table
    op.create_table('event_store',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('aggregate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('aggregate_type', sa.String(length=100), nullable=False),
        sa.Column('event_type', sa.String(length=200), nullable=False),
        sa.Column('event_version', sa.Integer(), nullable=False),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('event_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('sequence_number', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id')
    )

    # Create indexes for event_store
    op.create_index('ix_event_store_aggregate_id', 'event_store', ['aggregate_id'])
    op.create_index('ix_event_store_event_type', 'event_store', ['event_type'])
    op.create_index('ix_event_store_created_at', 'event_store', ['created_at'])
    op.create_index('ix_event_store_sequence', 'event_store', ['sequence_number'])
    op.create_index('ix_event_store_aggregate_sequence', 'event_store', ['aggregate_id', 'sequence_number'])
    op.create_index('ix_event_store_type_created', 'event_store', ['event_type', 'created_at'])

    # Create read_deals table
    op.create_table('read_deals',
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
        sa.Column('calc_revenue_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('calc_margin_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('calc_cost_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('revenue_mismatch', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('margin_mismatch', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('cost_mismatch', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('has_totals_error', sa.Boolean(), nullable=False),
        sa.Column('items_count', sa.Integer(), nullable=False),
        sa.Column('total_quantity', sa.Numeric(precision=15, scale=3), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('deal_key'),
        sa.UniqueConstraint('hash_key')
    )

    # Create indexes for read_deals
    op.create_index('ix_read_deals_client_name', 'read_deals', ['client_name'])
    op.create_index('ix_read_deals_period', 'read_deals', ['period_year', 'period_month'])
    op.create_index('ix_read_deals_status', 'read_deals', ['is_shipped', 'is_paid'])
    op.create_index('ix_read_deals_seller', 'read_deals', ['seller'])
    op.create_index('ix_read_deals_created_at', 'read_deals', ['created_at'])
    op.create_index('ix_read_deals_hash_key', 'read_deals', ['hash_key'])
    op.create_index('ix_read_deals_search', 'read_deals', ['client_name', 'invoice_info', 'seller'])

    # Create read_positions table
    op.create_table('read_positions',
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
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for read_positions
    op.create_index('ix_read_positions_deal_id', 'read_positions', ['deal_id'])
    op.create_index('ix_read_positions_position_number', 'read_positions', ['position_number'])
    op.create_index('ix_read_positions_product_name', 'read_positions', ['product_name'])
    op.create_index('ix_read_positions_supplier', 'read_positions', ['supplier_name'])
    op.create_index('ix_read_positions_client', 'read_positions', ['client_name'])
    op.create_index('ix_read_positions_period', 'read_positions', ['period_year', 'period_month'])
    op.create_index('ix_read_positions_hash_key', 'read_positions', ['hash_key'])
    op.create_index('ix_read_positions_deal_product', 'read_positions', ['deal_id', 'product_name'])
    op.create_index('ix_read_positions_deal_position', 'read_positions', ['deal_id', 'position_number'])
    op.create_index('ix_read_positions_deal_hash_key', 'read_positions', ['deal_id', 'hash_key'], unique=True)
    op.create_index('ix_read_positions_hash_active', 'read_positions', ['hash_key', 'is_active'], unique=True)
    op.create_index('ix_read_positions_hash_version', 'read_positions', ['hash_key', 'version'], unique=True)

    # Create read_audit table
    op.create_table('read_audit',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_key', sa.String(length=500), nullable=False),
        sa.Column('change_type', sa.String(length=20), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=True),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('sync_session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for read_audit
    op.create_index('ix_read_audit_entity', 'read_audit', ['entity_type', 'entity_id'])
    op.create_index('ix_read_audit_session', 'read_audit', ['sync_session_id'])
    op.create_index('ix_read_audit_changed_at', 'read_audit', ['changed_at'])
    op.create_index('ix_read_audit_change_type', 'read_audit', ['change_type'])

    # Create read_stats table
    op.create_table('read_stats',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('stat_type', sa.String(length=50), nullable=False),
        sa.Column('stat_date', sa.String(length=20), nullable=False),
        sa.Column('dimension_type', sa.String(length=50), nullable=True),
        sa.Column('dimension_value', sa.String(length=500), nullable=True),
        sa.Column('deals_count', sa.Integer(), nullable=False),
        sa.Column('positions_count', sa.Integer(), nullable=False),
        sa.Column('total_revenue', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('total_margin', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('total_cost', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('total_quantity', sa.Numeric(precision=15, scale=3), nullable=False),
        sa.Column('shipped_deals_count', sa.Integer(), nullable=False),
        sa.Column('paid_deals_count', sa.Integer(), nullable=False),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for read_stats
    op.create_index('ix_read_stats_type_date', 'read_stats', ['stat_type', 'stat_date'])
    op.create_index('ix_read_stats_dimension', 'read_stats', ['dimension_type', 'dimension_value'])
    op.create_index('ix_read_stats_calculated_at', 'read_stats', ['calculated_at'])
    op.create_index('ix_read_stats_unique', 'read_stats', ['stat_type', 'stat_date', 'dimension_type', 'dimension_value'], unique=True)

    # Create sync_sessions table
    op.create_table('sync_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sync_type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('file_path', sa.String(length=1000), nullable=False),
        sa.Column('file_hash', sa.String(length=32), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('stats_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for sync_sessions
    op.create_index('ix_sync_sessions_status', 'sync_sessions', ['status'])
    op.create_index('ix_sync_sessions_type', 'sync_sessions', ['sync_type'])
    op.create_index('ix_sync_sessions_started_at', 'sync_sessions', ['started_at'])
    op.create_index('ix_sync_sessions_file_hash', 'sync_sessions', ['file_hash'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('sync_sessions')
    op.drop_table('read_stats')
    op.drop_table('read_audit')
    op.drop_table('read_positions')
    op.drop_table('read_deals')
    op.drop_table('event_store')

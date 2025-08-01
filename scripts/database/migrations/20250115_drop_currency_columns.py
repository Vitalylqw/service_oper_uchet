"""
Migration: Drop currency columns from read models.

Removes all *_currency columns from read_deals and read_positions tables
since the system now only uses RUB currency.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250115_drop_currency_columns'
down_revision = '20250730_add_deal_status_enum'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop currency columns from read models."""
    
    # Drop currency columns from read_deals table
    op.drop_column('read_deals', 'total_revenue_currency')
    op.drop_column('read_deals', 'total_margin_currency')
    op.drop_column('read_deals', 'total_cost_currency')
    op.drop_column('read_deals', 'kickback_amount_currency')
    
    # Drop currency columns from read_positions table
    op.drop_column('read_positions', 'purchase_price_currency')
    op.drop_column('read_positions', 'sale_price_currency')
    op.drop_column('read_positions', 'revenue_currency')
    op.drop_column('read_positions', 'margin_currency')
    op.drop_column('read_positions', 'cost_currency')


def downgrade() -> None:
    """Re-add currency columns (for rollback)."""
    
    # Re-add currency columns to read_deals table
    op.add_column('read_deals', sa.Column('total_revenue_currency', sa.String(3), nullable=True, server_default='RUB'))
    op.add_column('read_deals', sa.Column('total_margin_currency', sa.String(3), nullable=True, server_default='RUB'))
    op.add_column('read_deals', sa.Column('total_cost_currency', sa.String(3), nullable=True, server_default='RUB'))
    op.add_column('read_deals', sa.Column('kickback_amount_currency', sa.String(3), nullable=True, server_default='RUB'))
    
    # Re-add currency columns to read_positions table
    op.add_column('read_positions', sa.Column('purchase_price_currency', sa.String(3), nullable=True, server_default='RUB'))
    op.add_column('read_positions', sa.Column('sale_price_currency', sa.String(3), nullable=True, server_default='RUB'))
    op.add_column('read_positions', sa.Column('revenue_currency', sa.String(3), nullable=True, server_default='RUB'))
    op.add_column('read_positions', sa.Column('margin_currency', sa.String(3), nullable=True, server_default='RUB'))
    op.add_column('read_positions', sa.Column('cost_currency', sa.String(3), nullable=True, server_default='RUB')) 
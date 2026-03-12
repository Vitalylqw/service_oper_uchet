"""Add hash_deal_key field to read_deals table

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add hash_deal_key field to read_deals table."""
    # Add hash_deal_key column
    op.add_column('read_deals', sa.Column('hash_deal_key', sa.String(32), nullable=True))

    # Create index for hash_deal_key
    op.create_index('ix_read_deals_hash_deal_key', 'read_deals', ['hash_deal_key'])

    # Update existing records with proper MD5 hash of deal_key
    # Note: We need to use a proper hash function, not just copy deal_key
    op.execute("""
        UPDATE read_deals
        SET hash_deal_key = md5(deal_key)
        WHERE hash_deal_key IS NULL
    """)

    # Make hash_deal_key NOT NULL after populating
    op.alter_column('read_deals', 'hash_deal_key', nullable=False)


def downgrade() -> None:
    """Remove hash_deal_key field from read_deals table."""
    # Drop index
    op.drop_index('ix_read_deals_hash_deal_key', 'read_deals')

    # Drop column
    op.drop_column('read_deals', 'hash_deal_key')

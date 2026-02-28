"""Add database snapshot tables for dashboard monitoring.

Revision ID: 0005
Revises: 0004
Create Date: 2026-02-28 00:00:00.000000

Three tables for storing DB state snapshots:
1. db_snapshots - header with aggregate totals + health checks (JSONB)
2. db_snapshot_deal_periods - deals breakdown by period_full_name
3. db_snapshot_position_periods - positions breakdown by period_month+period_year
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create snapshot tables for DB state monitoring."""

    # 1. Head table: db_snapshots
    op.create_table(
        "db_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("label", sa.String(200), nullable=True),
        sa.Column("source", sa.String(50), nullable=False, server_default="manual"),

        # --- read_deals aggregates ---
        sa.Column("deals_total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deals_unique_deal_key", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deals_unique_hash_key", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deals_unique_client", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deals_unique_period", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deals_sum_revenue", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("deals_sum_margin", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("deals_sum_cost", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("deals_sum_kickback", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column(
            "deals_sum_calc_revenue", sa.Numeric(18, 2), nullable=False, server_default="0"
        ),
        sa.Column(
            "deals_sum_calc_margin", sa.Numeric(18, 2), nullable=False, server_default="0"
        ),
        sa.Column(
            "deals_sum_calc_cost", sa.Numeric(18, 2), nullable=False, server_default="0"
        ),
        sa.Column("deals_sum_items_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "deals_sum_quantity", sa.Numeric(18, 3), nullable=False, server_default="0"
        ),
        sa.Column("deals_has_error_count", sa.Integer(), nullable=False, server_default="0"),

        # --- read_positions aggregates ---
        sa.Column("pos_total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pos_unique_deal_key", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pos_unique_hash_key", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pos_unique_client", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pos_unique_product", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pos_unique_supplier", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pos_unique_period", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pos_sum_quantity", sa.Numeric(18, 3), nullable=False, server_default="0"),
        sa.Column("pos_sum_revenue", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("pos_sum_margin", sa.Numeric(18, 5), nullable=False, server_default="0"),
        sa.Column("pos_sum_cost", sa.Numeric(18, 2), nullable=False, server_default="0"),

        # Health checks as JSONB (flexible structure)
        sa.Column(
            "health_checks",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_db_snapshots_label", "db_snapshots", ["label"])
    op.create_index("ix_db_snapshots_created_at", "db_snapshots", ["created_at"])

    # 2. Deal periods breakdown
    op.create_table(
        "db_snapshot_deal_periods",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column(
            "snapshot_id",
            sa.BigInteger(),
            sa.ForeignKey("db_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_full_name", sa.String(100), nullable=False),

        sa.Column("rows_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_deal_key", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_hash_key", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delta_dk_hk", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_client", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sum_revenue", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("sum_margin", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("sum_cost", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("sum_kickback", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("sum_calc_revenue", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("sum_calc_margin", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("sum_calc_cost", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("sum_items_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sum_quantity", sa.Numeric(18, 3), nullable=False, server_default="0"),
        sa.Column("has_error_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_snap_deal_periods_sid", "db_snapshot_deal_periods", ["snapshot_id"]
    )

    # 3. Position periods breakdown
    op.create_table(
        "db_snapshot_position_periods",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column(
            "snapshot_id",
            sa.BigInteger(),
            sa.ForeignKey("db_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_key", sa.String(50), nullable=False),

        sa.Column("rows_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_hash_key", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delta_rows_hk", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_deal_key", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_client", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_product", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_supplier", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sum_quantity", sa.Numeric(18, 3), nullable=False, server_default="0"),
        sa.Column("sum_revenue", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("sum_margin", sa.Numeric(18, 5), nullable=False, server_default="0"),
        sa.Column("sum_cost", sa.Numeric(18, 2), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_snap_pos_periods_sid", "db_snapshot_position_periods", ["snapshot_id"]
    )


def downgrade() -> None:
    """Drop snapshot tables."""
    op.drop_table("db_snapshot_position_periods")
    op.drop_table("db_snapshot_deal_periods")
    op.drop_table("db_snapshots")

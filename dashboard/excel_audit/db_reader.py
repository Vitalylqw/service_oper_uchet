"""Database reader for period-level deal aggregates.

Uses synchronous SQLAlchemy (psycopg2/sqlite) to query read_deals and
read_positions for a given period. Mirrors the pattern used in
dashboard/db_snapshot_service.py.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from loguru import logger
from sqlalchemy import text
from sqlalchemy.engine import Connection

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC = str(_PROJECT_ROOT / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


@dataclass
class DbDealRow:
    """Single deal row as read from read_deals for a period."""

    deal_key: str
    source_row_number: int | None
    total_revenue: Decimal | None
    total_margin: Decimal | None
    total_cost: Decimal | None


@dataclass
class DbPeriodData:
    """Aggregated and deal-level data for one period from the database."""

    period_name: str
    revenue_sum: Decimal
    margin_sum: Decimal
    cost_sum: Decimal
    deal_count: int
    position_count: int
    deals: list[DbDealRow] = field(default_factory=list)


def _to_decimal(value: object) -> Decimal | None:
    """Safely convert a DB value to Decimal."""
    if value is None:
        return None
    return Decimal(str(value))


def get_db_period_data(
    conn: Connection,
    period_month: str,
    period_year: str,
    period_name: str,
) -> DbPeriodData:
    """Fetch aggregated and deal-level data for a period from read_deals / read_positions.

    Compares against total_revenue_amount (declared master-row value), not
    the calculated calc_revenue_amount.

    Args:
        conn: Open synchronous SQLAlchemy connection.
        period_month: Normalised month name (e.g. "Январь").
        period_year: Four-digit year string (e.g. "2025").
        period_name: Human-readable label used in result (e.g. "Январь 2025").

    Returns:
        DbPeriodData: Aggregates and per-deal rows for the period.
    """
    params = {"month": period_month, "year": period_year}

    # --- Aggregate totals from read_deals ---
    agg_row = conn.execute(
        text("""
            SELECT
                COALESCE(SUM(total_revenue_amount), 0) AS revenue,
                COALESCE(SUM(total_margin_amount),  0) AS margin,
                COALESCE(SUM(total_cost_amount),    0) AS cost,
                COUNT(*)                                AS deal_count
            FROM read_deals
            WHERE period_month = :month AND period_year = :year
        """),
        params,
    ).fetchone()

    # --- Position count ---
    pos_row = conn.execute(
        text("""
            SELECT COUNT(*) AS pos_count
            FROM read_positions rp
            JOIN read_deals rd ON rp.deal_id = rd.id
            WHERE rd.period_month = :month AND rd.period_year = :year
        """),
        params,
    ).fetchone()

    # --- Per-deal rows ---
    deal_rows = conn.execute(
        text("""
            SELECT
                deal_key,
                source_row_number,
                total_revenue_amount,
                total_margin_amount,
                total_cost_amount
            FROM read_deals
            WHERE period_month = :month AND period_year = :year
            ORDER BY source_row_number NULLS LAST, deal_key
        """),
        params,
    ).fetchall()

    deals = [
        DbDealRow(
            deal_key=row.deal_key,
            source_row_number=row.source_row_number,
            total_revenue=_to_decimal(row.total_revenue_amount),
            total_margin=_to_decimal(row.total_margin_amount),
            total_cost=_to_decimal(row.total_cost_amount),
        )
        for row in deal_rows
    ]

    data = DbPeriodData(
        period_name=period_name,
        revenue_sum=_to_decimal(agg_row.revenue) or Decimal("0"),
        margin_sum=_to_decimal(agg_row.margin) or Decimal("0"),
        cost_sum=_to_decimal(agg_row.cost) or Decimal("0"),
        deal_count=int(agg_row.deal_count),
        position_count=int(pos_row.pos_count),
        deals=deals,
    )

    logger.info(
        "DB period '{}': deals={} positions={} revenue={} margin={} cost={}",
        period_name,
        data.deal_count,
        data.position_count,
        data.revenue_sum,
        data.margin_sum,
        data.cost_sum,
    )
    return data

"""Comparator: Excel deals vs database records for a period.

Produces PeriodComparison containing:
- aggregate deltas (Excel SUM vs DB SUM)
- deals only in Excel (not yet synced or sync error)
- deals only in DB (removed from source file)
- deals in both with value differences above THRESHOLD
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from loguru import logger

from .config import AuditConfig
from .db_reader import DbPeriodData

_DEFAULT_THRESHOLD = AuditConfig().threshold


def _source_sort_key(source_row_number: int | None, deal_key: str) -> tuple[int, str]:
    """Sort rows by Excel row first, keeping missing rows at the end."""
    return (source_row_number if source_row_number is not None else 10**12, deal_key)


@dataclass
class PeriodAggregates:
    """Sum of declared totals for one side (Excel or DB) of a period."""

    revenue: Decimal
    margin: Decimal
    cost: Decimal
    deal_count: int
    position_count: int


@dataclass
class OnlySideDeal:
    """Deal that exists on only one side (Excel-only or DB-only)."""

    deal_key: str
    period_name: str
    source_row_number: int | None
    revenue: Decimal | None
    margin: Decimal | None
    cost: Decimal | None


@dataclass
class DealDiff:
    """Deal present on both sides but with value differences above THRESHOLD."""

    deal_key: str
    period_name: str
    source_row_number_excel: int | None
    source_row_number_db: int | None
    revenue_excel: Decimal | None
    revenue_db: Decimal | None
    margin_excel: Decimal | None
    margin_db: Decimal | None
    cost_excel: Decimal | None
    cost_db: Decimal | None


@dataclass
class PeriodComparison:
    """Full comparison result for one period."""

    period_name: str
    excel_agg: PeriodAggregates
    db_agg: PeriodAggregates
    only_in_excel: list[OnlySideDeal] = field(default_factory=list)
    only_in_db: list[OnlySideDeal] = field(default_factory=list)
    diffs: list[DealDiff] = field(default_factory=list)


def _excel_aggregates(deals: list[Any]) -> PeriodAggregates:
    """Calculate aggregate totals from Excel Deal objects.

    Uses declared master-row totals (total_revenue / total_margin / total_cost)
    which contain formula-computed values from the Excel file.
    """
    revenue = sum((d.total_revenue.amount for d in deals if d.total_revenue), Decimal("0"))
    margin = sum((d.total_margin.amount for d in deals if d.total_margin), Decimal("0"))
    cost = sum((d.total_cost.amount for d in deals if d.total_cost), Decimal("0"))
    positions = sum(len(d.items) for d in deals)
    return PeriodAggregates(
        revenue=revenue,
        margin=margin,
        cost=cost,
        deal_count=len(deals),
        position_count=positions,
    )


def _has_diff(
    a: Decimal | None,
    b: Decimal | None,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> bool:
    """Return True when both values are present and differ by more than threshold."""
    if a is None or b is None:
        return a != b  # one side missing -> always a diff
    return abs(a - b) > threshold


def compare_period(
    excel_deals: list[Any],
    db_data: DbPeriodData,
    period_name: str,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> PeriodComparison:
    """Join Excel deals and DB records by deal_key and classify differences.

    Args:
        excel_deals: Deal objects parsed from the Excel sheet.
        db_data: Aggregated and per-deal data from the database.
        period_name: Human-readable period label.
        threshold: Minimum absolute delta to treat as a real discrepancy.

    Returns:
        PeriodComparison: Full comparison result.
    """
    excel_by_key: dict[str, Any] = {d.deal_key: d for d in excel_deals}
    db_by_key = {r.deal_key: r for r in db_data.deals}

    excel_keys = set(excel_by_key)
    db_keys = set(db_by_key)

    # --- Deals present only in Excel ---
    only_in_excel: list[OnlySideDeal] = [
        OnlySideDeal(
            deal_key=k,
            period_name=period_name,
            source_row_number=excel_by_key[k].source_row_number,
            revenue=excel_by_key[k].total_revenue.amount if excel_by_key[k].total_revenue else None,
            margin=excel_by_key[k].total_margin.amount if excel_by_key[k].total_margin else None,
            cost=excel_by_key[k].total_cost.amount if excel_by_key[k].total_cost else None,
        )
        for k in sorted(
            excel_keys - db_keys,
            key=lambda key: _source_sort_key(excel_by_key[key].source_row_number, key),
        )
    ]

    # --- Deals present only in DB ---
    only_in_db: list[OnlySideDeal] = [
        OnlySideDeal(
            deal_key=k,
            period_name=period_name,
            source_row_number=db_by_key[k].source_row_number,
            revenue=db_by_key[k].total_revenue,
            margin=db_by_key[k].total_margin,
            cost=db_by_key[k].total_cost,
        )
        for k in sorted(
            db_keys - excel_keys,
            key=lambda key: _source_sort_key(db_by_key[key].source_row_number, key),
        )
    ]

    # --- Deals in both with value differences ---
    # Compare Excel declared totals (total_revenue) vs DB total_revenue_amount.
    diffs: list[DealDiff] = []
    for key in sorted(
        excel_keys & db_keys,
        key=lambda item: _source_sort_key(excel_by_key[item].source_row_number, item),
    ):
        xl = excel_by_key[key]
        db = db_by_key[key]

        xl_rev = xl.total_revenue.amount if xl.total_revenue else None
        xl_mar = xl.total_margin.amount if xl.total_margin else None
        xl_cost = xl.total_cost.amount if xl.total_cost else None

        if (
            _has_diff(xl_rev, db.total_revenue, threshold)
            or _has_diff(xl_mar, db.total_margin, threshold)
            or _has_diff(xl_cost, db.total_cost, threshold)
        ):
            diffs.append(
                DealDiff(
                    deal_key=key,
                    period_name=period_name,
                    source_row_number_excel=xl.source_row_number,
                    source_row_number_db=db.source_row_number,
                    revenue_excel=xl_rev,
                    revenue_db=db.total_revenue,
                    margin_excel=xl_mar,
                    margin_db=db.total_margin,
                    cost_excel=xl_cost,
                    cost_db=db.total_cost,
                )
            )

    db_agg = PeriodAggregates(
        revenue=db_data.revenue_sum,
        margin=db_data.margin_sum,
        cost=db_data.cost_sum,
        deal_count=db_data.deal_count,
        position_count=db_data.position_count,
    )

    result = PeriodComparison(
        period_name=period_name,
        excel_agg=_excel_aggregates(excel_deals),
        db_agg=db_agg,
        only_in_excel=only_in_excel,
        only_in_db=only_in_db,
        diffs=diffs,
    )

    logger.info(
        "Period '{}': only_excel={} only_db={} diffs={}",
        period_name,
        len(only_in_excel),
        len(only_in_db),
        len(diffs),
    )
    return result

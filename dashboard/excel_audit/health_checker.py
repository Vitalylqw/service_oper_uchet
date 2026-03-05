"""Health checker for Excel data integrity.

Performs two checks per period:
1. Duplicate deal_keys within the same sheet.
2. Mismatch between master-row totals (deal.total_revenue / total_margin / total_cost)
   and the sum of item rows (deal.calc_* computed fields).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from loguru import logger

from .config import AuditConfig

_DEFAULT_THRESHOLD = AuditConfig().threshold


@dataclass
class DuplicateIssue:
    """Represents a deal_key that appears more than once in a period."""

    deal_key: str
    period_name: str
    count: int  # number of occurrences


@dataclass
class TotalsIssue:
    """Represents a mismatch between master-row total and sum of item rows."""

    deal_key: str
    period_name: str
    field: str          # "revenue" | "margin" | "cost"
    master_value: Decimal   # value declared in the master row (formula result)
    calc_value: Decimal     # sum calculated from item rows
    delta: Decimal          # abs(master - calc)
    level: str              # "WARN" (delta <= threshold) | "FAIL" (delta > threshold)


@dataclass
class PeriodHealthReport:
    """Aggregated health-check result for one period."""

    period_name: str
    total_deals: int
    total_positions: int
    duplicates: list[DuplicateIssue] = field(default_factory=list)
    totals_issues: list[TotalsIssue] = field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        """Return True when no duplicates and no FAIL-level totals issues."""
        has_fails = any(i.level == "FAIL" for i in self.totals_issues)
        return not self.duplicates and not has_fails

    @property
    def fail_count(self) -> int:
        """Number of FAIL-level totals issues."""
        return sum(1 for i in self.totals_issues if i.level == "FAIL")

    @property
    def warn_count(self) -> int:
        """Number of WARN-level totals issues."""
        return sum(1 for i in self.totals_issues if i.level == "WARN")


def find_duplicate_keys(deals: list[Any], period_name: str) -> list[DuplicateIssue]:
    """Find deal_keys that appear more than once in the list.

    Args:
        deals: List of Deal domain objects for one period.
        period_name: Human-readable period label for reporting.

    Returns:
        list[DuplicateIssue]: One entry per duplicated deal_key.
    """
    counts = Counter(d.deal_key for d in deals)
    issues = [
        DuplicateIssue(deal_key=key, period_name=period_name, count=cnt)
        for key, cnt in counts.items()
        if cnt > 1
    ]
    if issues:
        logger.warning(
            "Period '{}': {} duplicate deal_key(s) found", period_name, len(issues)
        )
    return issues


def check_totals_consistency(
    deals: list[Any],
    period_name: str,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> list[TotalsIssue]:
    """Check that master-row totals match the sum of item rows.

    Compares deal.total_revenue / total_margin / total_cost against the
    Deal.calc_* computed fields (sum across items). Only fields that have a
    declared master value are checked; None values are skipped.

    Args:
        deals: List of Deal domain objects for one period.
        period_name: Human-readable period label for reporting.
        threshold: Minimum absolute delta to classify as FAIL.

    Returns:
        list[TotalsIssue]: One entry per (deal, field) pair with a non-zero delta.
    """
    issues: list[TotalsIssue] = []

    for deal in deals:
        checks = [
            ("revenue", deal.total_revenue, deal.calc_revenue_amount),
            ("margin", deal.total_margin, deal.calc_margin_amount),
            ("cost", deal.total_cost, deal.calc_cost_amount),
        ]
        for field_name, master, calc in checks:
            if master is None:
                continue
            delta = abs(master.amount - calc.amount)
            if delta == Decimal("0"):
                continue
            level = "FAIL" if delta > threshold else "WARN"
            issues.append(
                TotalsIssue(
                    deal_key=deal.deal_key,
                    period_name=period_name,
                    field=field_name,
                    master_value=master.amount,
                    calc_value=calc.amount,
                    delta=delta,
                    level=level,
                )
            )

    fails = sum(1 for i in issues if i.level == "FAIL")
    warns = sum(1 for i in issues if i.level == "WARN")
    if issues:
        logger.warning(
            "Period '{}': totals consistency — {} FAIL, {} WARN",
            period_name,
            fails,
            warns,
        )
    return issues


def run_health_check(
    deals: list[Any],
    period_name: str,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> PeriodHealthReport:
    """Run all health checks for a period and return aggregated report.

    Args:
        deals: List of Deal domain objects for one period.
        period_name: Human-readable period label for reporting.
        threshold: Minimum absolute delta to classify as FAIL.

    Returns:
        PeriodHealthReport: Full health check result.
    """
    total_positions = sum(len(d.items) for d in deals)
    report = PeriodHealthReport(
        period_name=period_name,
        total_deals=len(deals),
        total_positions=total_positions,
        duplicates=find_duplicate_keys(deals, period_name),
        totals_issues=check_totals_consistency(deals, period_name, threshold),
    )
    logger.info(
        "Period '{}': health={} deals={} positions={} dups={} totals_issues={}",
        period_name,
        "OK" if report.is_healthy else "ISSUES",
        report.total_deals,
        report.total_positions,
        len(report.duplicates),
        len(report.totals_issues),
    )
    return report

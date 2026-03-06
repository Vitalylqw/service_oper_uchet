"""Chronological period sorting utilities.

Provides helpers to sort period strings like 'Январь 2025' or 'Июнь.2025'
by actual date order instead of lexicographic (alphabetical) order.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from typing import Any

MONTH_TO_NUM: dict[str, int] = {
    "Январь": 1,
    "Февраль": 2,
    "Март": 3,
    "Апрель": 4,
    "Май": 5,
    "Июнь": 6,
    "Июль": 7,
    "Август": 8,
    "Сентябрь": 9,
    "Октябрь": 10,
    "Ноябрь": 11,
    "Декабрь": 12,
}


def period_sort_key(period_str: str) -> tuple[int, int]:
    """Parse period string into a sortable (year, month_num) tuple.

    Handles formats: 'Январь 2025', 'Июнь.2025', 'Март  2024'.

    Args:
        period_str: Period string in 'Month YYYY' or 'Month.YYYY' format.

    Returns:
        Tuple of (year, month_number) for use as a sort key.
        Returns (0, 0) if parsing fails to keep unparseable entries at the end.
    """
    try:
        normalized = re.sub(r"[.\s]+", " ", period_str.strip())
        month_name, year_str = normalized.rsplit(" ", 1)
        return (int(year_str), MONTH_TO_NUM.get(month_name, 0))
    except (ValueError, AttributeError):
        return (0, 0)


def sort_periods(
    periods: Iterable[str],
    *,
    reverse: bool = True,
) -> list[str]:
    """Sort period strings in chronological order.

    Args:
        periods: Iterable of period strings ('Месяц YYYY').
        reverse: True for DESC (newest first), False for ASC. Default: True.

    Returns:
        Sorted list of period strings.
    """
    return sorted(periods, key=period_sort_key, reverse=reverse)


def sort_period_items(
    items: Iterable[tuple[str, Any]],
    *,
    key_func: Callable[[tuple[str, Any]], str] = lambda x: x[0],
    reverse: bool = True,
) -> list[tuple[str, Any]]:
    """Sort dict items / tuples by period key in chronological order.

    Args:
        items: Iterable of (period_string, value) tuples.
        key_func: Function to extract period string from each item.
        reverse: True for DESC (newest first), False for ASC. Default: True.

    Returns:
        Sorted list of tuples.
    """
    return sorted(
        items,
        key=lambda x: period_sort_key(key_func(x)),
        reverse=reverse,
    )


def sort_period_dicts(
    rows: Sequence[dict[str, Any]],
    period_field: str,
    *,
    reverse: bool = True,
) -> list[dict[str, Any]]:
    """Sort a list of dicts by a period-valued field in chronological order.

    Args:
        rows: List of dicts containing period data.
        period_field: Key name holding the period string.
        reverse: True for DESC (newest first), False for ASC. Default: True.

    Returns:
        Sorted list of dicts.
    """
    return sorted(
        rows,
        key=lambda r: period_sort_key(str(r.get(period_field, ""))),
        reverse=reverse,
    )

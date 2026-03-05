"""Configuration for Excel audit dashboard.

Centralises tuneable parameters so they can be adjusted
without touching comparison / health-check / rendering logic.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class AuditConfig(BaseModel):
    """Excel audit dashboard settings."""

    threshold: Decimal = Field(
        default=Decimal("0.1"),
        description=(
            "Minimum absolute delta (rubles) to treat as a real discrepancy. "
            "Differences at or below this value are classified as WARN; "
            "differences above it are classified as FAIL."
        ),
    )
    show_warnings: bool = Field(
        default=False,
        description=(
            "Whether to display WARN-level totals issues in the HTML report. "
            "When False, only FAIL-level issues are shown."
        ),
    )

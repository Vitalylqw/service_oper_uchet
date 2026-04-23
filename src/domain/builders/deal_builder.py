"""
DealBuilder: deferred construction of Deal aggregate.

Provides an explicit builder to accumulate fields and build a valid Deal only
when all required data is available. This keeps parsing logic simple while
ensuring domain invariants at creation time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from ..models.deal import Deal
from ..value_objects.common import Money, Period, SignedMoney, Status


@dataclass
class DealBuilder:
    """Builder for Deal aggregate.

    Usage:
        builder = DealBuilder(period=period)
        builder.client_name = "..."
        builder.invoice_info = "..."
        builder.invoice_number = "..."
        builder.invoice_date = "..."
        builder.seller = "..."
        ... set optional totals/status ...
        deal = builder.build()
    """

    period: Period

    # Required at build time
    client_name: Optional[str] = None
    invoice_info: Optional[str] = None
    seller: Optional[str] = None
    explicit_deal_key: Optional[str] = None

    # Optional/basic
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    upd_number: Optional[str] = None
    is_shipped: Optional[Status] = None
    is_paid: Optional[Status] = None

    # Optional totals
    total_revenue: Optional[Money] = None
    total_margin: Optional[SignedMoney] = None
    total_cost: Optional[Money] = None
    kickback_amount: Optional[Money] = None

    def is_ready(self) -> bool:
        """Return True if enough data is provided to build a Deal.

        Required: client_name, invoice_info, seller, period.
        """
        return (
            bool(self.client_name and self.client_name.strip())
            and bool(self.invoice_info and self.invoice_info.strip())
            and bool(self.seller and self.seller.strip())
            and self.period is not None
        )

    def build(self) -> Deal:
        """Construct a Deal with all collected fields.

        Raises:
            ValueError: If required fields are missing.
        """
        if not self.is_ready():
            missing = []
            if not (self.client_name and self.client_name.strip()):
                missing.append("client_name")
            if not (self.invoice_info and self.invoice_info.strip()):
                missing.append("invoice_info")
            if not (self.seller and self.seller.strip()):
                missing.append("seller")
            if self.period is None:
                missing.append("period")
            raise ValueError(
                f"DealBuilder is not ready, missing: {', '.join(missing)}"
            )

        # Compose Deal. period_month/year are mandatory in the model; pass from Period.
        deal = Deal(
            client_name=self.client_name,  # type: ignore[arg-type]
            invoice_info=self.invoice_info,  # type: ignore[arg-type]
            invoice_number=self.invoice_number,
            invoice_date=self.invoice_date,
            upd_number=self.upd_number,
            is_shipped=self.is_shipped,
            is_paid=self.is_paid,
            total_revenue=self.total_revenue,
            total_margin=self.total_margin,
            total_cost=self.total_cost,
            kickback_amount=self.kickback_amount,
            period=self.period,
            period_month=self.period.month,
            period_year=self.period.year,
            seller=self.seller,  # type: ignore[arg-type]
            explicit_deal_key=self.explicit_deal_key,
        )
        return deal


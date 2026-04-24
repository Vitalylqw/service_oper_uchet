"""Infrastructure mappers for converting data sources to DealItem."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from loguru import logger

from domain.models import Deal, DealItem
from domain.value_objects import Money, Money5, SignedMoney, SignedMoney5
from infrastructure.database.models import ReadModelPosition

MISMATCH_FIELDS = ("client_name", "period_year", "period_month")


def from_read_position(position: ReadModelPosition, deal: Deal) -> DealItem:
    """Create DealItem from read-model position with deal context."""
    mismatches: dict[str, tuple[str | None, str | None]] = {}
    for field in MISMATCH_FIELDS:
        read_value = getattr(position, field)
        deal_value = getattr(deal, field)
        if read_value != deal_value:
            mismatches[field] = (read_value, deal_value)

    if mismatches:
        _log_context_mismatch(deal.deal_key, mismatches)

    try:
        item = DealItem(
            product_name=position.product_name,
            supplier_name=position.supplier_name,
            pickup_date=position.pickup_date,
            quantity=position.quantity,
            purchase_price=_money5_from_amount(position.purchase_price_amount),
            sale_price=_money_from_amount(position.sale_price_amount),
            revenue=_money_from_amount(position.revenue_amount),
            margin=_signed_money5_from_amount(position.margin_amount),
            cost=_money_from_amount(position.cost_amount),
            position_number=position.position_number,
            client_name=deal.client_name,
            period_month=deal.period_month,
            period_year=deal.period_year,
            seller=deal.seller,
            invoice_info=deal.invoice_info,
            source_row_number=position.source_row_number,
        )
    except Exception as e:
        logger.error(
            "Failed to create DealItem from position %s: %s. "
            "purchase_price_amount=%s, margin_amount=%s",
            position.id,
            str(e),
            position.purchase_price_amount,
            position.margin_amount,
        )
        raise

    if position.id:
        item.set_id(UUID(str(position.id)))

    item.deal_id = deal.id
    item.deal_key = deal.deal_key

    return item


def from_event(item_data: dict[str, Any], deal: Deal) -> DealItem:
    """Create DealItem from event payload using parent deal context."""
    item = DealItem(
        product_name=item_data["product_name"],
        supplier_name=item_data.get("supplier_name"),
        pickup_date=item_data.get("pickup_date"),
        quantity=_decimal_or_none(item_data.get("quantity")),
        purchase_price=_money5_from_amount(_read_price(item_data, "purchase")),
        sale_price=_money_from_amount(_read_price(item_data, "sale")),
        revenue=_money_from_amount(_read_price(item_data, "revenue")),
        margin=_signed_money5_from_amount(_read_price(item_data, "margin")),
        cost=_money_from_amount(_read_price(item_data, "cost")),
        position_number=int(item_data.get("position_number", 1)),
        client_name=deal.client_name,
        period_month=deal.period_month,
        period_year=deal.period_year,
        seller=deal.seller,
        invoice_info=deal.invoice_info,
        source_row_number=item_data.get("source_row_number"),
    )

    explicit_id = item_data.get("item_id")
    if explicit_id:
        try:
            item.set_id(UUID(str(explicit_id)))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to set explicit DealItem id from event; deal_key={deal_key} error={error}",
                deal_key=deal.deal_key,
                error=str(exc),
            )

    item.deal_id = deal.id
    item.deal_key = deal.deal_key

    return item


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to convert quantity to Decimal: value={value} error={error}",
            value=value,
            error=str(exc),
        )
        return None


def _read_price(item_data: dict[str, Any], key: str) -> Any:
    prices = item_data.get("prices", {})
    price = prices.get(key)
    if price is not None:
        return price
    flat_key = f"{key}_price"
    return item_data.get(flat_key)


def _money_from_amount(amount: Any) -> Money | None:
    if amount in (None, ""):
        return None
    if isinstance(amount, Money):
        return amount
    try:
        return Money(amount=Decimal(str(amount)))
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to convert value to Money: value={value} error={error}",
            value=amount,
            error=str(exc),
        )
        return None


def _money5_from_amount(amount: Any) -> Money5 | None:
    if amount in (None, ""):
        return None
    if isinstance(amount, Money5):
        return amount
    if isinstance(amount, Money):
        return Money5(amount=amount.amount)
    try:
        return Money5(amount=Decimal(str(amount)))
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to convert value to Money5: value={value} error={error}",
            value=amount,
            error=str(exc),
        )
        return None


def _signed_money_from_amount(amount: Any) -> SignedMoney | None:
    if amount in (None, ""):
        return None
    if isinstance(amount, SignedMoney):
        return amount
    try:
        return SignedMoney(amount=Decimal(str(amount)))
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to convert value to SignedMoney: value={value} error={error}",
            value=amount,
            error=str(exc),
        )
        return None


def _signed_money5_from_amount(amount: Any) -> SignedMoney5 | None:
    if amount in (None, ""):
        return None
    if isinstance(amount, SignedMoney5):
        return amount
    if isinstance(amount, SignedMoney):
        return SignedMoney5(amount=amount.amount)
    try:
        return SignedMoney5(amount=Decimal(str(amount)))
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to convert value to SignedMoney5: value={value} error={error}",
            value=amount,
            error=str(exc),
        )
        return None


def _log_context_mismatch(deal_key: str, mismatches: dict[str, tuple[str | None, str | None]]) -> None:
    mismatch_details = "; ".join(
        f"{field}: read='{read_val}' deal='{deal_val}'"
        for field, (read_val, deal_val) in mismatches.items()
    )
    logger.warning(
        "DealItem context mismatch for deal {deal_key}: {details}",
        deal_key=deal_key,
        details=mismatch_details,
    )

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from domain.models import Deal
from domain.value_objects import Period
from infrastructure.database.models import ReadModelDeal, ReadModelPosition
from infrastructure.database.repositories import DealRepositoryImplementation


class FakeScalars:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def all(self) -> list[Any]:
        return self._items


class FakeResult:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def scalars(self) -> FakeScalars:
        return FakeScalars(self._items)


class FakeSession:
    def __init__(self, positions: list[ReadModelPosition]) -> None:
        self.positions = positions

    async def execute(self, query: Any) -> FakeResult:  # pragma: no cover - simple stub
        return FakeResult(self.positions)


@pytest.mark.asyncio
async def test_load_deal_items_uses_mapper() -> None:
    deal = Deal(
        deal_key="DEAL-1",
        client_name="ООО Тест",
        invoice_info="Счет 001",
        period=Period(month="Январь", year="2025", full_name="Январь 2025"),
        period_month="Январь",
        period_year="2025",
        seller="Продавец",
    )
    deal.set_id(uuid4())

    position = ReadModelPosition(
        id=uuid4(),
        deal_id=deal.id,
        deal_key=deal.deal_key,
        position_number=1,
        hash_key="hash",
        product_name="Товар",
        supplier_name="Поставщик",
        pickup_date="2025-01-10",
        quantity=Decimal("2"),
        purchase_price_amount=Decimal("150.00"),
        sale_price_amount=Decimal("200.00"),
        revenue_amount=Decimal("400.00"),
        margin_amount=Decimal("100.00"),
        cost_amount=Decimal("300.00"),
        client_name=deal.client_name,
        period_month=deal.period_month,
        period_year=deal.period_year,
    )

    repository = DealRepositoryImplementation(session=FakeSession([position]))

    await repository._load_deal_items(deal)

    assert len(deal.items) == 1
    item = deal.items[0]
    assert item.product_name == "Товар"
    assert item.deal_id == deal.id
    assert item.client_name == deal.client_name
    assert item.position_number == 1


@pytest.mark.asyncio
async def test_read_model_to_domain_preserves_zero_totals() -> None:
    """Read-model reconstruction must not convert numeric zeros to None."""
    period = Period(month="Январь", year="2025", full_name="Январь 2025")
    deal_id = uuid4()
    deal_model = ReadModelDeal(
        id=deal_id,
        deal_key="001|01.01.2025|продавец|январь 2025",
        hash_key="hash",
        client_name="ООО Тест",
        invoice_info="001 от 01.01.2025",
        invoice_number="001",
        invoice_date="01.01.2025",
        period_month=period.month,
        period_year=period.year,
        period_full_name=period.full_name,
        is_shipped=None,
        is_paid=None,
        upd_number=None,
        seller="Продавец",
        total_revenue_amount=Decimal("0.00"),
        total_margin_amount=Decimal("0.00"),
        total_cost_amount=Decimal("0.00"),
        kickback_amount_value=Decimal("0.00"),
    )

    repository = DealRepositoryImplementation(session=FakeSession([]))

    deal = await repository._read_model_to_domain(deal_model)

    assert deal.total_revenue is not None
    assert deal.total_revenue.amount == Decimal("0.00")
    assert deal.total_margin is not None
    assert deal.total_margin.amount == Decimal("0.00")
    assert deal.total_cost is not None
    assert deal.total_cost.amount == Decimal("0.00")
    assert deal.kickback_amount is not None
    assert deal.kickback_amount.amount == Decimal("0.00")

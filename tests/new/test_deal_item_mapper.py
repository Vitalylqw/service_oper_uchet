from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from domain.models import Deal
from domain.value_objects import Money, Period, SignedMoney
from infrastructure.database.models import ReadModelPosition
from infrastructure.mappers import deal_item_mapper


@pytest.fixture
def sample_deal() -> Deal:
    period = Period(month="Январь", year="2025", full_name="Январь 2025")
    deal = Deal(
        deal_key="DEAL-1",
        client_name="ООО Тест",
        invoice_info="Счет 001",
        period=period,
        period_month=period.month,
        period_year=period.year,
        seller="Продавец",
    )
    deal.set_id(uuid4())
    return deal


def test_from_read_position_basic(sample_deal: Deal) -> None:
    position = ReadModelPosition(
        id=uuid4(),
        deal_id=sample_deal.id,
        deal_key=sample_deal.deal_key,
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
        client_name=sample_deal.client_name,
        period_month=sample_deal.period_month,
        period_year=sample_deal.period_year,
    )

    item = deal_item_mapper.from_read_position(position, sample_deal)

    assert item.product_name == "Товар"
    assert item.supplier_name == "Поставщик"
    assert item.client_name == sample_deal.client_name
    assert item.position_number == 1
    assert item.deal_id == sample_deal.id
    assert item.purchase_price == Money(amount=Decimal("150.00"))
    assert item.margin == SignedMoney(amount=Decimal("100.00"))


def test_from_read_position_logs_mismatch(sample_deal: Deal, monkeypatch: pytest.MonkeyPatch) -> None:
    warnings: list[dict[str, str]] = []

    def fake_log(deal_key: str, mismatches: dict[str, tuple[str | None, str | None]]) -> None:
        warnings.append({
            "deal_key": deal_key,
            "details": "; ".join(
                f"{field}: read='{read_val}' deal='{deal_val}'"
                for field, (read_val, deal_val) in mismatches.items()
            ),
        })

    monkeypatch.setattr(deal_item_mapper, "_log_context_mismatch", fake_log)

    position = ReadModelPosition(
        id=uuid4(),
        deal_id=sample_deal.id,
        deal_key=sample_deal.deal_key,
        position_number=1,
        hash_key="hash",
        product_name="Товар",
        supplier_name="Поставщик",
        pickup_date=None,
        quantity=None,
        purchase_price_amount=None,
        sale_price_amount=None,
        revenue_amount=None,
        margin_amount=None,
        cost_amount=None,
        client_name="Другой",
        period_month="Февраль",
        period_year="2024",
    )

    deal_item_mapper.from_read_position(position, sample_deal)

    assert warnings
    assert warnings[0]["deal_key"] == sample_deal.deal_key


def test_from_event(sample_deal: Deal) -> None:
    item_data = {
        "product_name": "Товар",
        "supplier_name": "Поставщик",
        "pickup_date": "2025-01-11",
        "quantity": "5",
        "position_number": 2,
        "item_id": str(uuid4()),
        "prices": {
            "purchase": "100.00",
            "sale": "150.00",
            "revenue": "750.00",
            "margin": "250.00",
            "cost": "500.00",
        },
    }

    item = deal_item_mapper.from_event(item_data, sample_deal)

    assert item.position_number == 2
    assert item.sale_price == Money(amount=Decimal("150.00"))
    assert item.margin == SignedMoney(amount=Decimal("250.00"))
    assert item.client_name == sample_deal.client_name
    assert item.deal_id == sample_deal.id

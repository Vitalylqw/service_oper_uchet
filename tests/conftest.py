"""
Pytest configuration and common fixtures.
"""

from decimal import Decimal

import pytest

from src.domain.models import Deal, DealItem, SyncSession
from src.domain.models.sync_session import SyncType
from src.domain.value_objects import Money, Period, Status


@pytest.fixture
def sample_period() -> Period:
    """Sample period for tests."""
    return Period(
        month="Май",
        year="2025",
        full_name="Май 2025"
    )


@pytest.fixture
def sample_money() -> Money:
    """Sample money for tests."""
    return Money(amount=Decimal("1000.50"), currency="RUB")


@pytest.fixture
def sample_deal_item() -> DealItem:
    """Sample deal item for tests."""
    return DealItem(
        product_name="Тестовый товар",
        supplier_name="Тестовый поставщик",
        quantity=Decimal("10.5"),
        purchase_price=Money(amount=Decimal("100.00")),
        sale_price=Money(amount=Decimal("150.00")),
        pickup_date="15"
    )


@pytest.fixture
def sample_deal(sample_period: Period) -> Deal:
    """Sample deal for tests."""
    return Deal(
        client_name="Тестовый клиент",
        invoice_info="12345 от 01.05.2025",
        invoice_number="12345",
        invoice_date="01.05.2025",
        seller="Тестовый продавец",
        is_shipped=Status.SHIPPED,
        is_paid=Status.PAID,
        period=sample_period
    )


@pytest.fixture
def sample_sync_session() -> SyncSession:
    """Sample sync session for tests."""
    return SyncSession(
        sync_type=SyncType.FULL,
        source_file_path="test_file.xlsx",
        source_file_hash="abc123",
        created_by="test_user"
    )

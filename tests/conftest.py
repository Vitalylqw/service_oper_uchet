"""
Pytest configuration and common fixtures.
"""

import importlib
import platform
import sys
import tempfile
import time
from decimal import Decimal
from pathlib import Path

import pytest


def _alias_domain_modules() -> None:
    """Alias `domain` and `src.domain` modules to avoid duplicate class identities."""
    module_names = [
        "domain",
        "domain.builders",
        "domain.builders.deal_builder",
        "domain.exceptions",
        "domain.interfaces",
        "domain.models",
        "domain.models.deal",
        "domain.models.sync_session",
        "domain.value_objects",
        "domain.value_objects.common",
    ]

    for domain_name in module_names:
        module = importlib.import_module(domain_name)
        src_name = f"src.{domain_name}"
        sys.modules.setdefault(src_name, module)


_alias_domain_modules()


def safe_cleanup_file(file_path: str | Path) -> None:
    """
    Safely remove file, handling Windows file locking issues.

    Args:
        file_path: Path to file to remove
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            Path(file_path).unlink()
            break
        except (OSError, PermissionError) as e:
            if attempt == max_retries - 1:
                # On any OS, file might be locked - log but don't fail
                print(f"Warning: Could not delete temporary file: {e}")
            else:
                # Wait and retry
                time.sleep(0.1)

from src.domain.models import Deal, DealItem, SyncSession
from src.domain.models.sync_session import SyncType
from src.domain.value_objects import Money, Period, Status


def build_test_period(month: str = "Май", year: str = "2025") -> Period:
    """Build a normalized test period."""
    return Period(month=month, year=year, full_name=f"{month} {year}")


def build_test_deal(
    *,
    period: Period | None = None,
    explicit_id=None,
    **overrides,
) -> Deal:
    """Build a valid Deal using the current domain contract."""
    period = period or build_test_period()
    data = {
        "client_name": "Тестовый клиент",
        "invoice_info": "12345 от 01.05.2025",
        "invoice_number": "12345",
        "invoice_date": "01.05.2025",
        "seller": "Тестовый продавец",
        "is_shipped": Status.SHIPPED,
        "is_paid": Status.PAID,
        "period": period,
        "period_month": period.month,
        "period_year": period.year,
    }
    data.update(overrides)
    deal = Deal(**data)
    if explicit_id is not None:
        deal.set_id(explicit_id)
    return deal


def build_test_item(
    *,
    deal: Deal | None = None,
    position_number: int = 1,
    explicit_id=None,
    **overrides,
) -> DealItem:
    """Build a valid DealItem using the current domain contract."""
    period = deal.period if deal is not None else build_test_period()
    data = {
        "product_name": "Тестовый товар",
        "supplier_name": "Тестовый поставщик",
        "client_name": deal.client_name if deal is not None else "Тестовый клиент",
        "period_month": period.month,
        "period_year": period.year,
        "seller": deal.seller if deal is not None else "Тестовый продавец",
        "invoice_info": deal.invoice_info if deal is not None else "12345 от 01.05.2025",
        "position_number": position_number,
    }
    if deal is not None:
        data["deal_id"] = deal.id
        data["deal_key"] = deal.deal_key
    data.update(overrides)
    item = DealItem(**data)
    if explicit_id is not None:
        item.set_id(explicit_id)
    return item


@pytest.fixture
def sample_period() -> Period:
    """Sample period for tests."""
    return build_test_period()


@pytest.fixture
def sample_money() -> Money:
    """Sample money for tests."""
    return Money(amount=Decimal("1000.50"))


@pytest.fixture
def sample_deal_item() -> DealItem:
    """Sample deal item for tests."""
    return build_test_item(
        quantity=Decimal("10.5"),
        purchase_price=Money(amount=Decimal("100.00")),
        sale_price=Money(amount=Decimal("150.00")),
        pickup_date="15",
    )


@pytest.fixture
def sample_deal(sample_period: Period) -> Deal:
    """Sample deal for tests."""
    return build_test_deal(
        period=sample_period,
    )


@pytest.fixture
def sample_sync_session() -> SyncSession:
    """Sample sync session for tests."""
    return SyncSession(
        sync_type=SyncType.FULL,
        source_file_path="test_file.xlsx",
        source_file_hash="abc123",
        source_file_size=512,  # Required field
        created_by="test_user",
    )


# Database Integration Test Fixtures

@pytest.fixture(scope="session")
async def test_database():
    """Test database for integration tests."""
    from src.infrastructure.database.connection import DatabaseConfig, DatabaseManager

    # Создаем временную БД для тестов
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        config = DatabaseConfig()
        config.db_type = "sqlite"
        config.sqlite_db_path = tmp_file.name

        db_manager = DatabaseManager(config)

        # Создаем схему
        from src.infrastructure.database.models import Base
        Base.metadata.create_all(db_manager.sync_engine)

        yield db_manager

        # Cleanup with Windows-safe file removal
        try:
            # Close database connections first
            await db_manager.close()
        except Exception:
            pass  # Ignore cleanup errors

        # Safe file removal with retry for Windows
        safe_cleanup_file(tmp_file.name)


@pytest.fixture
async def test_session(test_database):
    """Test database session."""
    async with test_database.get_async_session() as session:
        yield session


@pytest.fixture
async def test_repositories(test_session, test_database):
    """Test repositories with real database connection."""
    from src.infrastructure.database.repositories import (
        DealRepositoryImplementation,
        SyncSessionRepositoryImplementation,
    )

    deal_repo = DealRepositoryImplementation(test_session)
    session_repo = SyncSessionRepositoryImplementation(test_session)

    return {
        "deals": deal_repo,
        "sessions": session_repo,
        "db_manager": test_database,
        "session": test_session
    }


@pytest.fixture
def real_excel_file():
    """Real Excel file for integration tests."""
    file_path = Path("data/real_data_for_testing/Data_source_excel.xlsx")

    if not file_path.exists():
        pytest.skip(f"Real Excel file {file_path} not found")

    return str(file_path)

"""
Pytest configuration and common fixtures.
"""

import platform
import tempfile
import time
from decimal import Decimal
from pathlib import Path

import pytest


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
                # On Windows, file might be locked - log but don't fail
                if platform.system() == "Windows":
                    print(f"Warning: Could not delete temporary file: {e}")
                else:
                    raise
            else:
                # Wait and retry
                time.sleep(0.1)

from src.domain.models import Deal, DealItem, SyncSession
from src.domain.models.sync_session import SyncType
from src.domain.value_objects import Money, Period, Status


@pytest.fixture
def sample_period() -> Period:
    """Sample period for tests."""
    return Period(month="Май", year="2025", full_name="Май 2025")


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
        pickup_date="15",
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
    file_path = Path("Data_source_excel.xlsx")

    if not file_path.exists():
        pytest.skip(f"Real Excel file {file_path} not found")

    return str(file_path)

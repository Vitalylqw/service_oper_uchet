"""
Unit tests for RealDealService.

Tests the real deal service wrapper that integrates DealRepositoryImplementation
with FastAPI presentation layer.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.domain.models import Deal, DealItem
from src.domain.value_objects import Money, Period
from src.infrastructure.database.repositories import DealRepositoryImplementation
from src.presentation.api.services.real_deal_service import RealDealService


@pytest.mark.unit
class TestRealDealService:
    """Test RealDealService functionality."""

    @pytest.fixture
    def mock_deal_repository(self):
        """Create mock deal repository."""
        repository = AsyncMock(spec=DealRepositoryImplementation)
        return repository

    @pytest.fixture
    def real_deal_service(self, mock_deal_repository):
        """Create RealDealService instance with mocked repository."""
        return RealDealService(mock_deal_repository)

    @pytest.fixture
    def sample_deal(self):
        """Create sample deal for testing."""
        period = Period(month="Январь", year="2024", full_name="Январь 2024")
        deal = Deal(
            client_name="Тестовый клиент",
            invoice_info="Счет 001 от 15.01.2024",
            period=period,
        )
        deal.id = uuid.uuid4()
        # НЕ устанавливаем deal_key - это computed field!
        return deal

    @pytest.fixture
    def sample_deal_with_items(self, sample_deal):
        """Create sample deal with items."""
        item1 = DealItem(
            product_name="Товар 1",
            supplier_name="Поставщик 1",
            sale_price=Money(amount=1000),
            purchase_price=Money(amount=800),
        )
        item2 = DealItem(
            product_name="Товар 2",
            supplier_name="Поставщик 2",
            sale_price=Money(amount=2000),
            purchase_price=Money(amount=1500),
        )

        sample_deal.add_item(item1)
        sample_deal.add_item(item2)
        sample_deal.calculate_totals()

        return sample_deal

    async def test_get_deals_paginated_empty_database(self, real_deal_service, mock_deal_repository):
        """Test get_deals_paginated with empty database."""
        # Arrange
        mock_deal_repository.find_all_paginated.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "limit": 10,
            "pages": 0
        }
        
        # Act
        result = await real_deal_service.get_deals_paginated(page=1, limit=10, filters={})

        # Assert
        assert result["items"] == []
        assert result["total"] == 0
        assert result["page"] == 1
        assert result["limit"] == 10
        assert result["pages"] == 0

    async def test_get_deals_paginated_with_filters(self, real_deal_service, mock_deal_repository):
        """Test get_deals_paginated with filters applied."""
        # Arrange
        filters = {"client_name": "Тестовый", "period_month": "01", "period_year": "2024"}
        mock_deal_repository.find_all_paginated.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "limit": 10,
            "pages": 0
        }

        # Act
        result = await real_deal_service.get_deals_paginated(page=1, limit=10, filters=filters)

        # Assert - should return empty results but not fail
        assert isinstance(result, dict)
        assert "items" in result
        assert "total" in result
        assert result["page"] == 1
        assert result["limit"] == 10

    async def test_get_deal_by_id_found(self, real_deal_service, mock_deal_repository, sample_deal):
        """Test get_deal_by_id when deal is found."""
        # Arrange
        deal_id = str(sample_deal.id)
        mock_deal_repository.get_by_id.return_value = sample_deal

        # Act
        result = await real_deal_service.get_deal_by_id(deal_id)

        # Assert
        assert result is not None
        assert result["id"] == deal_id
        assert result["client_name"] == "Тестовый клиент"
        assert result["deal_key"] == "Тестовый клиент|||"  # computed field
        assert result["invoice_info"] == "Счет 001 от 15.01.2024"
        assert result["items_count"] == 0

        # Verify repository was called with correct UUID
        mock_deal_repository.get_by_id.assert_called_once_with(sample_deal.id)

    async def test_get_deal_by_id_not_found(self, real_deal_service, mock_deal_repository):
        """Test get_deal_by_id when deal is not found."""
        # Arrange
        deal_id = str(uuid.uuid4())
        mock_deal_repository.get_by_id.return_value = None

        # Act
        result = await real_deal_service.get_deal_by_id(deal_id)

        # Assert
        assert result is None
        mock_deal_repository.get_by_id.assert_called_once()

    async def test_get_deal_by_id_invalid_uuid(self, real_deal_service):
        """Test get_deal_by_id with invalid UUID format."""
        # Act
        result = await real_deal_service.get_deal_by_id("invalid-uuid")

        # Assert
        assert result is None

    async def test_get_deal_by_id_with_exception(self, real_deal_service, mock_deal_repository):
        """Test get_deal_by_id when repository raises exception."""
        # Arrange
        deal_id = str(uuid.uuid4())
        mock_deal_repository.get_by_id.side_effect = Exception("Database error")

        # Act
        result = await real_deal_service.get_deal_by_id(deal_id)

        # Assert
        assert result is None

    async def test_get_deals_by_client(self, real_deal_service, mock_deal_repository, sample_deal):
        """Test get_deals_by_client method."""
        # Arrange
        client_name = "Тестовый клиент"
        mock_deal_repository.find_by_client.return_value = [sample_deal]

        # Act
        result = await real_deal_service.get_deals_by_client(client_name)

        # Assert
        assert len(result) == 1
        assert result[0]["client_name"] == client_name
        assert result[0]["id"] == str(sample_deal.id)
        mock_deal_repository.find_by_client.assert_called_once_with(client_name)

    async def test_get_deals_by_client_with_exception(self, real_deal_service, mock_deal_repository):
        """Test get_deals_by_client when repository raises exception."""
        # Arrange
        mock_deal_repository.find_by_client.side_effect = Exception("Database error")

        # Act
        result = await real_deal_service.get_deals_by_client("Test Client")

        # Assert
        assert result == []

    async def test_get_deals_by_period(self, real_deal_service, mock_deal_repository, sample_deal):
        """Test get_deals_by_period method."""
        # Arrange
        period_month = "Январь"
        period_year = "2024"
        mock_deal_repository.find_by_period.return_value = [sample_deal]

        # Act
        result = await real_deal_service.get_deals_by_period(period_month, period_year)

        # Assert
        assert len(result) == 1
        assert result[0]["client_name"] == "Тестовый клиент"
        assert result[0]["id"] == str(sample_deal.id)
        # Проверяем, что метод был вызван с правильными параметрами
        mock_deal_repository.find_by_period.assert_called_once_with(period_month, period_year)

    async def test_get_deals_by_period_with_exception(self, real_deal_service, mock_deal_repository):
        """Test get_deals_by_period when repository raises exception."""
        # Arrange
        mock_deal_repository.find_by_period.side_effect = Exception("Database error")

        # Act
        result = await real_deal_service.get_deals_by_period("01", "2024")

        # Assert
        assert result == []

    async def test_domain_deal_to_api_format_basic(self, real_deal_service, sample_deal):
        """Test _domain_deal_to_api_format method with basic deal."""
        # Act
        result = await real_deal_service._domain_deal_to_api_format(sample_deal)

        # Assert
        assert result["id"] == str(sample_deal.id)
        assert result["client_name"] == "Тестовый клиент"
        assert result["deal_key"] == "Тестовый клиент|||"  # computed field
        assert result["invoice_info"] == "Счет 001 от 15.01.2024"
        assert result["items_count"] == 0
        assert "created_at" in result
        assert "updated_at" in result

    async def test_domain_deal_to_api_format_with_items(self, real_deal_service, sample_deal):
        """Test _domain_deal_to_api_format method with include_items=True."""
        # Arrange
        item = DealItem(product_name="Тестовый товар")
        item.id = uuid.uuid4()
        item.quantity = Decimal("5")
        item.sale_price = Money(amount=Decimal("20000.00"))
        item.supplier_name = "Поставщик Тест"
        sample_deal.add_item(item)

        # Act
        result = await real_deal_service._domain_deal_to_api_format(sample_deal, include_items=True)

        # Assert
        assert result["items_count"] == 1
        assert "items" in result
        assert len(result["items"]) == 1

        api_item = result["items"][0]
        assert api_item["id"] == str(item.id)
        assert api_item["product_name"] == "Тестовый товар"
        assert api_item["quantity"] == Decimal("5")
        assert api_item["sale_price"] == Decimal("20000.00")
        assert api_item["supplier_name"] == "Поставщик Тест"

    def test_status_to_bool_conversion(self, real_deal_service):
        """Test _status_to_bool method with various inputs."""
        # Test None
        assert real_deal_service._status_to_bool(None) is False

        # Test boolean values
        assert real_deal_service._status_to_bool(True) is True
        assert real_deal_service._status_to_bool(False) is False

        # Test string values
        assert real_deal_service._status_to_bool("completed") is True
        assert real_deal_service._status_to_bool("да") is True
        assert real_deal_service._status_to_bool("yes") is True
        assert real_deal_service._status_to_bool("true") is True
        assert real_deal_service._status_to_bool("pending") is False
        assert real_deal_service._status_to_bool("нет") is False

    async def test_get_deals_paginated_exception_handling(self, real_deal_service, mock_deal_repository):
        """Test that get_deals_paginated handles exceptions gracefully."""
        # Arrange - симулируем исключение
        mock_deal_repository.find_all_paginated.side_effect = Exception("Database error")

        # Act
        result = await real_deal_service.get_deals_paginated(page=1, limit=10, filters={})

        # Assert - should always return valid structure even on errors
        assert isinstance(result, dict)
        assert all(key in result for key in ["items", "total", "page", "limit", "pages"])
        assert isinstance(result["items"], list)
        assert isinstance(result["total"], int)
        assert result["page"] == 1
        assert result["limit"] == 10

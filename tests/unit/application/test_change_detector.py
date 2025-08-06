"""
Unit tests for Change Detector Service.

Tests the change detection algorithms including hash comparison and detailed field comparison.
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.application.change_detector import ChangeDetectorService
from src.application.change_detector.models import ChangeType, EntityType
from src.domain.interfaces import DealRepository
from src.domain.models import Deal, DealItem
from src.domain.value_objects import Money, Period, Status


@pytest.mark.unit
class TestChangeDetectorService:
    """Test Change Detector Service."""

    @pytest.fixture
    def mock_deal_repository(self):
        """Mock deal repository."""
        return AsyncMock(spec=DealRepository)

    @pytest.fixture
    def change_detector(self, mock_deal_repository):
        """Change detector service instance."""
        return ChangeDetectorService(mock_deal_repository)

    @pytest.fixture
    def sample_period(self):
        """Sample period for testing."""
        return Period(month="Январь", year="2024", full_name="Январь 2024")

    @pytest.fixture
    def sample_deal_1(self, sample_period):
        """Sample deal for testing."""
        deal = Deal(
            client_name="Тестовый клиент 1",
            invoice_info="Счет 001 от 15.01.2024",
            period=sample_period,
        )
        deal.id = uuid.uuid4()
        deal.invoice_number = "001"
        deal.invoice_date = "15.01.2024"
        deal.is_shipped = Status.COMPLETED
        deal.is_paid = Status.PENDING
        deal.seller = "Продавец 1"
        deal.total_revenue = Money(amount=Decimal("100000.00"))

        # Add sample item
        item = DealItem(product_name="Товар 1")
        item.id = uuid.uuid4()
        item.quantity = Decimal("10")
        item.sale_price = Money(amount=Decimal("10000.00"))
        item.supplier_name = "Поставщик 1"
        deal.add_item(item)

        return deal

    @pytest.fixture
    def sample_deal_2(self, sample_period):
        """Another sample deal for testing."""
        deal = Deal(
            client_name="Тестовый клиент 2",
            invoice_info="Счет 002 от 16.01.2024",
            period=sample_period,
        )
        deal.id = uuid.uuid4()
        deal.invoice_number = "002"
        deal.invoice_date = "16.01.2024"
        deal.is_shipped = Status.PENDING
        deal.is_paid = Status.PENDING
        deal.seller = "Продавец 2"
        deal.total_revenue = Money(amount=Decimal("50000.00"))

        # Add sample item
        item = DealItem(product_name="Товар 2")
        item.id = uuid.uuid4()
        item.quantity = Decimal("5")
        item.sale_price = Money(amount=Decimal("10000.00"))
        item.supplier_name = "Поставщик 2"
        deal.add_item(item)

        return deal

    async def test_detect_changes_no_database_deals(
        self, change_detector, mock_deal_repository, sample_deal_1, sample_deal_2
    ):
        """Test change detection when no deals exist in database."""
        # Arrange
        excel_deals = [sample_deal_1, sample_deal_2]
        mock_deal_repository.find_by_period.return_value = []

        # Act
        result = await change_detector.detect_changes(excel_deals, sync_period_months=3)

        # Assert
        assert result.total_excel_deals == 2
        assert result.total_db_deals == 0
        assert result.insertion_count == 4  # 2 deals + 2 items
        assert result.update_count == 0
        assert result.deletion_count == 0
        assert result.has_changes

    async def test_detect_changes_identical_data(
        self, change_detector, mock_deal_repository, sample_deal_1, sample_deal_2
    ):
        """Test change detection when Excel and database data are identical."""
        # Arrange
        excel_deals = [sample_deal_1, sample_deal_2]
        db_deals = [sample_deal_1, sample_deal_2]  # Same deals
        mock_deal_repository.find_by_period.return_value = db_deals

        # Act
        result = await change_detector.detect_changes(excel_deals, sync_period_months=3)

        # Assert
        assert result.total_excel_deals == 2
        assert result.total_db_deals == 2
        assert result.insertion_count == 0
        assert result.update_count == 0
        assert result.deletion_count == 0
        assert not result.has_changes

    async def test_detect_changes_deal_updated(
        self, change_detector, mock_deal_repository, sample_deal_1, sample_period
    ):
        """Test change detection when deal is updated."""
        # Arrange
        excel_deal = sample_deal_1

        # Create modified version for database
        db_deal = Deal(
            client_name="Тестовый клиент 1",
            invoice_info="Счет 001 от 15.01.2024",
            period=sample_period,
        )
        db_deal.id = excel_deal.id
        # Set fields that determine deal_key to match excel_deal
        db_deal.invoice_number = excel_deal.invoice_number
        db_deal.invoice_date = excel_deal.invoice_date
        db_deal.is_shipped = Status.PENDING  # Different status
        db_deal.is_paid = Status.PENDING
        db_deal.seller = excel_deal.seller  # Same seller to keep deal_key identical
        db_deal.total_revenue = Money(amount=Decimal("80000.00"))  # Different amount
        db_deal.kickback_amount = Money(amount=Decimal("5000.00"))  # Different kickback

        # Same item for both deals
        item = DealItem(product_name="Товар 1")
        item.id = excel_deal.items[0].id
        item.quantity = excel_deal.items[0].quantity
        item.sale_price = excel_deal.items[0].sale_price
        item.supplier_name = excel_deal.items[0].supplier_name
        db_deal.add_item(item)

        excel_deals = [excel_deal]
        db_deals = [db_deal]
        mock_deal_repository.find_by_period.return_value = db_deals

        # Act
        result = await change_detector.detect_changes(excel_deals, sync_period_months=3)

        # Assert
        assert result.total_excel_deals == 1
        assert result.total_db_deals == 1
        assert result.insertion_count == 0
        assert result.update_count == 1  # Deal was updated
        assert result.deletion_count == 0
        assert result.has_changes

        # Check deal change details
        deal_changes = result.get_deal_changes()
        assert len(deal_changes) == 1
        change = deal_changes[0]
        assert change.change_type == ChangeType.UPDATE
        assert change.entity_type == EntityType.DEAL
        assert change.has_field_changes
        assert "is_shipped" in change.field_changes
        assert "total_revenue" in change.field_changes
        assert "kickback_amount" in change.field_changes

    async def test_detect_changes_deal_deleted(
        self, change_detector, mock_deal_repository, sample_deal_1, sample_deal_2
    ):
        """Test change detection when deal is deleted from Excel."""
        # Arrange
        excel_deals = [sample_deal_1]  # Only one deal
        db_deals = [sample_deal_1, sample_deal_2]  # Two deals in DB
        mock_deal_repository.find_by_period.return_value = db_deals

        # Act
        result = await change_detector.detect_changes(excel_deals, sync_period_months=3)

        # Assert
        assert result.total_excel_deals == 1
        assert result.total_db_deals == 2
        assert result.insertion_count == 0
        assert result.update_count == 0
        assert result.deletion_count == 2  # 1 deal + 1 item deleted
        assert result.has_changes

        # Check deletion changes
        deletions = result.get_changes_by_type(ChangeType.DELETE)
        assert len(deletions) == 2
        deal_deletion = [c for c in deletions if c.entity_type == EntityType.DEAL][0]
        assert deal_deletion.entity_key == sample_deal_2.deal_key

    async def test_detect_changes_item_updated(
        self, change_detector, mock_deal_repository, sample_deal_1, sample_period
    ):
        """Test change detection when deal item fields are changed (creates new position)."""
        # Arrange
        excel_deal = sample_deal_1

        # Create DB deal with modified item
        db_deal = Deal(
            client_name=excel_deal.client_name,
            invoice_info=excel_deal.invoice_info,
            period=sample_period,
        )
        db_deal.id = excel_deal.id
        # Copy all deal fields exactly (no need to set deal_key as it's computed)
        for attr in ["invoice_number", "invoice_date", "is_shipped", "is_paid", "seller"]:
            setattr(db_deal, attr, getattr(excel_deal, attr))
        db_deal.total_revenue = excel_deal.total_revenue

        # Modified item - any field change creates different hash_key (new position)
        db_item = DealItem(product_name="Товар 1")
        db_item.id = excel_deal.items[0].id
        db_item.quantity = Decimal("15")  # Different quantity → different hash → new position
        db_item.sale_price = Money(amount=Decimal("12000.00"))  # Different price → different hash → new position  
        db_item.supplier_name = excel_deal.items[0].supplier_name  # Same supplier
        db_item.purchase_price = Money(amount=Decimal("8000.00"))  # Different purchase price → different hash → new position
        db_item.pickup_date = "20.01.2024"  # Different pickup date → different hash → new position
        db_deal.add_item(db_item)

        excel_deals = [excel_deal]
        db_deals = [db_deal]
        mock_deal_repository.find_by_period.return_value = db_deals

        # Act
        result = await change_detector.detect_changes(excel_deals, sync_period_months=3)

        # Assert - with hash_key logic, different fields = different positions
        assert result.insertion_count == 1  # New position created (Excel version)
        assert result.update_count == 0     # No updates, only replacement
        assert result.deletion_count == 1   # Old position deleted (DB version)

        # Check changes details
        insertions = result.insertions
        deletions = result.deletions
        assert len(insertions) == 1
        assert len(deletions) == 1
        
        # Insertion should be the Excel item (new version)
        excel_item_hash = excel_deal.items[0].hash_key.value
        insertion = insertions[0]
        assert insertion.entity_type == EntityType.DEAL_ITEM
        assert insertion.new_hash == excel_item_hash
        
        # Deletion should be the DB item (old version)  
        db_item_hash = db_item.hash_key.value
        deletion = deletions[0]
        assert deletion.entity_type == EntityType.DEAL_ITEM
        assert deletion.old_hash == db_item_hash

    async def test_build_entity_hash_cache(self, change_detector, sample_deal_1):
        """Test hash cache building."""
        # Act
        cache = change_detector._build_entity_hash_cache([sample_deal_1])

        # Assert
        assert cache.entity_count == 2  # 1 deal + 1 item
        assert cache.has_entity(sample_deal_1.deal_key)

        item_key = change_detector._get_item_key(sample_deal_1, sample_deal_1.items[0])
        assert cache.has_entity(item_key)

    async def test_calculate_deal_hash(self, change_detector, sample_deal_1):
        """Test deal hash calculation."""
        # Act
        hash1 = change_detector._calculate_deal_hash(sample_deal_1)
        hash2 = change_detector._calculate_deal_hash(sample_deal_1)

        # Assert
        assert hash1 == hash2  # Same deal should produce same hash
        assert len(hash1) == 32  # MD5 hash length

    async def test_calculate_deal_hash_different_deals(
        self, change_detector, sample_deal_1, sample_deal_2
    ):
        """Test that different deals produce different hashes."""
        # Act
        hash1 = change_detector._calculate_deal_hash(sample_deal_1)
        hash2 = change_detector._calculate_deal_hash(sample_deal_2)

        # Assert
        assert hash1 != hash2

    async def test_calculate_item_hash(self, change_detector, sample_deal_1):
        """Test item hash calculation."""
        # Act
        item = sample_deal_1.items[0]
        hash1 = change_detector._calculate_item_hash(item)
        hash2 = change_detector._calculate_item_hash(item)

        # Assert
        assert hash1 == hash2  # Same item should produce same hash
        assert len(hash1) == 32  # MD5 hash length

    async def test_get_item_key(self, change_detector, sample_deal_1):
        """Test item key generation using full hash with deal_key and position_number."""
        # Act
        item = sample_deal_1.items[0]
        key = change_detector._get_item_key(sample_deal_1, item)

        # Assert
        expected_key = item.get_full_hash_key(sample_deal_1.deal_key).value
        assert key == expected_key
        assert len(key) == 32  # MD5 hash length
        assert isinstance(key, str)

    async def test_compare_deal_fields_no_changes(self, change_detector, sample_deal_1):
        """Test deal field comparison with no changes."""
        # Act
        changes = change_detector._compare_deal_fields(sample_deal_1, sample_deal_1)

        # Assert
        assert len(changes) == 0

    async def test_compare_deal_fields_with_changes(
        self, change_detector, sample_deal_1, sample_period
    ):
        """Test deal field comparison with changes."""
        # Arrange
        modified_deal = Deal(
            client_name="Измененный клиент",  # Changed
            invoice_info=sample_deal_1.invoice_info,
            period=sample_period,
        )
        modified_deal.id = sample_deal_1.id
        modified_deal.invoice_number = "999"  # Changed
        modified_deal.invoice_date = sample_deal_1.invoice_date
        modified_deal.is_shipped = Status.COMPLETED  # Same
        modified_deal.is_paid = Status.COMPLETED  # Changed
        modified_deal.seller = sample_deal_1.seller
        modified_deal.total_revenue = Money(amount=Decimal("200000.00"))  # Changed

        # Act
        changes = change_detector._compare_deal_fields(sample_deal_1, modified_deal)

        # Assert
        assert len(changes) == 4  # 4 fields changed
        assert "client_name" in changes
        assert "invoice_number" in changes
        assert "is_paid" in changes
        assert "total_revenue" in changes

        # Check change values
        assert changes["client_name"]["old_value"] == "Тестовый клиент 1"
        assert changes["client_name"]["new_value"] == "Измененный клиент"
        assert changes["is_paid"]["old_value"] == "pending"
        assert changes["is_paid"]["new_value"] == "completed"

    async def test_compare_item_fields_with_changes(self, change_detector):
        """Test item field comparison with changes."""
        # Arrange
        old_item = DealItem(product_name="Товар 1")
        old_item.quantity = Decimal("10")
        old_item.sale_price = Money(amount=Decimal("1000.00"))
        old_item.supplier_name = "Поставщик 1"

        new_item = DealItem(product_name="Товар 1")
        new_item.quantity = Decimal("15")  # Changed
        new_item.sale_price = Money(amount=Decimal("1200.00"))  # Changed
        new_item.supplier_name = "Новый поставщик"  # Changed

        # Act
        changes = change_detector._compare_item_fields(old_item, new_item)

        # Assert
        assert len(changes) == 3
        assert "quantity" in changes
        assert "sale_price" in changes
        assert "supplier_name" in changes

        assert changes["quantity"]["old_value"] == "10"
        assert changes["quantity"]["new_value"] == "15"

    async def test_get_database_deals(self, change_detector, mock_deal_repository, sample_deal_1):
        """Test getting database deals for comparison."""
        # Arrange
        excel_deals = [sample_deal_1]
        mock_deal_repository.find_by_period.return_value = [sample_deal_1]

        # Act
        db_deals = await change_detector._get_database_deals(excel_deals, sync_period_months=3)

        # Assert
        assert len(db_deals) == 1
        mock_deal_repository.find_by_period.assert_called_once_with("Январь", "2024")

    async def test_get_database_deals_multiple_periods(
        self, change_detector, mock_deal_repository, sample_deal_1, sample_deal_2
    ):
        """Test getting database deals for multiple periods."""
        # Arrange
        # Create deal in different period
        feb_period = Period(month="Февраль", year="2024", full_name="Февраль 2024")
        sample_deal_2.period = feb_period

        excel_deals = [sample_deal_1, sample_deal_2]
        mock_deal_repository.find_by_period.side_effect = [
            [sample_deal_1],  # January deals
            [sample_deal_2],  # February deals
        ]

        # Act
        db_deals = await change_detector._get_database_deals(excel_deals, sync_period_months=3)

        # Assert
        assert len(db_deals) == 2
        assert mock_deal_repository.find_by_period.call_count == 2

    async def test_get_cache_stats(self, change_detector):
        """Test cache statistics."""
        # Act
        stats = change_detector.get_cache_stats()

        # Assert
        assert "hash_cache_entities" in stats
        assert isinstance(stats["hash_cache_entities"], int)

    async def test_performance_metrics(self, change_detector, mock_deal_repository, sample_deal_1):
        """Test that performance metrics are captured."""
        # Arrange
        excel_deals = [sample_deal_1]
        mock_deal_repository.find_by_period.return_value = []

        # Act
        result = await change_detector.detect_changes(excel_deals, sync_period_months=3)

        # Assert
        assert result.comparison_duration_seconds >= 0  # Can be 0 for fast operations
        assert result.hash_comparison_count > 0
        assert isinstance(result.comparison_duration_seconds, float)

    async def test_error_handling_in_get_database_deals(
        self, change_detector, mock_deal_repository, sample_deal_1
    ):
        """Test error handling when getting database deals fails."""
        # Arrange
        excel_deals = [sample_deal_1]
        mock_deal_repository.find_by_period.side_effect = Exception("Database error")

        # Act
        db_deals = await change_detector._get_database_deals(excel_deals, sync_period_months=3)

        # Assert
        assert db_deals == []  # Should return empty list on error

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
from src.domain.value_objects import Money, Period, Status
from tests.conftest import build_test_deal, build_test_item


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
        deal = build_test_deal(
            period=sample_period,
            explicit_id=uuid.uuid4(),
            client_name="Тестовый клиент 1",
            invoice_info="Счет 001 от 15.01.2024",
            invoice_number="001",
            invoice_date="15.01.2024",
            seller="Продавец 1",
            is_shipped=Status.COMPLETED,
            is_paid=Status.PENDING,
            total_revenue=Money(amount=Decimal("100000.00")),
        )

        # Add sample item
        item = build_test_item(
            deal=deal,
            explicit_id=uuid.uuid4(),
            position_number=1,
            product_name="Товар 1",
            quantity=Decimal("10"),
            sale_price=Money(amount=Decimal("10000.00")),
            supplier_name="Поставщик 1",
        )
        deal.add_item(item)

        return deal

    @pytest.fixture
    def sample_deal_2(self, sample_period):
        """Another sample deal for testing."""
        deal = build_test_deal(
            period=sample_period,
            explicit_id=uuid.uuid4(),
            client_name="Тестовый клиент 2",
            invoice_info="Счет 002 от 16.01.2024",
            invoice_number="002",
            invoice_date="16.01.2024",
            seller="Продавец 2",
            is_shipped=Status.PENDING,
            is_paid=Status.PENDING,
            total_revenue=Money(amount=Decimal("50000.00")),
        )

        # Add sample item
        item = build_test_item(
            deal=deal,
            explicit_id=uuid.uuid4(),
            position_number=1,
            product_name="Товар 2",
            quantity=Decimal("5"),
            sale_price=Money(amount=Decimal("10000.00")),
            supplier_name="Поставщик 2",
        )
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
        assert result.insertion_count == 2  # 2 deals
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

    async def test_detect_changes_ignores_source_row_only_changes(
        self, change_detector, mock_deal_repository, sample_period
    ):
        """Changing only Excel row metadata must not create business updates."""
        db_deal = build_test_deal(
            period=sample_period,
            explicit_id=uuid.uuid4(),
            client_name="Тестовый клиент 1",
            invoice_info="Счет 001 от 15.01.2024",
            invoice_number="001",
            invoice_date="15.01.2024",
            seller="Продавец 1",
            is_shipped=Status.COMPLETED,
            is_paid=Status.PENDING,
            total_revenue=Money(amount=Decimal("100000.00")),
            source_row_number=10,
        )
        db_item = build_test_item(
            deal=db_deal,
            explicit_id=uuid.uuid4(),
            position_number=1,
            product_name="Товар 1",
            quantity=Decimal("10"),
            sale_price=Money(amount=Decimal("10000.00")),
            supplier_name="Поставщик 1",
            source_row_number=11,
        )
        db_deal.add_item(db_item)

        excel_deal = build_test_deal(
            period=sample_period,
            explicit_id=db_deal.id,
            client_name=db_deal.client_name,
            invoice_info=db_deal.invoice_info,
            invoice_number=db_deal.invoice_number,
            invoice_date=db_deal.invoice_date,
            seller=db_deal.seller,
            is_shipped=db_deal.is_shipped,
            is_paid=db_deal.is_paid,
            total_revenue=db_deal.total_revenue,
            source_row_number=20,
        )
        excel_item = build_test_item(
            deal=excel_deal,
            explicit_id=db_item.id,
            position_number=db_item.position_number,
            product_name=db_item.product_name,
            quantity=db_item.quantity,
            sale_price=db_item.sale_price,
            supplier_name=db_item.supplier_name,
            source_row_number=21,
        )
        excel_deal.add_item(excel_item)

        mock_deal_repository.find_by_period.return_value = [db_deal]

        result = await change_detector.detect_changes([excel_deal], sync_period_months=3)

        assert result.total_changes == 0

    async def test_detect_changes_deal_updated(
        self, change_detector, mock_deal_repository, sample_deal_1, sample_period
    ):
        """Test change detection when deal is updated."""
        # Arrange
        excel_deal = sample_deal_1

        # Create modified version for database
        db_deal = build_test_deal(
            period=sample_period,
            explicit_id=excel_deal.id,
            client_name="Тестовый клиент 1",
            invoice_info="Счет 001 от 15.01.2024",
            invoice_number=excel_deal.invoice_number,
            invoice_date=excel_deal.invoice_date,
            seller=excel_deal.seller,
            is_shipped=Status.PENDING,
            is_paid=Status.PENDING,
            total_revenue=Money(amount=Decimal("80000.00")),
        )
        db_deal.kickback_amount = Money(amount=Decimal("5000.00"))  # Different kickback

        # Same item for both deals
        item = build_test_item(
            deal=db_deal,
            explicit_id=excel_deal.items[0].id,
            position_number=1,
            product_name="Товар 1",
            quantity=excel_deal.items[0].quantity,
            sale_price=excel_deal.items[0].sale_price,
            supplier_name=excel_deal.items[0].supplier_name,
        )
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
        assert result.deletion_count == 1  # 1 deal deleted
        assert result.has_changes

        # Check deletion changes
        deletions = result.get_changes_by_type(ChangeType.DELETE)
        assert len(deletions) == 1
        deal_deletion = [c for c in deletions if c.entity_type == EntityType.DEAL][0]
        assert deal_deletion.entity_key == sample_deal_2.deal_key

    async def test_detect_changes_item_updated_promotes_to_deal_update(
        self, change_detector, mock_deal_repository, sample_deal_1, sample_period
    ):
        """Test that position changes surface as a deal update."""
        # Arrange
        excel_deal = sample_deal_1

        # Create DB deal with modified item
        db_deal = build_test_deal(
            period=sample_period,
            explicit_id=excel_deal.id,
            client_name=excel_deal.client_name,
            invoice_info=excel_deal.invoice_info,
            invoice_number=excel_deal.invoice_number,
            invoice_date=excel_deal.invoice_date,
            seller=excel_deal.seller,
            is_shipped=excel_deal.is_shipped,
            is_paid=excel_deal.is_paid,
            total_revenue=excel_deal.total_revenue,
        )

        # Modified item - any field change creates different hash_key (new position)
        db_item = build_test_item(
            deal=db_deal,
            explicit_id=excel_deal.items[0].id,
            position_number=1,
            product_name="Товар 1",
            quantity=Decimal("15"),
            sale_price=Money(amount=Decimal("12000.00")),
            supplier_name=excel_deal.items[0].supplier_name,
            purchase_price=Money(amount=Decimal("8000.00")),
            pickup_date="20.01.2024",
        )
        db_deal.add_item(db_item)

        excel_deals = [excel_deal]
        db_deals = [db_deal]
        mock_deal_repository.find_by_period.return_value = db_deals

        # Act
        result = await change_detector.detect_changes(excel_deals, sync_period_months=3)

        assert result.insertion_count == 0
        assert result.update_count == 1
        assert result.deletion_count == 0

        deal_changes = result.get_deal_changes()
        assert len(deal_changes) == 1
        change = deal_changes[0]
        assert change.entity_type == EntityType.DEAL
        assert "items" in change.field_changes

    async def test_build_entity_hash_cache(self, change_detector, sample_deal_1):
        """Test hash cache building."""
        # Act
        cache = change_detector._build_entity_hash_cache([sample_deal_1])

        # Assert
        assert cache.entity_count == 1  # 1 deal
        assert cache.has_entity(sample_deal_1.deal_key)

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

    async def test_compare_deal_fields_ignores_empty_optional_strings(
        self, change_detector, sample_period
    ):
        """Test empty optional strings are equivalent to missing values."""
        old_deal = build_test_deal(
            period=sample_period,
            client_name="Клиент",
            invoice_info="Счет 001 от 15.01.2024",
            invoice_number="001",
            invoice_date="15.01.2024",
            seller="Продавец",
            upd_number=None,
        )
        new_deal = build_test_deal(
            period=sample_period,
            client_name=old_deal.client_name,
            invoice_info=old_deal.invoice_info,
            invoice_number=old_deal.invoice_number,
            invoice_date=old_deal.invoice_date,
            seller=old_deal.seller,
            upd_number="",
        )

        changes = change_detector._compare_deal_fields(old_deal, new_deal)

        assert "upd_number" not in changes

    async def test_compare_item_fields_ignores_decimal_scale(self, change_detector):
        """Test detailed item comparison ignores DB Decimal scale differences."""
        old_item = build_test_item(
            position_number=1,
            product_name="Товар 1",
            quantity=Decimal("10.000"),
            sale_price=Money(amount=Decimal("1000.00")),
            supplier_name="Поставщик 1",
        )
        new_item = build_test_item(
            position_number=1,
            product_name="Товар 1",
            quantity=Decimal("10"),
            sale_price=Money(amount=Decimal("1000")),
            supplier_name="Поставщик 1",
        )

        changes = change_detector._compare_item_fields(old_item, new_item)

        assert changes == {}

    async def test_compare_deal_fields_with_changes(
        self, change_detector, sample_deal_1, sample_period
    ):
        """Test deal field comparison with changes."""
        # Arrange
        modified_deal = build_test_deal(
            period=sample_period,
            explicit_id=sample_deal_1.id,
            client_name="Измененный клиент",  # Changed
            invoice_info=sample_deal_1.invoice_info,
            invoice_number="999",
            invoice_date=sample_deal_1.invoice_date,
            seller=sample_deal_1.seller,
            is_shipped=Status.COMPLETED,
            is_paid=Status.COMPLETED,
            total_revenue=Money(amount=Decimal("200000.00")),
        )
        modified_item = build_test_item(
            deal=modified_deal,
            explicit_id=sample_deal_1.items[0].id,
            position_number=1,
            product_name=sample_deal_1.items[0].product_name,
            quantity=sample_deal_1.items[0].quantity,
            sale_price=sample_deal_1.items[0].sale_price,
            supplier_name=sample_deal_1.items[0].supplier_name,
        )
        modified_deal.add_item(modified_item)

        # Act
        changes = change_detector._compare_deal_fields(sample_deal_1, modified_deal)

        # Assert
        assert len(changes) == 5
        assert "client_name" in changes
        assert "invoice_number" in changes
        assert "is_paid" in changes
        assert "total_revenue" in changes
        assert "items" in changes

        # Check change values
        assert changes["client_name"]["old_value"] == "Тестовый клиент 1"
        assert changes["client_name"]["new_value"] == "Измененный клиент"
        assert changes["is_paid"]["old_value"] == "pending"
        assert changes["is_paid"]["new_value"] == "completed"

    async def test_compare_deal_fields_marks_position_changes(
        self, change_detector, sample_deal_1, sample_period
    ):
        """Test that position changes appear inside deal field changes."""
        modified_deal = build_test_deal(
            period=sample_period,
            explicit_id=sample_deal_1.id,
            client_name=sample_deal_1.client_name,
            invoice_info=sample_deal_1.invoice_info,
            invoice_number=sample_deal_1.invoice_number,
            invoice_date=sample_deal_1.invoice_date,
            seller=sample_deal_1.seller,
            is_shipped=sample_deal_1.is_shipped,
            is_paid=sample_deal_1.is_paid,
            total_revenue=sample_deal_1.total_revenue,
        )
        modified_item = build_test_item(
            deal=modified_deal,
            explicit_id=sample_deal_1.items[0].id,
            position_number=1,
            product_name=sample_deal_1.items[0].product_name,
            quantity=sample_deal_1.items[0].quantity,
            sale_price=sample_deal_1.items[0].sale_price,
            supplier_name="Другой поставщик",
        )
        modified_deal.add_item(modified_item)

        changes = change_detector._compare_deal_fields(sample_deal_1, modified_deal)

        assert list(changes.keys()) == ["items"]

    async def test_compare_item_fields_with_changes(self, change_detector):
        """Test item field comparison with changes."""
        # Arrange
        old_item = build_test_item(
            position_number=1,
            product_name="Товар 1",
            quantity=Decimal("10"),
            sale_price=Money(amount=Decimal("1000.00")),
            supplier_name="Поставщик 1",
        )
        new_item = build_test_item(
            position_number=1,
            product_name="Товар 1",
            quantity=Decimal("15"),
            sale_price=Money(amount=Decimal("1200.00")),
            supplier_name="Новый поставщик",
        )

        # Act
        changes = change_detector._compare_item_fields(old_item, new_item)

        # Assert
        assert len(changes) == 4
        assert "quantity" in changes
        assert "sale_price" in changes
        assert "supplier_name" in changes
        assert "revenue" in changes

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
        sample_deal_2 = build_test_deal(
            period=feb_period,
            explicit_id=sample_deal_2.id,
            client_name=sample_deal_2.client_name,
            invoice_info=sample_deal_2.invoice_info,
            invoice_number=sample_deal_2.invoice_number,
            invoice_date=sample_deal_2.invoice_date,
            seller=sample_deal_2.seller,
            is_shipped=sample_deal_2.is_shipped,
            is_paid=sample_deal_2.is_paid,
            total_revenue=sample_deal_2.total_revenue,
        )
        sample_deal_2.add_item(
            build_test_item(
                deal=sample_deal_2,
                explicit_id=uuid.uuid4(),
                position_number=1,
                product_name="Товар 2",
                quantity=Decimal("5"),
                sale_price=Money(amount=Decimal("10000.00")),
                supplier_name="Поставщик 2",
            )
        )

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

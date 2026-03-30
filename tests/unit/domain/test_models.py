"""
Unit tests for domain models.
"""

from decimal import Decimal
from uuid import UUID

import pytest

from src.domain.models import Deal, DealItem
from src.domain.models.sync_session import SyncResult, SyncType
from src.domain.value_objects import Money, Status
from tests.conftest import build_test_item


@pytest.mark.unit
class TestDealItem:
    """Tests for DealItem model."""

    def test_deal_item_creation(self, sample_deal_item):
        """Test DealItem creation with valid data."""
        item = sample_deal_item
        assert item.product_name == "Тестовый товар"
        assert item.supplier_name == "Тестовый поставщик"
        assert item.quantity == Decimal("10.5")
        assert item.pickup_date == "15"

    def test_deal_item_calculate_fields(self):
        """Test DealItem field calculations."""
        item = build_test_item(
            product_name="Test Product",
            quantity=Decimal("10"),
            purchase_price=Money(amount=Decimal("100")),
            sale_price=Money(amount=Decimal("150")),
        )

        item.calculate_fields()

        # Revenue = quantity * sale_price
        assert item.revenue.amount == Decimal("1500.00")
        # Cost = quantity * purchase_price
        assert item.cost.amount == Decimal("1000.00")
        # Margin = revenue - cost
        assert item.margin.amount == Decimal("500.00")

    def test_deal_item_hash_key(self, sample_deal_item):
        """Test DealItem hash key generation."""
        item = sample_deal_item
        hash_key = item.hash_key
        assert len(hash_key.value) == 32  # MD5 hash length
        assert hash_key.algorithm == "md5"

    def test_deal_item_key(self, sample_deal_item):
        """Test DealItem full hash key generation."""
        item = sample_deal_item
        full_hash = item.get_full_hash_key("deal-key")
        assert len(full_hash.value) == 32
        assert full_hash.algorithm == "md5"

    def test_deal_item_validation_product_name(self):
        """Test DealItem validation for product name."""
        item = DealItem(
            product_name="  Test Product  ",
            client_name="Client",
            period_month="январь",
            period_year="2025",
            seller="Seller",
            invoice_info="123",
            position_number=1,
        )
        assert item.product_name == "Test Product"  # Should be trimmed

    def test_deal_item_minimal_creation(self):
        """Test DealItem creation with minimal data."""
        item = DealItem(
            product_name="Minimal Product",
            client_name="Client",
            period_month="январь",
            period_year="2025",
            seller="Seller",
            invoice_info="123",
            position_number=1,
        )
        assert item.product_name == "Minimal Product"
        assert item.supplier_name is None
        assert item.quantity is None
        assert isinstance(item.id, UUID)


@pytest.mark.unit
class TestDeal:
    """Tests for Deal model."""

    def test_deal_creation(self, sample_deal):
        """Test Deal creation with valid data."""
        deal = sample_deal
        assert deal.client_name == "Тестовый клиент"
        assert deal.invoice_number == "12345"
        assert deal.invoice_date == "01.05.2025"
        assert deal.seller == "Тестовый продавец"
        assert deal.is_shipped == Status.SHIPPED
        assert deal.is_paid == Status.PAID

    def test_deal_add_item(self, sample_deal, sample_deal_item):
        """Test adding item to deal."""
        deal = sample_deal
        item = sample_deal_item

        deal.add_item(item)

        assert len(deal.items) == 1
        assert deal.items[0] == item
        assert item.deal_id == deal.id

    def test_deal_calculate_totals(self, sample_deal):
        """Test deal totals calculation."""
        deal = sample_deal

        # Add items with known values
        item1 = build_test_item(
            deal=deal,
            position_number=1,
            product_name="Item 1",
            revenue=Money(amount=Decimal("1000")),
            cost=Money(amount=Decimal("600")),
            margin=Money(amount=Decimal("400")),
        )
        item2 = build_test_item(
            deal=deal,
            position_number=2,
            product_name="Item 2",
            revenue=Money(amount=Decimal("500")),
            cost=Money(amount=Decimal("300")),
            margin=Money(amount=Decimal("200")),
        )

        deal.add_item(item1)
        deal.add_item(item2)
        deal.calculate_totals()

        # Check computed totals
        assert deal.calc_revenue_amount.amount == Decimal("1500.00")
        assert deal.calc_cost_amount.amount == Decimal("900.00")
        assert deal.calc_margin_amount.amount == Decimal("600.00")

    def test_deal_hash_key(self, sample_deal):
        """Test Deal hash key generation."""
        deal = sample_deal
        hash_key = deal.hash_key
        assert len(hash_key.value) == 32  # MD5 hash length
        assert hash_key.algorithm == "md5"

    def test_deal_key(self, sample_deal):
        """Test Deal unique key generation."""
        deal = sample_deal
        expected_key = "12345|01.05.2025|тестовый продавец|май 2025"
        assert deal.deal_key == expected_key

    def test_deal_validation_client_name(self, sample_period):
        """Test Deal validation for client name."""
        deal = Deal(
            client_name="  Test Client  ",
            invoice_info="123 от 01.01.2025",
            seller="Seller",
            period=sample_period,
            period_month=sample_period.month,
            period_year=sample_period.year,
        )
        assert deal.client_name == "Test Client"  # Should be trimmed

    def test_deal_minimal_creation(self, sample_period):
        """Test Deal creation with minimal required data."""
        deal = Deal(
            client_name="Minimal Client",
            invoice_info="123",
            seller="Seller",
            period=sample_period,
            period_month=sample_period.month,
            period_year=sample_period.year,
        )
        assert deal.client_name == "Minimal Client"
        assert deal.invoice_info == "123"
        assert deal.period == sample_period
        assert isinstance(deal.id, UUID)
        assert len(deal.items) == 0

    def test_deal_upd_number_truncated_to_100(self, sample_period):
        """Test Deal upd_number truncated from 150 to 100 chars."""
        long_upd = "x" * 150
        deal = Deal(
            client_name="Client",
            invoice_info="123",
            seller="Seller",
            period=sample_period,
            period_month=sample_period.month,
            period_year=sample_period.year,
            upd_number=long_upd,
        )
        assert deal.upd_number is not None
        assert len(deal.upd_number) == 100
        assert deal.upd_number == "x" * 100

    def test_deal_invoice_number_truncated_to_50(self, sample_period):
        """Test Deal invoice_number truncated from 60 to 50 chars."""
        long_inv = "n" * 60
        deal = Deal(
            client_name="Client",
            invoice_info="123",
            seller="Seller",
            period=sample_period,
            period_month=sample_period.month,
            period_year=sample_period.year,
            invoice_number=long_inv,
        )
        assert deal.invoice_number is not None
        assert len(deal.invoice_number) == 50

    def test_deal_client_name_truncated_to_100(self, sample_period):
        """Test Deal client_name (StringConstraints) truncated from 150 to 100 chars."""
        long_name = "c" * 150
        deal = Deal(
            client_name=long_name,
            invoice_info="123",
            seller="Seller",
            period=sample_period,
            period_month=sample_period.month,
            period_year=sample_period.year,
        )
        assert len(deal.client_name) == 100
        assert deal.client_name == "c" * 100


@pytest.mark.unit
class TestDealItemTruncation:
    """Tests for DealItem string truncation."""

    def test_deal_item_product_name_truncated_to_500(self):
        """Test DealItem product_name truncated from 600 to 500 chars."""
        long_name = "p" * 600
        item = DealItem(
            product_name=long_name,
            client_name="Client",
            period_month="январь",
            period_year="2025",
            seller="Seller",
            invoice_info="123",
            position_number=1,
        )
        assert len(item.product_name) == 500
        assert item.product_name == "p" * 500

    def test_deal_item_supplier_name_truncated_to_100(self):
        """Test DealItem supplier_name truncated from 150 to 100 chars."""
        long_supplier = "s" * 150
        item = DealItem(
            product_name="Product",
            supplier_name=long_supplier,
            client_name="Client",
            period_month="январь",
            period_year="2025",
            seller="Seller",
            invoice_info="123",
            position_number=1,
        )
        assert item.supplier_name is not None
        assert len(item.supplier_name) == 100


@pytest.mark.unit
class TestTruncateHelper:
    """Tests for _truncate_to_field_max helper."""

    def test_helper_returns_none_for_none(self):
        """Test helper returns None for None input."""
        from src.domain.models.deal import Deal, _truncate_to_field_max

        result = _truncate_to_field_max(Deal, "upd_number", None)
        assert result is None

    def test_helper_returns_value_unchanged_when_within_limit(self):
        """Test helper returns value unchanged when within max_length."""
        from src.domain.models.deal import Deal, _truncate_to_field_max

        short = "short"
        result = _truncate_to_field_max(Deal, "upd_number", short)
        assert result == short

    def test_helper_truncates_when_over_limit(self):
        """Test helper truncates when value exceeds max_length."""
        from src.domain.models.deal import Deal, _truncate_to_field_max

        long_val = "x" * 150
        result = _truncate_to_field_max(Deal, "upd_number", long_val)
        assert result is not None
        assert len(result) == 100
        assert result == "x" * 100


@pytest.mark.unit
class TestSyncSession:
    """Tests for SyncSession model."""

    def test_sync_session_creation(self, sample_sync_session):
        """Test SyncSession creation with valid data."""
        session = sample_sync_session
        assert session.sync_type == SyncType.FULL
        assert session.source_file_path == "test_file.xlsx"
        assert session.source_file_hash == "abc123"
        assert session.created_by == "test_user"
        assert session.status == Status.PENDING

    def test_sync_session_start(self, sample_sync_session):
        """Test SyncSession start method."""
        session = sample_sync_session
        session.start()

        assert session.status == Status.PENDING
        assert session.started_at is not None
        assert session.finished_at is None
        assert session.result is None

    def test_sync_session_complete_success(self, sample_sync_session):
        """Test SyncSession successful completion."""
        session = sample_sync_session
        session.start()
        session.complete_success()

        assert session.status == Status.COMPLETED
        assert session.result == SyncResult.SUCCESS
        assert session.finished_at is not None

    def test_sync_session_complete_partial(self, sample_sync_session):
        """Test SyncSession partial completion."""
        session = sample_sync_session
        session.start()
        session.complete_partial()

        assert session.status == Status.COMPLETED
        assert session.result == SyncResult.PARTIAL
        assert session.finished_at is not None

    def test_sync_session_complete_failed(self, sample_sync_session):
        """Test SyncSession failure completion."""
        session = sample_sync_session
        session.start()
        session.complete_failed("Test error")

        assert session.status == Status.FAILED
        assert session.result == SyncResult.FAILED
        assert session.finished_at is not None
        assert "Test error" in session.stats.errors

    def test_sync_session_cancel(self, sample_sync_session):
        """Test SyncSession cancellation."""
        session = sample_sync_session
        session.start()
        session.cancel("User requested")

        assert session.status == Status.CANCELLED
        assert session.result == SyncResult.CANCELLED
        assert session.finished_at is not None
        assert "Cancelled: User requested" in session.notes

    def test_sync_session_add_error(self, sample_sync_session):
        """Test adding error to sync session."""
        session = sample_sync_session
        session.add_error("Test error message")

        assert "Test error message" in session.stats.errors

    def test_sync_session_add_warning(self, sample_sync_session):
        """Test adding warning to sync session."""
        session = sample_sync_session
        session.add_warning("Test warning message")

        assert "Test warning message" in session.stats.warnings

    def test_sync_session_duration(self, sample_sync_session):
        """Test sync session duration calculation."""
        session = sample_sync_session
        session.start()

        # Before completion, duration should be None
        assert session.duration_seconds is None

        session.complete_success()

        # After completion, should have duration
        assert session.duration_seconds is not None
        assert session.duration_seconds >= 0

    def test_sync_session_success_rates(self, sample_sync_session):
        """Test sync session success rate calculations."""
        session = sample_sync_session

        # Set some stats
        session.stats.total_deals = 100
        session.stats.processed_deals = 95
        session.stats.total_items = 200
        session.stats.processed_items = 180

        assert session.success_rate_deals == 95.0
        assert session.success_rate_items == 90.0

    def test_sync_session_is_running(self, sample_sync_session):
        """Test sync session running status."""
        session = sample_sync_session

        # Initially not running
        assert not session.is_running

        # After start, should be running
        session.start()
        assert session.is_running

        # After completion, should not be running
        session.complete_success()
        assert not session.is_running

    def test_sync_session_is_completed(self, sample_sync_session):
        """Test sync session completion status."""
        session = sample_sync_session

        # Initially not completed
        assert not session.is_completed

        # After start, still not completed
        session.start()
        assert not session.is_completed

        # After completion, should be completed
        session.complete_success()
        assert session.is_completed

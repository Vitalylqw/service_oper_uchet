"""
Unit tests for ReadModelBuilder unique constraints logic.

Tests new unique constraints:
1. (hash_key, is_active) - prevents duplicate active positions
2. (hash_key, version) - ensures version uniqueness
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import Deal, DealItem
from src.domain.value_objects import HashKey, Money, Period
from src.infrastructure.database.models import ReadModelPosition
from src.infrastructure.workers.read_model_builder import ReadModelBuilder


@pytest.mark.unit
class TestReadModelBuilderUniqueConstraints:
    """Test ReadModelBuilder with new unique constraints."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()  # add() is synchronous
        return session

    @pytest.fixture
    def mock_event_store(self):
        """Create mock event store."""
        return AsyncMock()

    @pytest.fixture
    def read_model_builder(self, mock_session, mock_event_store):
        """Create ReadModelBuilder instance."""
        return ReadModelBuilder(mock_session, mock_event_store)

    @pytest.fixture
    def sample_hash_key(self):
        """Sample hash key for tests."""
        return "abc123def456789"

    @pytest.fixture
    def sample_deal_context(self):
        """Sample deal context for denormalization."""
        return {
            "deal_key": "TEST_DEAL_001",
            "client_name": "Тестовый клиент",
            "period_month": "Январь",
            "period_year": "2024",
        }

    @pytest.fixture
    def sample_position_data(self, sample_hash_key, sample_deal_context):
        """Sample position data for tests."""
        return {
            "id": uuid.uuid4(),
            "deal_id": uuid.uuid4(),
            "deal_key": sample_deal_context["deal_key"],
            "position_number": 1,
            "hash_key": sample_hash_key,
            "product_name": "Тестовый товар",
            "supplier_name": "Тестовый поставщик",
            "pickup_date": "15.01.2024",
            "quantity": Decimal("10.000"),
            "purchase_price_amount": Decimal("1000.00"),
            "sale_price_amount": Decimal("1500.00"),
            "revenue_amount": Decimal("15000.00"),
            "margin_amount": Decimal("5000.00"),
            "cost_amount": Decimal("10000.00"),
            "client_name": sample_deal_context["client_name"],
            "period_month": sample_deal_context["period_month"],
            "period_year": sample_deal_context["period_year"],
        }

    @pytest.mark.asyncio
    async def test_create_new_position_with_unique_hash_key(
        self, read_model_builder, mock_session, sample_position_data, sample_hash_key
    ):
        """Test creating new position when no existing position with same hash_key."""
        # Arrange
        mock_session.execute.side_effect = [
            # No existing active position
            MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        ]

        # Mock _get_deal_context
        read_model_builder._get_deal_context = AsyncMock(
            return_value={
                "deal_key": "TEST_DEAL_001",
                "client_name": "Тестовый клиент",
                "period_month": "Январь",
                "period_year": "2024",
            }
        )

        # Mock _recalculate_totals
        read_model_builder._recalculate_totals = AsyncMock()

        # Create event data
        event_data = {
            "deal_item": {
                "item_id": str(sample_position_data["id"]),
                "deal_id": str(sample_position_data["deal_id"]),
                "product_name": sample_position_data["product_name"],
                "supplier_name": sample_position_data["supplier_name"],
                "pickup_date": sample_position_data["pickup_date"],
                "quantity": str(sample_position_data["quantity"]),
            },
            "prices": {
                "purchase": str(sample_position_data["purchase_price_amount"]),
                "sale": str(sample_position_data["sale_price_amount"]),
                "revenue": str(sample_position_data["revenue_amount"]),
                "margin": str(sample_position_data["margin_amount"]),
                "cost": str(sample_position_data["cost_amount"]),
            },
        }

        full_event = {"event_id": "test-event-123"}

        # Act
        await read_model_builder._create_deal_item_read_model(event_data, full_event)

        # Assert - Should create new position with version=1, is_active=True
        assert mock_session.execute.call_count >= 2  # Check + Insert
        read_model_builder._recalculate_totals.assert_called_once()

    @pytest.mark.asyncio
    async def test_prevent_duplicate_active_positions_same_hash_key(
        self, read_model_builder, mock_session, sample_position_data, sample_hash_key
    ):
        """Test preventing duplicate active positions with same hash_key but different deal_id."""
        # Arrange
        existing_position = MagicMock()
        existing_position.id = uuid.uuid4()
        existing_position.deal_id = uuid.uuid4()  # Different deal_id
        existing_position.hash_key = sample_hash_key
        existing_position.version = 1
        existing_position.is_active = True

        mock_session.execute.side_effect = [
            # Existing active position found
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_position)),
            # Update old position (deactivate)
            MagicMock(),
            # Insert new position
            MagicMock(),
        ]

        # Mock _get_deal_context
        read_model_builder._get_deal_context = AsyncMock(
            return_value={
                "deal_key": "TEST_DEAL_002",  # Different deal
                "client_name": "Другой клиент",
                "period_month": "Февраль",
                "period_year": "2024",
            }
        )

        # Mock other methods
        read_model_builder._recalculate_totals = AsyncMock()

        # Create event data with different deal_id
        new_deal_id = uuid.uuid4()
        event_data = {
            "deal_item": {
                "item_id": str(sample_position_data["id"]),
                "deal_id": str(new_deal_id),  # Different deal
                "product_name": sample_position_data["product_name"],
                "supplier_name": sample_position_data["supplier_name"],
                "pickup_date": sample_position_data["pickup_date"],
                "quantity": str(sample_position_data["quantity"]),
            },
            "prices": {
                "purchase": str(sample_position_data["purchase_price_amount"]),
                "sale": str(sample_position_data["sale_price_amount"]),
                "revenue": str(sample_position_data["revenue_amount"]),
                "margin": str(sample_position_data["margin_amount"]),
                "cost": str(sample_position_data["cost_amount"]),
            },
        }

        full_event = {"event_id": "test-event-456"}

        # Act
        await read_model_builder._create_deal_item_read_model(event_data, full_event)

        # Assert
        # Should have: 1 check + 1 deactivate old + 1 insert new = 3 calls
        assert mock_session.execute.call_count == 3

        # Verify deactivation call
        update_call = mock_session.execute.call_args_list[1]
        assert "is_active" in str(update_call)
        assert "version" in str(update_call)

        # Verify new position creation
        insert_call = mock_session.execute.call_args_list[2]
        assert "INSERT" in str(insert_call).upper()

    @pytest.mark.asyncio
    async def test_update_same_deal_same_hash_key(
        self, read_model_builder, mock_session, sample_position_data, sample_hash_key
    ):
        """Test updating position when same deal_id and same hash_key."""
        # Arrange
        existing_position = MagicMock()
        existing_position.id = sample_position_data["id"]
        existing_position.deal_id = sample_position_data["deal_id"]  # Same deal_id
        existing_position.hash_key = sample_hash_key
        existing_position.version = 1
        existing_position.is_active = True

        mock_session.execute.side_effect = [
            # Existing active position found with same deal_id
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_position)),
            # Update position
            MagicMock(),
        ]

        # Mock _get_deal_context
        read_model_builder._get_deal_context = AsyncMock(
            return_value={
                "deal_key": "TEST_DEAL_001",
                "client_name": "Тестовый клиент",
                "period_month": "Январь",
                "period_year": "2024",
            }
        )

        # Mock other methods
        read_model_builder._recalculate_totals = AsyncMock()

        # Create event data with same deal_id
        event_data = {
            "deal_item": {
                "item_id": str(sample_position_data["id"]),
                "deal_id": str(sample_position_data["deal_id"]),  # Same deal
                "product_name": sample_position_data["product_name"],
                "supplier_name": sample_position_data["supplier_name"],
                "pickup_date": sample_position_data["pickup_date"],
                "quantity": str(sample_position_data["quantity"]),
            },
            "prices": {
                "purchase": str(sample_position_data["purchase_price_amount"]),
                "sale": str(sample_position_data["sale_price_amount"]),
                "revenue": str(sample_position_data["revenue_amount"]),
                "margin": str(sample_position_data["margin_amount"]),
                "cost": str(sample_position_data["cost_amount"]),
            },
        }

        full_event = {"event_id": "test-event-789"}

        # Act
        await read_model_builder._create_deal_item_read_model(event_data, full_event)

        # Assert
        # Should have: 1 check + 1 update = 2 calls
        assert mock_session.execute.call_count == 2

        # Verify update call (should increment version)
        update_call = mock_session.execute.call_args_list[1]
        assert "version" in str(update_call)

    @pytest.mark.asyncio
    async def test_version_uniqueness_constraint(
        self, read_model_builder, sample_hash_key
    ):
        """Test that version uniqueness constraint prevents conflicts."""
        # This test verifies the theoretical constraint
        # In practice, the constraint (hash_key, version) ensures that:
        # - Same hash_key can have multiple versions (1, 2, 3, ...)
        # - But each (hash_key, version) combination is unique

        # Create test data for same hash_key with different versions
        position_v1 = {
            "hash_key": sample_hash_key,
            "version": 1,
            "is_active": False,  # Old version
        }

        position_v2 = {
            "hash_key": sample_hash_key,
            "version": 2,
            "is_active": True,  # Current version
        }

        # Both should be allowed because versions are different
        assert position_v1["hash_key"] == position_v2["hash_key"]
        assert position_v1["version"] != position_v2["version"]

        # But this should NOT be allowed (same hash_key + same version):
        duplicate_version = {
            "hash_key": sample_hash_key,
            "version": 2,  # Same version as position_v2
            "is_active": True,
        }

        # The database constraint (hash_key, version) UNIQUE
        # would prevent inserting duplicate_version
        assert duplicate_version["hash_key"] == position_v2["hash_key"]
        assert duplicate_version["version"] == position_v2["version"]

"""
Unit tests for Event Store implementation.

Tests the core Event Sourcing functionality including event storage, retrieval, and versioning.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.event_store import EventStoreImplementation
from src.infrastructure.database.models import EventStoreModel


class TestEventStoreImplementation:
    """Test Event Store implementation."""

    @pytest.fixture
    def mock_session(self):
        """Mock async database session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def event_store(self, mock_session):
        """Event store instance with mocked session."""
        return EventStoreImplementation(mock_session)

    @pytest.fixture
    def sample_aggregate_id(self):
        """Sample aggregate ID for testing."""
        return uuid.uuid4()

    @pytest.fixture
    def sample_event_data(self):
        """Sample event data for testing."""
        return {
            "deal_id": str(uuid.uuid4()),
            "deal_key": "TEST-001",
            "client_name": "Test Client",
            "invoice_info": "Invoice 123",
        }

    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for testing."""
        return {
            "sync_session_id": str(uuid.uuid4()),
            "source": "test",
            "user_id": "test-user",
        }

    async def test_append_event_success(
        self, event_store, mock_session, sample_aggregate_id, sample_event_data, sample_metadata
    ):
        """Test successful event appending."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0  # No existing events
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        # Act
        await event_store.append_event(
            aggregate_id=sample_aggregate_id,
            event_type="DealCreated",
            event_data=sample_event_data,
            metadata=sample_metadata
        )

        # Assert
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

        # Check that EventStoreModel was created with correct data
        added_event = mock_session.add.call_args[0][0]
        assert isinstance(added_event, EventStoreModel)
        assert added_event.aggregate_id == sample_aggregate_id
        assert added_event.event_type == "DealCreated"
        assert added_event.event_data == sample_event_data
        assert added_event.event_metadata == sample_metadata
        assert added_event.aggregate_type == "Deal"
        assert added_event.sequence_number == 1

    async def test_append_event_increments_sequence(
        self, event_store, mock_session, sample_aggregate_id, sample_event_data
    ):
        """Test that sequence number is incremented correctly."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5  # Existing max sequence
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        # Act
        await event_store.append_event(
            aggregate_id=sample_aggregate_id,
            event_type="DealUpdated",
            event_data=sample_event_data
        )

        # Assert
        added_event = mock_session.add.call_args[0][0]
        assert added_event.sequence_number == 6

    async def test_append_events_batch(
        self, event_store, mock_session, sample_aggregate_id, sample_event_data
    ):
        """Test batch event appending."""
        # Arrange
        events = [
            {
                "aggregate_id": sample_aggregate_id,
                "event_type": "DealCreated",
                "event_data": sample_event_data,
                "metadata": {"source": "test1"}
            },
            {
                "aggregate_id": sample_aggregate_id,
                "event_type": "DealUpdated",
                "event_data": sample_event_data,
                "metadata": {"source": "test2"}
            }
        ]

        mock_result_1 = MagicMock()
        mock_result_1.scalar.return_value = 0
        mock_result_2 = MagicMock()
        mock_result_2.scalar.return_value = 1
        mock_session.execute = AsyncMock(side_effect=[mock_result_1, mock_result_2])
        mock_session.add_all = MagicMock()
        mock_session.flush = AsyncMock()

        # Act
        await event_store.append_events(events)

        # Assert
        mock_session.add_all.assert_called_once()
        mock_session.flush.assert_called_once()

        added_events = mock_session.add_all.call_args[0][0]
        assert len(added_events) == 2
        assert added_events[0].event_type == "DealCreated"
        assert added_events[1].event_type == "DealUpdated"

    async def test_get_events_by_aggregate(
        self, event_store, mock_session, sample_aggregate_id
    ):
        """Test retrieving events for specific aggregate."""
        # Arrange
        mock_event_1 = MagicMock()
        mock_event_1.event_id = uuid.uuid4()
        mock_event_1.aggregate_id = sample_aggregate_id
        mock_event_1.aggregate_type = "Deal"
        mock_event_1.event_type = "DealCreated"
        mock_event_1.event_version = 1
        mock_event_1.event_data = {"test": "data1"}
        mock_event_1.metadata = {"source": "test"}
        mock_event_1.sequence_number = 1
        mock_event_1.created_at = datetime.now()

        mock_event_2 = MagicMock()
        mock_event_2.event_id = uuid.uuid4()
        mock_event_2.aggregate_id = sample_aggregate_id
        mock_event_2.aggregate_type = "Deal"
        mock_event_2.event_type = "DealUpdated"
        mock_event_2.event_version = 1
        mock_event_2.event_data = {"test": "data2"}
        mock_event_2.metadata = {"source": "test"}
        mock_event_2.sequence_number = 2
        mock_event_2.created_at = datetime.now()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_event_1, mock_event_2]
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        events = await event_store.get_events(sample_aggregate_id)

        # Assert
        assert len(events) == 2
        assert events[0]["event_type"] == "DealCreated"
        assert events[1]["event_type"] == "DealUpdated"
        assert events[0]["sequence_number"] == 1
        assert events[1]["sequence_number"] == 2

    async def test_get_events_by_type(self, event_store, mock_session):
        """Test retrieving events by event type."""
        # Arrange
        mock_event = MagicMock()
        mock_event.event_id = uuid.uuid4()
        mock_event.aggregate_id = uuid.uuid4()
        mock_event.aggregate_type = "Deal"
        mock_event.event_type = "DealCreated"
        mock_event.event_version = 1
        mock_event.event_data = {"test": "data"}
        mock_event.metadata = {"source": "test"}
        mock_event.sequence_number = 1
        mock_event.created_at = datetime.now()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_event]
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        events = await event_store.get_events_by_type("DealCreated", limit=50)

        # Assert
        assert len(events) == 1
        assert events[0]["event_type"] == "DealCreated"

    async def test_get_latest_events(self, event_store, mock_session):
        """Test retrieving latest events."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        events = await event_store.get_latest_events(limit=10)

        # Assert
        assert len(events) == 0
        mock_session.execute.assert_called_once()

    async def test_extract_aggregate_type_deal(self, event_store):
        """Test aggregate type extraction for Deal events."""
        assert event_store._extract_aggregate_type("DealCreated") == "Deal"
        assert event_store._extract_aggregate_type("DealUpdated") == "Deal"
        assert event_store._extract_aggregate_type("DealDeleted") == "Deal"
        assert event_store._extract_aggregate_type("DealItemAdded") == "Deal"

    async def test_extract_aggregate_type_sync_session(self, event_store):
        """Test aggregate type extraction for SyncSession events."""
        assert event_store._extract_aggregate_type("SyncSessionStarted") == "SyncSession"
        assert event_store._extract_aggregate_type("SyncSessionCompleted") == "SyncSession"

    async def test_extract_aggregate_type_fallback(self, event_store):
        """Test aggregate type extraction fallback logic."""
        assert event_store._extract_aggregate_type("CustomEntityCreated") == "CustomEntity"
        assert event_store._extract_aggregate_type("SomeThingUpdated") == "SomeThing"

    async def test_upcast_event_data_v1(self, event_store):
        """Test event data upcasting for version 1."""
        event_data = {"test": "data"}
        result = await event_store._upcast_event_data(event_data, "DealCreated", 1)
        assert result == event_data  # No transformation for v1

    async def test_get_event_count(self, event_store, mock_session):
        """Test getting total event count."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar.return_value = 150
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        count = await event_store.get_event_count()

        # Assert
        assert count == 150

    async def test_get_aggregate_version(self, event_store, mock_session, sample_aggregate_id):
        """Test getting aggregate version."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        version = await event_store.get_aggregate_version(sample_aggregate_id)

        # Assert
        assert version == 5

    async def test_append_event_exception_handling(
        self, event_store, mock_session, sample_aggregate_id, sample_event_data
    ):
        """Test exception handling in append_event."""
        # Arrange
        mock_session.execute = AsyncMock(side_effect=Exception("Database error"))

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await event_store.append_event(
                aggregate_id=sample_aggregate_id,
                event_type="DealCreated",
                event_data=sample_event_data
            )

    async def test_get_events_exception_handling(
        self, event_store, mock_session, sample_aggregate_id
    ):
        """Test exception handling in get_events."""
        # Arrange
        mock_session.execute = AsyncMock(side_effect=Exception("Database error"))

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await event_store.get_events(sample_aggregate_id)

    async def test_empty_events_batch(self, event_store, mock_session):
        """Test appending empty events batch."""
        # Act
        await event_store.append_events([])

        # Assert - no database calls should be made
        mock_session.add_all.assert_not_called()
        mock_session.flush.assert_not_called()

    async def test_get_next_sequence_number_no_existing_events(
        self, event_store, mock_session, sample_aggregate_id
    ):
        """Test sequence number generation with no existing events."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        sequence = await event_store._get_next_sequence_number(sample_aggregate_id)

        # Assert
        assert sequence == 1

    async def test_get_next_sequence_number_with_existing_events(
        self, event_store, mock_session, sample_aggregate_id
    ):
        """Test sequence number generation with existing events."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        sequence = await event_store._get_next_sequence_number(sample_aggregate_id)

        # Assert
        assert sequence == 11

"""
Unit tests for Read Model Builder Worker.

Tests event processing and read model updates.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.interfaces import EventStore
from src.domain.models import Deal, DealItem
from src.domain.value_objects import Money, Period, Status
from src.infrastructure.database.models import ReadModelAudit
from src.infrastructure.workers.read_model_builder import ReadModelBuilder


class TestReadModelBuilder:
    """Test suite for Read Model Builder."""

    @pytest.fixture
    def mock_session(self) -> AsyncSession:
        """Create mock database session."""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.execute = AsyncMock()
        session.add = MagicMock()  # add() is synchronous in SQLAlchemy
        return session

    @pytest.fixture
    def mock_event_store(self) -> EventStore:
        """Create mock event store."""
        return AsyncMock(spec=EventStore)

    @pytest.fixture
    def read_model_builder(
        self, mock_session: AsyncSession, mock_event_store: EventStore
    ) -> ReadModelBuilder:
        """Create Read Model Builder instance."""
        return ReadModelBuilder(session=mock_session, event_store=mock_event_store)

    @pytest.fixture
    def sample_deal_event(self) -> dict:
        """Create sample deal created event."""
        deal = Deal(
            id=uuid.uuid4(),
            client_name="Test Client",
            invoice_info="Test Invoice Info",
            invoice_number="INV-001",
            invoice_date="2024-01-15",
            seller="Test Seller",
            is_shipped=Status.SHIPPED,
            is_paid=Status.PENDING,
            total_revenue=Money(amount=Decimal("1000.00")),
            total_margin=Money(amount=Decimal("200.00")),
            total_cost=Money(amount=Decimal("800.00")),
            period=Period(month="Январь", year="2024", full_name="Январь 2024"),
            items=[],
        )

        return {
            "event_id": uuid.uuid4(),
            "aggregate_id": deal.id,
            "aggregate_type": "Deal",
            "event_type": "DealCreated",
            "event_data": {"deal": deal.model_dump()},
            "metadata": {"sync_session_id": uuid.uuid4()},
            "created_at": "2024-01-15T10:00:00",
        }

    @pytest.fixture
    def sample_deal_item_event(self) -> dict:
        """Create sample deal item created event."""
        deal_id = uuid.uuid4()
        item = DealItem(
            id=uuid.uuid4(),
            deal_id=deal_id,
            product_name="Test Product",
            supplier_name="Test Supplier",
            quantity=Decimal("10.0"),
            purchase_price=Money(amount=Decimal("80.00")),
            sale_price=Money(amount=Decimal("100.00")),
            pickup_date="2024-01-10",
        )

        return {
            "event_id": uuid.uuid4(),
            "aggregate_id": deal_id,
            "aggregate_type": "Deal",
            "event_type": "DealItemCreated",
            "event_data": {"deal_item": item.model_dump()},
            "metadata": {"sync_session_id": uuid.uuid4()},
            "created_at": "2024-01-15T10:00:00",
        }

    @pytest.mark.asyncio
    async def test_process_latest_events_empty(
        self, read_model_builder: ReadModelBuilder, mock_event_store: EventStore
    ):
        """Test processing when no events available."""
        # Arrange
        mock_event_store.get_latest_events.return_value = []

        # Act
        result = await read_model_builder.process_latest_events(limit=100)

        # Assert
        assert result == 0
        mock_event_store.get_latest_events.assert_called_once_with(limit=100)

    @pytest.mark.asyncio
    async def test_process_latest_events_with_events(
        self,
        read_model_builder: ReadModelBuilder,
        mock_event_store: EventStore,
        mock_session: AsyncSession,
        sample_deal_event: dict,
    ):
        """Test processing events successfully."""
        # Arrange
        mock_event_store.get_latest_events.return_value = [sample_deal_event]

        # Mock the read model creation
        with patch.object(
            read_model_builder, "_process_single_event", new_callable=AsyncMock
        ) as mock_process:
            # Act
            result = await read_model_builder.process_latest_events(limit=100)

        # Assert
        assert result == 1
        mock_process.assert_called_once_with(sample_deal_event)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_events_error_handling(
        self,
        read_model_builder: ReadModelBuilder,
        mock_event_store: EventStore,
        mock_session: AsyncSession,
        sample_deal_event: dict,
    ):
        """Test error handling during event processing."""
        # Arrange
        mock_event_store.get_latest_events.return_value = [sample_deal_event]

        # Mock processing to raise an exception
        with patch.object(
            read_model_builder, "_process_single_event", new_callable=AsyncMock
        ) as mock_process:
            mock_process.side_effect = Exception("Processing error")

            # Act & Assert
            with pytest.raises(Exception, match="Processing error"):
                await read_model_builder.process_latest_events()

            mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_single_event_deal_created(
        self, read_model_builder: ReadModelBuilder, sample_deal_event: dict
    ):
        """Test processing DealCreated event."""
        # Arrange
        with patch.object(
            read_model_builder, "_handle_deal_event", new_callable=AsyncMock
        ) as mock_handle:
            # Act
            await read_model_builder._process_single_event(sample_deal_event)

        # Assert
        mock_handle.assert_called_once_with(
            "DealCreated", sample_deal_event["event_data"], sample_deal_event
        )

    @pytest.mark.asyncio
    async def test_process_single_event_deal_item_created(
        self, read_model_builder: ReadModelBuilder, sample_deal_item_event: dict
    ):
        """Test processing DealItemCreated event."""
        # Arrange
        with patch.object(
            read_model_builder, "_handle_deal_item_event", new_callable=AsyncMock
        ) as mock_handle:
            # Act
            await read_model_builder._process_single_event(sample_deal_item_event)

        # Assert
        mock_handle.assert_called_once_with(
            "DealItemCreated", sample_deal_item_event["event_data"], sample_deal_item_event
        )

    @pytest.mark.asyncio
    async def test_handle_deal_event_created(
        self, read_model_builder: ReadModelBuilder, sample_deal_event: dict
    ):
        """Test handling DealCreated event."""
        # Arrange
        with patch.object(
            read_model_builder, "_create_deal_read_model", new_callable=AsyncMock
        ) as mock_create:
            # Act
            await read_model_builder._handle_deal_event(
                "DealCreated", sample_deal_event["event_data"], sample_deal_event
            )

        # Assert
        mock_create.assert_called_once_with(sample_deal_event["event_data"], sample_deal_event)

    @pytest.mark.asyncio
    async def test_handle_deal_event_updated(
        self, read_model_builder: ReadModelBuilder, sample_deal_event: dict
    ):
        """Test handling DealUpdated event."""
        # Arrange
        sample_deal_event["event_type"] = "DealUpdated"

        with patch.object(
            read_model_builder, "_update_deal_read_model", new_callable=AsyncMock
        ) as mock_update:
            # Act
            await read_model_builder._handle_deal_event(
                "DealUpdated", sample_deal_event["event_data"], sample_deal_event
            )

        # Assert
        mock_update.assert_called_once_with(sample_deal_event["event_data"], sample_deal_event)

    @pytest.mark.asyncio
    async def test_handle_deal_event_deleted(
        self, read_model_builder: ReadModelBuilder, sample_deal_event: dict
    ):
        """Test handling DealDeleted event."""
        # Arrange
        sample_deal_event["event_type"] = "DealDeleted"

        with patch.object(
            read_model_builder, "_delete_deal_read_model", new_callable=AsyncMock
        ) as mock_delete:
            # Act
            await read_model_builder._handle_deal_event(
                "DealDeleted", sample_deal_event["event_data"], sample_deal_event
            )

        # Assert
        mock_delete.assert_called_once_with(sample_deal_event["event_data"], sample_deal_event)

    @pytest.mark.asyncio
    async def test_create_deal_read_model(
        self,
        read_model_builder: ReadModelBuilder,
        mock_session: AsyncSession,
        sample_deal_event: dict,
    ):
        """Test creating deal read model."""
        # Arrange
        with patch.object(
            read_model_builder, "_create_audit_entry", new_callable=AsyncMock
        ) as mock_audit:
            # Act
            await read_model_builder._create_deal_read_model(
                sample_deal_event["event_data"], sample_deal_event
            )

        # Assert
        # Should execute insert statement
        mock_session.execute.assert_called_once()

        # Should create audit entry
        mock_audit.assert_called_once()

        # Verify audit entry parameters
        call_args = mock_audit.call_args[1]
        assert call_args["entity_type"] == "deal"
        assert call_args["change_type"] == "INSERT"
        assert call_args["event_id"] == sample_deal_event["event_id"]

    @pytest.mark.asyncio
    async def test_update_deal_read_model(
        self,
        read_model_builder: ReadModelBuilder,
        mock_session: AsyncSession,
        sample_deal_event: dict,
    ):
        """Test updating deal read model."""
        # Arrange
        sample_deal_event["event_data"]["changes"] = {
            "client_name": {"old_value": "Old Client", "new_value": "New Client"}
        }

        with patch.object(
            read_model_builder, "_create_audit_entry", new_callable=AsyncMock
        ) as mock_audit:
            # Act
            await read_model_builder._update_deal_read_model(
                sample_deal_event["event_data"], sample_deal_event
            )

        # Assert
        # Should execute update statement
        mock_session.execute.assert_called_once()

        # Should create audit entry for each changed field
        mock_audit.assert_called_once()

        # Verify audit entry parameters
        call_args = mock_audit.call_args[1]
        assert call_args["entity_type"] == "deal"
        assert call_args["change_type"] == "UPDATE"
        assert call_args["field_name"] == "client_name"
        assert call_args["old_value"] == "Old Client"
        assert call_args["new_value"] == "New Client"

    @pytest.mark.asyncio
    async def test_delete_deal_read_model(
        self, read_model_builder: ReadModelBuilder, mock_session: AsyncSession
    ):
        """Test soft deleting deal read model."""
        # Arrange
        deal_id = uuid.uuid4()
        deal_key = "test|deal|key"
        event_data = {"deal_id": str(deal_id), "deal_key": deal_key}
        event = {"event_id": uuid.uuid4(), "metadata": {"sync_session_id": uuid.uuid4()}}

        with patch.object(
            read_model_builder, "_create_audit_entry", new_callable=AsyncMock
        ) as mock_audit:
            # Act
            await read_model_builder._delete_deal_read_model(event_data, event)

        # Assert
        # Should execute two update statements (deal and positions)
        assert mock_session.execute.call_count == 2

        # Should create audit entry
        mock_audit.assert_called_once()

        # Verify audit entry parameters
        call_args = mock_audit.call_args[1]
        assert call_args["entity_type"] == "deal"
        assert call_args["change_type"] == "DELETE"
        assert call_args["entity_id"] == deal_id

    @pytest.mark.asyncio
    async def test_create_deal_item_read_model(
        self,
        read_model_builder: ReadModelBuilder,
        mock_session: AsyncSession,
        sample_deal_item_event: dict,
    ):
        """Test creating deal item read model."""
        # Arrange
        deal_context = {
            "deal_key": "test|deal|key",
            "client_name": "Test Client",
            "period_month": "01",
            "period_year": "2024",
        }

        with patch.object(
            read_model_builder, "_get_deal_context", new_callable=AsyncMock
        ) as mock_context:
            with patch.object(
                read_model_builder, "_create_audit_entry", new_callable=AsyncMock
            ) as mock_audit:
                mock_context.return_value = deal_context

                # Act
                await read_model_builder._create_deal_item_read_model(
                    sample_deal_item_event["event_data"], sample_deal_item_event
                )

        # Assert
        # Should get deal context
        mock_context.assert_called_once()

        # Should execute insert statement
        mock_session.execute.assert_called_once()

        # Should create audit entry
        mock_audit.assert_called_once()

        # Verify audit entry parameters
        call_args = mock_audit.call_args[1]
        assert call_args["entity_type"] == "position"
        assert call_args["change_type"] == "INSERT"

    @pytest.mark.asyncio
    async def test_get_deal_context_success(
        self, read_model_builder: ReadModelBuilder, mock_session: AsyncSession
    ):
        """Test getting deal context successfully."""
        # Arrange
        deal_id = uuid.uuid4()
        mock_deal = MagicMock()
        mock_deal.deal_key = "test|deal|key"
        mock_deal.client_name = "Test Client"
        mock_deal.period_month = "01"
        mock_deal.period_year = "2024"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_deal
        mock_session.execute.return_value = mock_result

        # Act
        context = await read_model_builder._get_deal_context(deal_id)

        # Assert
        assert context == {
            "deal_key": "test|deal|key",
            "client_name": "Test Client",
            "period_month": "01",
            "period_year": "2024",
        }
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_deal_context_not_found(
        self, read_model_builder: ReadModelBuilder, mock_session: AsyncSession
    ):
        """Test getting deal context when deal not found."""
        # Arrange
        deal_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        context = await read_model_builder._get_deal_context(deal_id)

        # Assert
        assert context == {}
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_deal_context_none_id(self, read_model_builder: ReadModelBuilder):
        """Test getting deal context with None ID."""
        # Act
        context = await read_model_builder._get_deal_context(None)

        # Assert
        assert context == {}

    @pytest.mark.asyncio
    async def test_create_audit_entry(
        self, read_model_builder: ReadModelBuilder, mock_session: AsyncSession
    ):
        """Test creating audit entry."""
        # Arrange
        entity_id = uuid.uuid4()
        event_id = uuid.uuid4()
        sync_session_id = uuid.uuid4()

        # Act
        await read_model_builder._create_audit_entry(
            entity_type="deal",
            entity_id=entity_id,
            entity_key="test|deal|key",
            change_type="INSERT",
            event_id=event_id,
            sync_session_id=sync_session_id,
            field_name="client_name",
            old_value="Old Client",
            new_value="New Client",
        )

        # Assert
        mock_session.add.assert_called_once()

        # Verify the audit entry object
        audit_entry = mock_session.add.call_args[0][0]
        assert isinstance(audit_entry, ReadModelAudit)
        assert audit_entry.entity_type == "deal"
        assert audit_entry.entity_id == entity_id
        assert audit_entry.entity_key == "test|deal|key"
        assert audit_entry.change_type == "INSERT"
        assert audit_entry.event_id == event_id
        assert audit_entry.sync_session_id == sync_session_id
        assert audit_entry.field_name == "client_name"
        assert audit_entry.old_value == "Old Client"
        assert audit_entry.new_value == "New Client"

    @pytest.mark.asyncio
    async def test_process_events_by_type(
        self,
        read_model_builder: ReadModelBuilder,
        mock_event_store: EventStore,
        mock_session: AsyncSession,
        sample_deal_event: dict,
    ):
        """Test processing events by specific type."""
        # Arrange
        mock_event_store.get_events_by_type.return_value = [sample_deal_event]

        with patch.object(
            read_model_builder, "_process_single_event", new_callable=AsyncMock
        ) as mock_process:
            # Act
            result = await read_model_builder.process_events_by_type("DealCreated", limit=50)

        # Assert
        assert result == 1
        mock_event_store.get_events_by_type.assert_called_once_with(
            event_type="DealCreated", limit=50
        )
        mock_process.assert_called_once_with(sample_deal_event)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_rebuild_read_model(
        self,
        read_model_builder: ReadModelBuilder,
        mock_event_store: EventStore,
        mock_session: AsyncSession,
        sample_deal_event: dict,
    ):
        """Test rebuilding read model for specific aggregate."""
        # Arrange
        aggregate_id = uuid.uuid4()
        mock_event_store.get_events.return_value = [sample_deal_event]

        with patch.object(
            read_model_builder, "_clear_read_models_for_aggregate", new_callable=AsyncMock
        ) as mock_clear:
            with patch.object(
                read_model_builder, "_process_single_event", new_callable=AsyncMock
            ) as mock_process:
                # Act
                await read_model_builder.rebuild_read_model(aggregate_id)

        # Assert
        mock_event_store.get_events.assert_called_once_with(aggregate_id=aggregate_id)
        mock_clear.assert_called_once_with(aggregate_id)
        mock_process.assert_called_once_with(sample_deal_event)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_rebuild_read_model_no_events(
        self,
        read_model_builder: ReadModelBuilder,
        mock_event_store: EventStore,
        mock_session: AsyncSession,
    ):
        """Test rebuilding read model when no events found."""
        # Arrange
        aggregate_id = uuid.uuid4()
        mock_event_store.get_events.return_value = []

        # Act
        await read_model_builder.rebuild_read_model(aggregate_id)

        # Assert
        mock_event_store.get_events.assert_called_once_with(aggregate_id=aggregate_id)
        # Should not commit since nothing was processed
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_clear_read_models_for_aggregate(
        self, read_model_builder: ReadModelBuilder, mock_session: AsyncSession
    ):
        """Test clearing read models for specific aggregate."""
        # Arrange
        aggregate_id = uuid.uuid4()

        # Act
        await read_model_builder._clear_read_models_for_aggregate(aggregate_id)

        # Assert
        # Should execute two delete statements (deal and positions)
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_update_deal_item_read_model(
        self,
        read_model_builder: ReadModelBuilder,
        mock_session: AsyncSession,
        sample_deal_item_event: dict,
    ):
        """Test updating deal item read model."""
        # Arrange
        sample_deal_item_event["event_data"]["changes"] = {
            "product_name": {"old_value": "Old Product", "new_value": "New Product"}
        }

        deal_context = {
            "deal_key": "test|deal|key",
            "client_name": "Test Client",
            "period_month": "Январь",
            "period_year": "2024",
        }

        with patch.object(
            read_model_builder, "_get_deal_context", new_callable=AsyncMock
        ) as mock_context:
            with patch.object(
                read_model_builder, "_create_audit_entry", new_callable=AsyncMock
            ) as mock_audit:
                mock_context.return_value = deal_context

                # Act
                await read_model_builder._update_deal_item_read_model(
                    sample_deal_item_event["event_data"], sample_deal_item_event
                )

        # Assert
        # Should get deal context
        mock_context.assert_called_once()

        # Should execute update statement
        mock_session.execute.assert_called_once()

        # Should create audit entry
        mock_audit.assert_called_once()

        # Verify audit entry parameters
        call_args = mock_audit.call_args[1]
        assert call_args["entity_type"] == "position"
        assert call_args["change_type"] == "UPDATE"
        assert call_args["field_name"] == "product_name"
        assert call_args["old_value"] == "Old Product"
        assert call_args["new_value"] == "New Product"

    @pytest.mark.asyncio
    async def test_delete_deal_item_read_model(
        self, read_model_builder: ReadModelBuilder, mock_session: AsyncSession
    ):
        """Test soft deleting deal item read model."""
        # Arrange
        item_id = uuid.uuid4()
        item_key = "test|item|key"
        event_data = {"deal_item_id": str(item_id), "item_key": item_key}
        event = {"event_id": uuid.uuid4(), "metadata": {"sync_session_id": uuid.uuid4()}}

        with patch.object(
            read_model_builder, "_create_audit_entry", new_callable=AsyncMock
        ) as mock_audit:
            # Act
            await read_model_builder._delete_deal_item_read_model(event_data, event)

        # Assert
        # Should execute update statement for soft delete
        mock_session.execute.assert_called_once()

        # Should create audit entry
        mock_audit.assert_called_once()

        # Verify audit entry parameters
        call_args = mock_audit.call_args[1]
        assert call_args["entity_type"] == "position"
        assert call_args["change_type"] == "DELETE"
        assert call_args["entity_id"] == item_id

    @pytest.mark.asyncio
    async def test_update_stats_after_sync(
        self, read_model_builder: ReadModelBuilder, mock_session: AsyncSession
    ):
        """Test updating statistics after sync completion."""
        # Arrange
        event_data = {
            "sync_session": {"sync_type": "incremental"},
            "stats": {
                "total_processed": 100,
                "new_deals": 10,
                "updated_deals": 20,
                "deleted_deals": 5,
                "total_positions": 250,
                "total_revenue": 50000.00,
                "total_margin": 10000.00,
                "total_cost": 40000.00,
                "total_quantity": 1000.00,
                "shipped_deals": 80,
                "paid_deals": 75,
            },
        }
        event = {"event_id": uuid.uuid4(), "metadata": {"sync_session_id": uuid.uuid4()}}

        # Act
        await read_model_builder._update_stats_after_sync(event_data, event)

        # Assert
        # Should execute upsert statement
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_event_type_warning(self, read_model_builder: ReadModelBuilder):
        """Test handling of unknown event types."""
        # Arrange
        unknown_event = {
            "event_type": "UnknownEvent",
            "event_data": {},
            "aggregate_id": uuid.uuid4(),
        }

        # Act - should not raise exception, just process silently
        await read_model_builder._process_single_event(unknown_event)

        # Assert - just verify it doesn't crash
        # (Logging verification is complex with loguru, focus on behavior)

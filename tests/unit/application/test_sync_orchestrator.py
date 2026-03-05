"""
Unit tests for Sync Orchestrator Service.

Tests the main synchronization orchestration logic including session management,
phase coordination, and error handling.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from domain.models import SyncSession, SyncType
from src.application.change_detector import ChangeDetectorService
from src.application.excel_parser import ExcelParserService
from src.application.sync_orchestrator import SyncOrchestratorService
from src.application.sync_orchestrator.models import SyncConfiguration, SyncResult
from src.domain.interfaces import EventStore, SyncSessionRepository
from src.domain.value_objects import Status


@pytest.mark.unit
class TestSyncOrchestratorService:
    """Test Sync Orchestrator Service."""

    @pytest.fixture
    def mock_excel_parser(self):
        """Mock Excel parser service."""
        return AsyncMock(spec=ExcelParserService)

    @pytest.fixture
    def mock_change_detector(self):
        """Mock change detector service."""
        return AsyncMock(spec=ChangeDetectorService)

    @pytest.fixture
    def mock_event_store(self):
        """Mock event store."""
        return AsyncMock(spec=EventStore)

    @pytest.fixture
    def mock_sync_session_repository(self):
        """Mock sync session repository."""
        return AsyncMock(spec=SyncSessionRepository)

    @pytest.fixture
    def orchestrator(
        self,
        mock_excel_parser,
        mock_change_detector,
        mock_event_store,
        mock_sync_session_repository,
    ):
        """Sync orchestrator service instance."""
        return SyncOrchestratorService(
            excel_parser=mock_excel_parser,
            change_detector=mock_change_detector,
            event_store=mock_event_store,
            sync_session_repository=mock_sync_session_repository,
        )

    @pytest.fixture
    def full_sync_config(self):
        """Full synchronization configuration."""
        return SyncConfiguration(
            sync_type="full",
            incremental_period_months=3,
            batch_size=100,
            create_events=True,
            update_read_models=True,
            continue_on_errors=True,
            rollback_on_failure=True,
        )

    @pytest.fixture
    def incremental_sync_config(self):
        """Incremental synchronization configuration."""
        return SyncConfiguration(
            sync_type="incremental",
            incremental_period_months=3,
            batch_size=50,
            create_events=True,
            update_read_models=True,
            continue_on_errors=True,
            rollback_on_failure=False,
        )

    @pytest.fixture
    def sample_parse_result(self):
        """Sample parse result for testing."""
        from src.application.excel_parser.models import ParseResult, ParseStats
        from src.domain.models import SyncSession, SyncType

        # Create real SyncSession object
        sync_session = SyncSession(sync_type=SyncType.FULL)
        sync_session.source_file_path = "test.xlsx"

        stats = ParseStats(total_deals=10, processed_deals=10, total_items=25, processed_items=25)

        return ParseResult(
            deals=[],  # Empty for simplicity
            stats=stats,
            sync_session=sync_session,
            file_path="test.xlsx",
            file_size=1024,
            file_hash="abc123",
        )

    @pytest.fixture
    def sample_change_result(self):
        """Sample change detection result for testing."""
        from src.application.change_detector.models import ChangeDetectionResult

        return ChangeDetectionResult(
            total_excel_deals=10,
            total_db_deals=8,
            total_excel_items=25,
            total_db_items=20,
            comparison_duration_seconds=0.5,
            hash_comparison_count=35,
            detailed_comparison_count=5,
        )

    async def test_execute_sync_full_success(
        self,
        orchestrator,
        mock_excel_parser,
        mock_event_store,
        mock_sync_session_repository,
        full_sync_config,
        sample_parse_result,
    ):
        """Test successful full synchronization."""
        # Arrange
        file_path = "test.xlsx"
        mock_sync_session_repository.get_running_session.return_value = None
        mock_excel_parser.parse_file.return_value = sample_parse_result

        # Act
        result = await orchestrator.execute_sync(file_path, full_sync_config)

        # Assert
        assert isinstance(result, SyncResult)
        assert result.summary.success is True
        assert result.summary.total_deals_processed == 0  # Empty deals list
        assert result.summary.total_items_processed == 0  # Empty deals list
        assert result.summary.insertions_count == 0  # No deals to insert
        assert result.summary.updates_count == 0
        assert result.summary.deletions_count == 0
        assert result.parse_result == sample_parse_result

        # Verify session lifecycle
        mock_sync_session_repository.save.assert_called()
        mock_excel_parser.parse_file.assert_called_once()

    async def test_execute_sync_incremental_success(
        self,
        orchestrator,
        mock_excel_parser,
        mock_change_detector,
        mock_event_store,
        mock_sync_session_repository,
        incremental_sync_config,
        sample_parse_result,
        sample_change_result,
    ):
        """Test successful incremental synchronization."""
        # Arrange
        file_path = "test.xlsx"
        mock_sync_session_repository.get_running_session.return_value = None
        mock_excel_parser.parse_file.return_value = sample_parse_result
        mock_change_detector.detect_changes.return_value = sample_change_result

        # Act
        result = await orchestrator.execute_sync(file_path, incremental_sync_config)

        # Assert
        assert result.summary.success is True
        assert result.change_detection_result == sample_change_result
        assert result.summary.change_detection_duration_seconds >= 0  # Can be 0 for empty datasets

        # Verify change detection was called
        mock_change_detector.detect_changes.assert_called_once_with(
            sample_parse_result.deals, incremental_sync_config.incremental_period_months
        )

    async def test_execute_sync_running_session_error(
        self, orchestrator, mock_sync_session_repository, full_sync_config
    ):
        """Test error when another sync session is already running."""
        # Arrange
        file_path = "test.xlsx"
        running_session = SyncSession(sync_type=SyncType.FULL, file_path="other.xlsx")
        running_session.id = uuid.uuid4()
        mock_sync_session_repository.get_running_session.return_value = running_session

        # Act & Assert
        with pytest.raises(RuntimeError, match="Another sync session is already running"):
            await orchestrator.execute_sync(file_path, full_sync_config)

    async def test_execute_sync_parsing_error(
        self, orchestrator, mock_excel_parser, mock_sync_session_repository, full_sync_config
    ):
        """Test error handling during parsing phase."""
        # Arrange
        file_path = "test.xlsx"
        mock_sync_session_repository.get_running_session.return_value = None
        mock_excel_parser.parse_file.side_effect = Exception("Parse error")

        # Act
        result = await orchestrator.execute_sync(file_path, full_sync_config)

        # Assert
        assert result.summary.success is False
        assert result.summary.error_message is not None
        assert "Parse error" in result.summary.error_message
        assert len(result.errors) > 0

    async def test_execute_sync_continue_on_errors(
        self, orchestrator, mock_excel_parser, mock_sync_session_repository, incremental_sync_config
    ):
        """Test continuing sync when continue_on_errors is True."""
        # Arrange
        file_path = "test.xlsx"
        incremental_sync_config.continue_on_errors = True
        mock_sync_session_repository.get_running_session.return_value = None
        mock_excel_parser.parse_file.side_effect = Exception("Parse error")

        # Act - should not raise exception
        result = await orchestrator.execute_sync(file_path, incremental_sync_config)

        # Assert
        assert result.summary.success is False
        assert result.has_errors

    async def test_execute_sync_rollback_on_failure(
        self, orchestrator, mock_excel_parser, mock_sync_session_repository, full_sync_config
    ):
        """Test raising exception when rollback_on_failure is True."""
        # Arrange
        file_path = "test.xlsx"
        full_sync_config.rollback_on_failure = True
        full_sync_config.continue_on_errors = False
        mock_sync_session_repository.get_running_session.return_value = None
        mock_excel_parser.parse_file.side_effect = Exception("Critical error")

        # Act & Assert
        with pytest.raises(Exception, match="Critical error"):
            await orchestrator.execute_sync(file_path, full_sync_config)

    async def test_create_sync_session_success(
        self, orchestrator, mock_sync_session_repository, full_sync_config
    ):
        """Test successful sync session creation."""
        # Arrange
        session_id = str(uuid.uuid4())  # Valid UUID
        file_path = "test.xlsx"
        mock_sync_session_repository.get_running_session.return_value = None

        # Act
        session = await orchestrator._create_sync_session(session_id, file_path, full_sync_config)

        # Assert
        assert isinstance(session, SyncSession)
        assert session.sync_type == SyncType.FULL
        assert session.source_file_path == file_path
        assert session.is_running
        mock_sync_session_repository.save.assert_called_once_with(session)

    async def test_create_sync_session_incremental(
        self, orchestrator, mock_sync_session_repository, incremental_sync_config
    ):
        """Test incremental sync session creation."""
        # Arrange
        session_id = str(uuid.uuid4())  # Valid UUID
        file_path = "test.xlsx"
        mock_sync_session_repository.get_running_session.return_value = None

        # Act
        session = await orchestrator._create_sync_session(
            session_id, file_path, incremental_sync_config
        )

        # Assert
        assert session.sync_type == SyncType.INCREMENTAL

    async def test_complete_sync_session_success(self, orchestrator, mock_sync_session_repository):
        """Test successful sync session completion."""
        # Arrange
        sync_session = SyncSession(sync_type=SyncType.FULL)
        sync_session.source_file_path = "test.xlsx"
        sync_session.start()

        # Act
        await orchestrator._complete_sync_session(sync_session, success=True)

        # Assert
        assert sync_session.status == Status.COMPLETED
        assert sync_session.finished_at is not None
        mock_sync_session_repository.save.assert_called_once_with(sync_session)

    async def test_complete_sync_session_failure(self, orchestrator, mock_sync_session_repository):
        """Test sync session completion with failure."""
        # Arrange
        sync_session = SyncSession(sync_type=SyncType.FULL)
        sync_session.source_file_path = "test.xlsx"
        sync_session.start()
        error_message = "Sync failed"

        # Act
        await orchestrator._complete_sync_session(
            sync_session, success=False, error_message=error_message
        )

        # Assert
        assert sync_session.status == Status.FAILED
        assert error_message in sync_session.stats.errors  # Error is stored in stats.errors
        assert sync_session.finished_at is not None

    async def test_apply_changes_events_disabled(
        self, orchestrator, mock_event_store, sample_parse_result
    ):
        """Test skipping event creation when disabled."""
        # Arrange
        from src.application.sync_orchestrator.models import SyncSummary

        config = SyncConfiguration(sync_type="full", create_events=False)

        summary = SyncSummary(
            started_at=datetime.now(),
            file_path="test.xlsx",
            file_hash="abc123",
            success=True,
            total_deals_processed=0,
            total_items_processed=0,
        )

        result = SyncResult(
            sync_session_id="test",
            sync_type="full",
            summary=summary,
            parse_result=sample_parse_result,
        )

        # Act
        await orchestrator._apply_changes_to_database(result, config)

        # Assert
        mock_event_store.append_events.assert_not_called()

    async def test_apply_changes_full_sync(
        self, orchestrator, mock_event_store, sample_parse_result
    ):
        """Test applying changes for full sync."""
        # Arrange
        from src.application.sync_orchestrator.models import SyncSummary

        config = SyncConfiguration(sync_type="full", create_events=True)

        summary = SyncSummary(
            started_at=datetime.now(),
            file_path="test.xlsx",
            file_hash="abc123",
            success=True,
            total_deals_processed=0,
            total_items_processed=0,
        )

        result = SyncResult(
            sync_session_id="test",
            sync_type="full",
            summary=summary,
            parse_result=sample_parse_result,
        )

        # Mock event creation
        orchestrator._create_full_sync_events = AsyncMock(
            return_value=[
                {"event_type": "DealCreated", "aggregate_id": uuid.uuid4()},
                {"event_type": "DealItemAdded", "aggregate_id": uuid.uuid4()},
            ]
        )

        # Act
        await orchestrator._apply_changes_to_database(result, config)

        # Assert
        mock_event_store.append_events.assert_called_once()
        assert len(result.events_created) == 2

    async def test_apply_changes_incremental_sync(
        self, orchestrator, mock_event_store, sample_change_result
    ):
        """Test applying changes for incremental sync."""
        # Arrange
        from src.application.sync_orchestrator.models import SyncSummary

        config = SyncConfiguration(sync_type="incremental", create_events=True)

        # Create real SyncSummary object
        summary = SyncSummary(
            started_at=datetime.now(),
            file_path="test.xlsx",
            file_hash="abc123",
            success=True,
            total_deals_processed=10,
            total_items_processed=25,
        )

        result = SyncResult(
            sync_session_id="test",
            sync_type="incremental",
            summary=summary,
            change_detection_result=sample_change_result,
        )

        # Mock event creation
        orchestrator._create_incremental_sync_events = AsyncMock(
            return_value=[
                {"event_type": "DealWithPositionsCreated", "aggregate_id": uuid.uuid4()}
            ]
        )

        # Act
        await orchestrator._apply_changes_to_database(result, config)

        # Assert
        mock_event_store.append_events.assert_called_once()
        assert len(result.events_created) == 1

    async def test_create_full_sync_events_empty_deals(self, orchestrator):
        """Test creating events with no deals."""
        # Arrange
        from src.application.sync_orchestrator.models import SyncSummary

        summary = SyncSummary(
            started_at=datetime.now(),
            file_path="test.xlsx",
            file_hash="abc123",
            success=True,
            total_deals_processed=0,
            total_items_processed=0,
        )

        result = SyncResult(
            sync_session_id="test", sync_type="full", summary=summary, parse_result=None
        )

        # Act
        events = await orchestrator._create_full_sync_events(result)

        # Assert
        assert len(events) == 0

    async def test_create_full_sync_events_with_deals(self, orchestrator):
        """Test creating events for deals."""
        # Arrange
        from decimal import Decimal

        from src.domain.models import Deal, DealItem
        from src.domain.value_objects import Money, Period

        period = Period(month="Январь", year="2024", full_name="Январь 2024")
        deal = Deal(client_name="Test Client", invoice_info="Invoice 1", period=period)
        deal.id = uuid.uuid4()
        deal.total_revenue = Money(amount=Decimal("1000.00"))

        item = DealItem(product_name="Test Product")
        item.id = uuid.uuid4()
        item.sale_price = Money(amount=Decimal("500.00"))
        deal.add_item(item)

        from src.application.excel_parser.models import ParseResult, ParseStats
        from src.domain.models import SyncSession, SyncType

        # Create real ParseResult with the deal
        sync_session = SyncSession(sync_type=SyncType.FULL)
        sync_session.source_file_path = "test.xlsx"

        stats = ParseStats(total_deals=1, processed_deals=1, total_items=1, processed_items=1)

        parse_result = ParseResult(
            deals=[deal],
            stats=stats,
            sync_session=sync_session,
            file_path="test.xlsx",
            file_size=1024,
            file_hash="abc123",
        )

        from src.application.sync_orchestrator.models import SyncSummary

        summary = SyncSummary(
            started_at=datetime.now(),
            file_path="test.xlsx",
            file_hash="abc123",
            success=True,
            total_deals_processed=1,
            total_items_processed=1,
        )

        result = SyncResult(
            sync_session_id="test-session",
            sync_type="full",
            summary=summary,
            parse_result=parse_result,
        )

        # Act
        events = await orchestrator._create_full_sync_events(result)

        # Assert
        assert len(events) == 2  # 1 deal + 1 item

        deal_event = events[0]
        assert deal_event["event_type"] == "DealCreated"
        assert deal_event["aggregate_id"] == deal.id
        assert deal_event["metadata"]["sync_session_id"] == "test-session"
        assert deal_event["metadata"]["sync_type"] == "full"

        item_event = events[1]
        assert item_event["event_type"] == "DealItemAdded"
        assert item_event["aggregate_id"] == deal.id

    async def test_create_incremental_events_deal_insert(self, orchestrator):
        """Test that deal insertions produce DealWithPositionsCreated events."""
        from decimal import Decimal

        from src.application.change_detector.models import (
            ChangeDetectionResult,
            EntityChange,
            EntityType,
        )
        from src.application.sync_orchestrator.models import SyncSummary
        from src.domain.models import Deal, DealItem
        from src.domain.value_objects import Money, Period

        period = Period(month="Январь", year="2024", full_name="Январь 2024")
        deal_id = uuid.uuid4()
        deal = Deal(
            client_name="Test Client",
            invoice_info="Inv 1",
            period=period,
            period_month="Январь",
            period_year="2024",
            seller="Seller A",
        )
        deal.set_id(deal_id)
        deal.total_revenue = Money(amount=Decimal("1000.00"))

        item = DealItem(
            product_name="Product A",
            client_name="Test Client",
            period_month="Январь",
            period_year="2024",
            seller="Seller A",
            invoice_info="Inv 1",
            position_number=1,
        )
        item.set_id(uuid.uuid4())
        item.sale_price = Money(amount=Decimal("500.00"))
        deal.add_item(item)

        change = EntityChange(
            entity_type=EntityType.DEAL,
            change_type="INSERT",
            entity_key=deal.deal_key,
            new_entity=deal,
        )
        change_result = ChangeDetectionResult(
            total_excel_deals=1,
            total_db_deals=0,
            total_excel_items=1,
            total_db_items=0,
        )
        change_result.insertions.append(change)

        summary = SyncSummary(
            started_at=datetime.now(),
            file_path="test.xlsx",
            file_hash="abc",
        )
        result = SyncResult(
            sync_session_id="test-session",
            sync_type="incremental",
            summary=summary,
            change_detection_result=change_result,
        )

        events = await orchestrator._create_incremental_sync_events(result)

        assert len(events) == 1
        ev = events[0]
        assert ev["event_type"] == "DealWithPositionsCreated"
        assert ev["aggregate_id"] == deal.id
        assert ev["event_data"]["deal"]["deal_key"] == deal.deal_key
        assert len(ev["event_data"]["items"]) == 1
        assert ev["metadata"]["change_type"] == "INSERT"

    async def test_create_incremental_events_deal_update(self, orchestrator):
        """Test that deal updates produce DealWithPositionsCreated events."""
        from decimal import Decimal

        from src.application.change_detector.models import (
            ChangeDetectionResult,
            EntityChange,
            EntityType,
        )
        from src.application.sync_orchestrator.models import SyncSummary
        from src.domain.models import Deal, DealItem
        from src.domain.value_objects import Money, Period

        period = Period(month="Март", year="2024", full_name="Март 2024")
        deal = Deal(
            client_name="Client B",
            invoice_info="Inv 2",
            period=period,
            period_month="Март",
            period_year="2024",
            seller="Seller B",
        )
        deal.set_id(uuid.uuid4())
        deal.total_revenue = Money(amount=Decimal("2000.00"))

        item = DealItem(
            product_name="Product B",
            client_name="Client B",
            period_month="Март",
            period_year="2024",
            seller="Seller B",
            invoice_info="Inv 2",
            position_number=1,
        )
        item.set_id(uuid.uuid4())
        deal.add_item(item)

        change = EntityChange(
            entity_type=EntityType.DEAL,
            change_type="UPDATE",
            entity_key=deal.deal_key,
            new_entity=deal,
        )
        change_result = ChangeDetectionResult(
            total_excel_deals=1,
            total_db_deals=1,
            total_excel_items=1,
            total_db_items=1,
        )
        change_result.updates.append(change)

        summary = SyncSummary(
            started_at=datetime.now(),
            file_path="test.xlsx",
            file_hash="abc",
        )
        result = SyncResult(
            sync_session_id="s2",
            sync_type="incremental",
            summary=summary,
            change_detection_result=change_result,
        )

        events = await orchestrator._create_incremental_sync_events(result)

        assert len(events) == 1
        assert events[0]["event_type"] == "DealWithPositionsCreated"
        assert events[0]["metadata"]["change_type"] == "UPDATE"

    async def test_create_incremental_events_deal_delete(self, orchestrator):
        """Test that deal deletions produce DealDeleted events."""
        from src.application.change_detector.models import (
            ChangeDetectionResult,
            EntityChange,
            EntityType,
        )
        from src.application.sync_orchestrator.models import SyncSummary
        from src.domain.models import Deal
        from src.domain.value_objects import Period

        period = Period(month="Февраль", year="2024", full_name="Февраль 2024")
        deal = Deal(
            client_name="Client C",
            invoice_info="Inv 3",
            period=period,
            period_month="Февраль",
            period_year="2024",
            seller="Seller C",
        )
        deal.set_id(uuid.uuid4())

        change = EntityChange(
            entity_type=EntityType.DEAL,
            change_type="DELETE",
            entity_key=deal.deal_key,
            old_entity=deal,
        )
        change_result = ChangeDetectionResult(
            total_excel_deals=0,
            total_db_deals=1,
            total_excel_items=0,
            total_db_items=0,
        )
        change_result.deletions.append(change)

        summary = SyncSummary(
            started_at=datetime.now(),
            file_path="test.xlsx",
            file_hash="abc",
        )
        result = SyncResult(
            sync_session_id="s3",
            sync_type="incremental",
            summary=summary,
            change_detection_result=change_result,
        )

        events = await orchestrator._create_incremental_sync_events(result)

        assert len(events) == 1
        assert events[0]["event_type"] == "DealDeleted"
        assert events[0]["event_data"]["deal_id"] == str(deal.id)
        assert events[0]["metadata"]["change_type"] == "DELETE"

    async def test_create_incremental_events_item_changes_skipped(self, orchestrator):
        """Test that deal_item level changes are skipped (covered by deal-level)."""
        from src.application.change_detector.models import (
            ChangeDetectionResult,
            EntityChange,
            EntityType,
        )
        from src.application.sync_orchestrator.models import SyncSummary
        from src.domain.models import DealItem

        item = DealItem(
            product_name="Product X",
            client_name="Client X",
            period_month="Январь",
            period_year="2024",
            seller="Seller X",
            invoice_info="Inv X",
            position_number=1,
        )
        item.set_id(uuid.uuid4())

        change = EntityChange(
            entity_type=EntityType.DEAL_ITEM,
            change_type="INSERT",
            entity_key="item_key",
            new_entity=item,
        )
        change_result = ChangeDetectionResult(
            total_excel_deals=1,
            total_db_deals=1,
            total_excel_items=2,
            total_db_items=1,
        )
        change_result.insertions.append(change)

        summary = SyncSummary(
            started_at=datetime.now(),
            file_path="test.xlsx",
            file_hash="abc",
        )
        result = SyncResult(
            sync_session_id="s4",
            sync_type="incremental",
            summary=summary,
            change_detection_result=change_result,
        )

        events = await orchestrator._create_incremental_sync_events(result)

        assert len(events) == 0

    async def test_get_sync_history(self, orchestrator, mock_sync_session_repository):
        """Test getting sync history."""
        # Arrange
        session1 = SyncSession(sync_type=SyncType.FULL)
        session1.id = uuid.uuid4()
        session1.source_file_path = "file1.xlsx"
        session1.status = Status.COMPLETED

        session2 = SyncSession(sync_type=SyncType.INCREMENTAL)
        session2.id = uuid.uuid4()
        session2.source_file_path = "file2.xlsx"
        session2.status = Status.PENDING

        mock_sync_session_repository.get_latest_sessions.return_value = [session1, session2]

        # Act
        history = await orchestrator.get_sync_history(limit=5)

        # Assert
        assert len(history) == 2
        assert history[0]["id"] == str(session1.id)
        assert history[0]["sync_type"] == "full"
        assert history[0]["status"] == "completed"
        assert history[1]["sync_type"] == "incremental"

    async def test_get_sync_history_error(self, orchestrator, mock_sync_session_repository):
        """Test error handling in get_sync_history."""
        # Arrange
        mock_sync_session_repository.get_latest_sessions.side_effect = Exception("Database error")

        # Act
        history = await orchestrator.get_sync_history()

        # Assert
        assert history == []

    async def test_get_running_session(self, orchestrator, mock_sync_session_repository):
        """Test getting currently running session."""
        # Arrange
        running_session = SyncSession(sync_type=SyncType.INCREMENTAL)
        running_session.id = uuid.uuid4()
        running_session.source_file_path = "test.xlsx"
        running_session.start()
        mock_sync_session_repository.get_running_session.return_value = running_session

        # Act
        session_data = await orchestrator.get_running_session()

        # Assert
        assert session_data is not None
        assert session_data["id"] == str(running_session.id)
        assert session_data["sync_type"] == "incremental"
        assert session_data["status"] == "pending"

    async def test_get_running_session_none(self, orchestrator, mock_sync_session_repository):
        """Test getting running session when none exists."""
        # Arrange
        mock_sync_session_repository.get_running_session.return_value = None

        # Act
        session_data = await orchestrator.get_running_session()

        # Assert
        assert session_data is None

    async def test_sync_performance_metrics(
        self,
        orchestrator,
        mock_excel_parser,
        mock_sync_session_repository,
        full_sync_config,
        sample_parse_result,
    ):
        """Test that sync captures performance metrics."""
        # Arrange
        file_path = "test.xlsx"
        mock_sync_session_repository.get_running_session.return_value = None
        mock_excel_parser.parse_file.return_value = sample_parse_result

        # Act
        result = await orchestrator.execute_sync(file_path, full_sync_config)

        # Assert
        assert result.summary.duration_seconds > 0
        assert result.summary.parsing_duration_seconds >= 0
        assert result.summary.change_detection_duration_seconds >= 0
        assert result.summary.database_update_duration_seconds >= 0
        assert result.summary.started_at is not None
        assert result.summary.finished_at is not None

    async def test_sync_configuration_methods(self):
        """Test sync configuration helper methods."""
        # Test full sync
        full_config = SyncConfiguration(sync_type="full")
        assert full_config.is_full_sync() is True
        assert full_config.is_incremental_sync() is False

        # Test incremental sync
        incremental_config = SyncConfiguration(sync_type="incremental")
        assert incremental_config.is_full_sync() is False
        assert incremental_config.is_incremental_sync() is True

        # Test case insensitive
        full_config_upper = SyncConfiguration(sync_type="FULL")
        assert full_config_upper.is_full_sync() is True

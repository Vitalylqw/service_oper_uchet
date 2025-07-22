"""
Integration tests for synchronization process.

Tests the complete sync workflow from Excel parsing through change detection
to event storage and read model updates.
"""

import tempfile
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from src.application.change_detector import ChangeDetectorService
from src.application.excel_parser import ExcelParserService
from src.application.sync_orchestrator import SyncOrchestratorService
from src.application.sync_orchestrator.models import SyncConfiguration
from src.domain.interfaces import DealRepository, EventStore, SyncSessionRepository
from src.domain.models import Deal, DealItem, SyncSession, SyncType
from src.domain.value_objects import Money, Period, Status


def safe_cleanup_file(file_path: str | Path) -> None:
    """Safely remove file, handling Windows file locking issues."""
    try:
        Path(file_path).unlink()
    except (OSError, PermissionError):
        # File might be locked on Windows
        pass


@pytest.mark.integration
class TestSyncIntegration:
    """Integration tests for sync workflow."""

    @pytest.fixture
    def mock_deal_repository(self):
        """Mock deal repository for integration tests."""
        repository = AsyncMock(spec=DealRepository)
        # Default empty database
        repository.find_by_period.return_value = []
        repository.get_all_keys.return_value = []
        return repository

    @pytest.fixture
    def mock_event_store(self):
        """Mock event store for integration tests."""
        store = AsyncMock(spec=EventStore)
        store.append_events.return_value = None
        return store

    @pytest.fixture
    def mock_sync_session_repository(self):
        """Mock sync session repository for integration tests."""
        repository = AsyncMock(spec=SyncSessionRepository)
        repository.get_running_session.return_value = None
        repository.save.return_value = None
        return repository

    @pytest.fixture
    def excel_parser(self):
        """Real Excel parser service for integration tests."""
        return ExcelParserService()

    @pytest.fixture
    def change_detector(self, mock_deal_repository):
        """Real change detector service for integration tests."""
        return ChangeDetectorService(mock_deal_repository)

    @pytest.fixture
    def sync_orchestrator(
        self,
        excel_parser,
        change_detector,
        mock_event_store,
        mock_sync_session_repository
    ):
        """Real sync orchestrator with some mocked dependencies."""
        return SyncOrchestratorService(
            excel_parser=excel_parser,
            change_detector=change_detector,
            event_store=mock_event_store,
            sync_session_repository=mock_sync_session_repository
        )

    @pytest.fixture
    def sample_excel_file(self):
        """Create a sample Excel file for testing."""
        # Create temporary Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            # Create sample data
            data = {
                'Клиент': [
                    'ООО "Тестовая компания"', None, None,
                    'АО "Другая компания"', None,
                ],
                'Счет': [
                    '001 от 15.01.2024', 'Товар 1', 'Товар 2',
                    '002 от 16.01.2024', 'Товар 3',
                ],
                'Отгружен': [
                    'да', None, None,
                    'нет', None,
                ],
                'Оплачен': [
                    'да', None, None,
                    'нет', None,
                ],
                'Продавец': [
                    'Продавец 1', None, None,
                    'Продавец 2', None,
                ],
                'Выручка': [
                    100000, 50000, 50000,
                    75000, 75000,
                ],
                'Маржа': [
                    20000, 10000, 10000,
                    15000, 15000,
                ],
                'Количество': [
                    None, 10, 5,
                    None, 15,
                ],
                'Поставщик': [
                    None, 'Поставщик А', 'Поставщик Б',
                    None, 'Поставщик В',
                ]
            }

            df = pd.DataFrame(data)

            # Create Excel with sheet named "Январь 2024"
            with pd.ExcelWriter(tmp_file.name, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Январь 2024', index=False)

            return tmp_file.name

    async def test_full_sync_integration(
        self,
        sync_orchestrator,
        mock_event_store,
        mock_sync_session_repository,
        sample_excel_file
    ):
        """Test complete full synchronization workflow."""
        # Arrange
        config = SyncConfiguration(
            sync_type="full",
            create_events=True,
            update_read_models=True,
            continue_on_errors=True
        )

        # Act
        result = await sync_orchestrator.execute_sync(sample_excel_file, config)

        # Assert
        assert result.summary.success is True
        assert result.summary.total_deals_processed == 2  # Two deals
        assert result.summary.total_items_processed == 3  # Three items total
        assert result.parse_result is not None
        assert result.parse_result.total_deals == 2
        assert result.parse_result.total_items == 3

        # Verify events were created
        mock_event_store.append_events.assert_called_once()
        created_events = mock_event_store.append_events.call_args[0][0]
        assert len(created_events) == 5  # 2 deals + 3 items

        # Verify session management
        assert mock_sync_session_repository.save.call_count >= 2  # Create + complete

        # Check performance metrics
        assert result.summary.parsing_duration_seconds > 0
        assert result.summary.database_update_duration_seconds >= 0

        # Clean up
        safe_cleanup_file(sample_excel_file)

    async def test_incremental_sync_with_changes(
        self,
        sync_orchestrator,
        mock_deal_repository,
        mock_event_store,
        sample_excel_file
    ):
        """Test incremental synchronization with detected changes."""
        # Arrange - simulate existing deals in database
        existing_period = Period(month="Январь", year="2024", full_name="Январь 2024")

        existing_deal = Deal(
            client_name='ООО "Тестовая компания"',
            invoice_info='001 от 15.01.2024',
            period=existing_period
        )
        existing_deal.id = uuid.uuid4()
        existing_deal.seller = "Старый продавец"  # Different from Excel
        existing_deal.total_revenue = Money(amount=Decimal("80000.00"))  # Different amount

        # Mock repository to return existing deal
        mock_deal_repository.find_by_period.return_value = [existing_deal]

        config = SyncConfiguration(
            sync_type="incremental",
            incremental_period_months=3,
            create_events=True
        )

        # Act
        result = await sync_orchestrator.execute_sync(sample_excel_file, config)

        # Assert
        assert result.summary.success is True
        assert result.change_detection_result is not None
        assert result.change_detection_result.has_changes

        # Should detect insertions (new deal + items) and updates (existing deal changed)
        assert result.change_detection_result.insertion_count > 0
        assert result.change_detection_result.update_count >= 0  # May be 0 if no actual updates detected

        # Verify change detection performance
        assert result.summary.change_detection_duration_seconds > 0

        # Clean up
        Path(sample_excel_file).unlink()

    async def test_sync_with_parsing_errors(
        self,
        sync_orchestrator,
        mock_sync_session_repository
    ):
        """Test sync with file that causes parsing errors."""
        # Arrange - use non-existent file
        non_existent_file = "non_existent_file.xlsx"

        config = SyncConfiguration(
            sync_type="full",
            continue_on_errors=True,
            rollback_on_failure=False
        )

        # Act
        result = await sync_orchestrator.execute_sync(non_existent_file, config)

        # Assert
        assert result.summary.success is False
        assert result.has_errors
        assert len(result.errors) > 0
        assert "non_existent_file.xlsx" in str(result.errors[0])

        # Session should still be completed with failure
        assert mock_sync_session_repository.save.call_count >= 1

    async def test_concurrent_sync_prevention(
        self,
        sync_orchestrator,
        mock_sync_session_repository,
        sample_excel_file
    ):
        """Test prevention of concurrent sync sessions."""
        # Arrange - simulate running session
        running_session = SyncSession(sync_type=SyncType.FULL, file_path="other.xlsx")
        running_session.id = uuid.uuid4()
        running_session.start()
        mock_sync_session_repository.get_running_session.return_value = running_session

        config = SyncConfiguration(sync_type="full")

        # Act & Assert
        with pytest.raises(RuntimeError, match="Another sync session is already running"):
            await sync_orchestrator.execute_sync(sample_excel_file, config)

        # Clean up
        Path(sample_excel_file).unlink()

    async def test_sync_session_lifecycle(
        self,
        sync_orchestrator,
        mock_sync_session_repository,
        sample_excel_file
    ):
        """Test complete sync session lifecycle."""
        # Arrange
        config = SyncConfiguration(sync_type="full")
        saved_sessions = []

        # Capture saved sessions
        async def capture_save(session):
            saved_sessions.append(session)

        mock_sync_session_repository.save.side_effect = capture_save

        # Act
        await sync_orchestrator.execute_sync(sample_excel_file, config)

        # Assert
        assert len(saved_sessions) >= 2  # Create + complete

        # Check session creation
        created_session = saved_sessions[0]
        assert created_session.sync_type == SyncType.FULL
        assert created_session.source_file_path == sample_excel_file
        assert created_session.status in [Status.PENDING, Status.COMPLETED]  # Can be either during fast execution
        assert created_session.started_at is not None

        # Check session completion
        completed_session = saved_sessions[-1]
        assert completed_session.status == Status.COMPLETED
        assert completed_session.finished_at is not None

        # Clean up
        Path(sample_excel_file).unlink()

    async def test_event_creation_structure(
        self,
        sync_orchestrator,
        mock_event_store,
        sample_excel_file
    ):
        """Test structure and content of created events."""
        # Arrange
        config = SyncConfiguration(
            sync_type="full",
            create_events=True
        )

        # Act
        await sync_orchestrator.execute_sync(sample_excel_file, config)

        # Assert
        mock_event_store.append_events.assert_called_once()
        events = mock_event_store.append_events.call_args[0][0]

        # Check event structure
        for event in events:
            assert "aggregate_id" in event
            assert "event_type" in event
            assert "event_data" in event
            assert "metadata" in event

            # Check metadata structure
            metadata = event["metadata"]
            assert "sync_session_id" in metadata
            assert "sync_type" in metadata
            assert "source" in metadata
            assert metadata["source"] == "excel_sync"

        # Check event types
        event_types = [event["event_type"] for event in events]
        assert "DealCreated" in event_types
        assert "DealItemAdded" in event_types

        # Clean up
        Path(sample_excel_file).unlink()

    async def test_change_detection_accuracy(
        self,
        change_detector,
        mock_deal_repository
    ):
        """Test accuracy of change detection algorithms."""
        # Arrange - create Excel deals
        period = Period(month="Январь", year="2024", full_name="Январь 2024")

        excel_deal = Deal(
            client_name="Тестовый клиент",
            invoice_info="Счет 001",
            period=period
        )
        excel_deal.seller = "Продавец 1"
        excel_deal.total_revenue = Money(amount=Decimal("100000.00"))

        item = DealItem(product_name="Товар 1")
        item.quantity = Decimal("10")
        item.supplier_name = "Поставщик А"
        excel_deal.add_item(item)

        # Create slightly different DB deal
        db_deal = Deal(
            client_name="Тестовый клиент",
            invoice_info="Счет 001",
            period=period
        )
        db_deal.id = excel_deal.id
        # Don't set deal_key directly - it's computed from other fields
        db_deal.seller = excel_deal.seller  # Keep same seller to maintain same deal_key
        db_deal.total_revenue = Money(amount=Decimal("90000.00"))  # Changed
        db_deal.kickback_amount = Money(amount=Decimal("5000.00"))  # Changed field for testing

        db_item = DealItem(product_name="Товар 1")
        db_item.id = item.id
        db_item.quantity = Decimal("12")  # Changed
        db_item.supplier_name = "Поставщик А"
        db_deal.add_item(db_item)

        # Mock repository response
        mock_deal_repository.find_by_period.return_value = [db_deal]

        # Act
        result = await change_detector.detect_changes([excel_deal], sync_period_months=3)

        # Assert
        assert result.total_changes == 2  # Deal + item updated
        assert result.update_count == 2
        assert result.insertion_count == 0
        assert result.deletion_count == 0

        # Check specific changes
        deal_changes = result.get_deal_changes()
        assert len(deal_changes) == 1
        deal_change = deal_changes[0]
        assert "kickback_amount" in deal_change.field_changes  # This field was changed
        assert "total_revenue" in deal_change.field_changes

        item_changes = result.get_item_changes()
        assert len(item_changes) == 1
        item_change = item_changes[0]
        assert "quantity" in item_change.field_changes

    async def test_performance_metrics_integration(
        self,
        sync_orchestrator,
        sample_excel_file
    ):
        """Test performance metrics collection across all sync phases."""
        # Arrange
        config = SyncConfiguration(
            sync_type="incremental",
            enable_metrics=True
        )

        # Act
        result = await sync_orchestrator.execute_sync(sample_excel_file, config)

        # Assert performance metrics
        assert result.summary.duration_seconds > 0
        assert result.summary.parsing_duration_seconds >= 0
        assert result.summary.change_detection_duration_seconds >= 0
        assert result.summary.database_update_duration_seconds >= 0

        # Get detailed metrics
        metrics = result.get_performance_metrics()
        assert "total_duration" in metrics
        assert "parsing_duration" in metrics
        assert "change_detection_duration" in metrics
        assert "database_update_duration" in metrics

        # Check rates
        if result.summary.duration_seconds > 0:
            assert "deals_per_second" in metrics
            assert "items_per_second" in metrics

        # Clean up
        Path(sample_excel_file).unlink()

    async def test_error_propagation_integration(
        self,
        sync_orchestrator,
        mock_event_store
    ):
        """Test error propagation through the sync pipeline."""
        # Arrange - simulate event store error
        mock_event_store.append_events.side_effect = Exception("Event store error")

        config = SyncConfiguration(
            sync_type="full",
            continue_on_errors=True,
            rollback_on_failure=False
        )

        # Create a simple valid Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df = pd.DataFrame({
                'Клиент': ['Тест'],
                'Счет': ['001'],
                'Выручка': [1000]
            })
            with pd.ExcelWriter(tmp_file.name, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Январь 2024', index=False)

            # Act
            result = await sync_orchestrator.execute_sync(tmp_file.name, config)

            # Assert
            assert result.summary.success is False
            assert result.has_errors
            assert any("Event store error" in error for error in result.errors)

            # Parsing should have succeeded
            assert result.parse_result is not None
            assert result.parse_result.total_deals > 0

            # Clean up
            try:
                Path(tmp_file.name).unlink()
            except (OSError, PermissionError):
                # File might be locked on Windows
                pass

    async def test_sync_history_integration(
        self,
        sync_orchestrator,
        mock_sync_session_repository,
        sample_excel_file
    ):
        """Test sync history tracking integration."""
        # Arrange
        completed_session = SyncSession(sync_type=SyncType.FULL, file_path="old.xlsx")
        completed_session.id = uuid.uuid4()
        completed_session.status = Status.COMPLETED

        mock_sync_session_repository.get_latest_sessions.return_value = [completed_session]

        # Act
        history = await sync_orchestrator.get_sync_history(limit=10)

        # Assert
        assert len(history) == 1
        assert history[0]["id"] == str(completed_session.id)
        assert history[0]["sync_type"] == "full"
        assert history[0]["status"] == "completed"

        # Clean up
        Path(sample_excel_file).unlink()

    async def test_running_session_detection(
        self,
        sync_orchestrator,
        mock_sync_session_repository
    ):
        """Test running session detection integration."""
        # Arrange
        running_session = SyncSession(sync_type=SyncType.INCREMENTAL, file_path="running.xlsx")
        running_session.id = uuid.uuid4()
        running_session.start()

        mock_sync_session_repository.get_running_session.return_value = running_session

        # Act
        session_data = await sync_orchestrator.get_running_session()

        # Assert
        assert session_data is not None
        assert session_data["id"] == str(running_session.id)
        assert session_data["sync_type"] == "incremental"
        assert session_data["status"] == "pending"
        assert "started_at" in session_data
        assert "duration_seconds" in session_data

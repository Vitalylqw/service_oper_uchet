"""Tests for sync session visibility lifecycle in the orchestrator."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.application.change_detector.models import ChangeDetectionResult
from src.application.excel_parser.models import ParseResult, ParseStats
from src.application.sync_orchestrator import SyncConfiguration, SyncOrchestratorService
from src.domain.interfaces import EventStore, SyncSessionRepository
from src.domain.models import SyncSession, SyncType


@pytest.mark.unit
class TestSyncOrchestratorVisibility:
    """Visibility-specific tests for sync session lifecycle."""

    @pytest.fixture
    def mock_sync_session_repository(self):
        """Mock sync session repository."""
        return AsyncMock(spec=SyncSessionRepository)

    @pytest.fixture
    def orchestrator(self, mock_sync_session_repository):
        """Orchestrator instance with mocked dependencies."""
        parser = AsyncMock()
        parser.parse_file.return_value = ParseResult(
            deals=[],
            stats=ParseStats(),
            sync_session=SyncSession(sync_type=SyncType.FULL),
            file_path="test.xlsx",
            file_size=128,
            file_hash="abc123",
            parsed_at=datetime.now(),
        )

        change_detector = AsyncMock()
        change_detector.detect_changes.return_value = ChangeDetectionResult()

        event_store = AsyncMock(spec=EventStore)

        return SyncOrchestratorService(
            excel_parser=parser,
            change_detector=change_detector,
            event_store=event_store,
            sync_session_repository=mock_sync_session_repository,
        )

    async def test_execute_sync_uses_visible_session_persistence(
        self,
        orchestrator,
        mock_sync_session_repository,
    ):
        """Orchestrator should persist session start and finish visibly."""
        mock_sync_session_repository.get_running_session.return_value = None
        config = SyncConfiguration(sync_type="full")

        result = await orchestrator.execute_sync("test.xlsx", config)

        assert result.summary.success is True
        assert mock_sync_session_repository.save_visible.await_count == 2
        assert mock_sync_session_repository.save.await_count == 0

    async def test_execute_sync_marks_session_failed_on_interrupt(
        self,
        orchestrator,
        mock_sync_session_repository,
    ):
        """Interrupted sync should not leave a pending visible session."""
        mock_sync_session_repository.get_running_session.return_value = None
        orchestrator.excel_parser.parse_file.side_effect = KeyboardInterrupt()
        config = SyncConfiguration(sync_type="full")

        with pytest.raises(KeyboardInterrupt):
            await orchestrator.execute_sync("test.xlsx", config)

        assert mock_sync_session_repository.save_visible.await_count == 2
        final_session = mock_sync_session_repository.save_visible.await_args_list[-1].args[0]
        assert final_session.status.value == "failed"
        assert final_session.finished_at is not None
        assert final_session.stats.errors

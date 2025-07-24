"""
Unit tests for RealSyncService.

Tests the real sync service wrapper that integrates SyncOrchestratorService
with FastAPI presentation layer.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.application.sync_orchestrator import SyncOrchestratorService
from src.domain.models import SyncSession, SyncType
from src.domain.models.sync_session import SyncResult
from src.domain.value_objects import Status
from src.infrastructure.database.repositories import SyncSessionRepositoryImplementation
from src.presentation.api.services.real_sync_service import RealSyncService


@pytest.mark.unit
class TestRealSyncService:
    """Test RealSyncService functionality."""

    @pytest.fixture
    def mock_sync_orchestrator(self):
        """Create mock sync orchestrator."""
        orchestrator = AsyncMock(spec=SyncOrchestratorService)
        return orchestrator

    @pytest.fixture
    def mock_sync_session_repository(self):
        """Create mock sync session repository."""
        repository = AsyncMock(spec=SyncSessionRepositoryImplementation)
        return repository

    @pytest.fixture
    def real_sync_service(self, mock_sync_orchestrator, mock_sync_session_repository):
        """Create RealSyncService instance with mocked dependencies."""
        return RealSyncService(mock_sync_orchestrator, mock_sync_session_repository)

    @pytest.fixture
    def sample_sync_session(self):
        """Create sample sync session for testing."""
        session = SyncSession(sync_type=SyncType.INCREMENTAL)
        session.id = uuid.uuid4()
        session.started_at = datetime(2024, 1, 15, 3, 0, 0)  # Устанавливаем до complete_success()
        session.complete_success()  # Завершаем сессию, что установит finished_at
        session.finished_at = datetime(2024, 1, 15, 3, 5, 30)  # Переопределяем для точности
        # duration_seconds - computed property
        session.source_file_path = "/data/test.xlsx"
        # SyncSession не имеет поля created_at, только created_by
        # error_message берется из stats.errors
        return session

    @pytest.fixture
    def temp_excel_file(self, tmp_path):
        """Create temporary Excel file and return its path as str."""
        file_path = tmp_path / "test.xlsx"
        file_path.write_bytes(b"dummy")
        return str(file_path)

    async def test_get_sessions_paginated_empty_database(self, real_sync_service, mock_sync_session_repository):
        """Test get_sessions_paginated with empty database."""
        # Arrange
        mock_sync_session_repository.get_latest_sessions.return_value = []

        # Act
        result = await real_sync_service.get_sessions_paginated(page=1, limit=10, filters={})

        # Assert
        assert result["items"] == []
        assert result["total"] == 0
        assert result["page"] == 1
        assert result["limit"] == 10
        assert result["pages"] == 0
        mock_sync_session_repository.get_latest_sessions.assert_called_once_with(limit=100)

    async def test_get_sessions_paginated_with_data(self, real_sync_service, mock_sync_session_repository, sample_sync_session):
        """Test get_sessions_paginated with data."""
        # Arrange
        mock_sync_session_repository.get_latest_sessions.return_value = [sample_sync_session]

        # Act
        result = await real_sync_service.get_sessions_paginated(page=1, limit=10, filters={})

        # Assert
        assert len(result["items"]) == 1
        assert result["total"] == 1
        assert result["page"] == 1
        assert result["limit"] == 10
        assert result["pages"] == 1

    async def test_get_sessions_paginated_with_status_filter(self, real_sync_service, mock_sync_session_repository, sample_sync_session):
        """Test get_sessions_paginated with status filtering."""
        # Arrange
        mock_sync_session_repository.get_latest_sessions.return_value = [sample_sync_session]
        filters = {"status": "completed"}

        # Act
        result = await real_sync_service.get_sessions_paginated(page=1, limit=10, filters=filters)

        # Assert
        assert len(result["items"]) == 1

    async def test_get_sessions_paginated_with_type_filter(self, real_sync_service, mock_sync_session_repository, sample_sync_session):
        """Test get_sessions_paginated with session type filtering."""
        # Arrange
        mock_sync_session_repository.get_latest_sessions.return_value = [sample_sync_session]
        filters = {"session_type": "incremental"}

        # Act
        result = await real_sync_service.get_sessions_paginated(page=1, limit=10, filters=filters)

        # Assert
        assert len(result["items"]) == 1

    async def test_get_sessions_paginated_filter_no_match(self, real_sync_service, mock_sync_session_repository, sample_sync_session):
        """Test get_sessions_paginated with filter that doesn't match."""
        # Arrange
        mock_sync_session_repository.get_latest_sessions.return_value = [sample_sync_session]
        filters = {"status": "failed"}  # Session is completed, so no match

        # Act
        result = await real_sync_service.get_sessions_paginated(page=1, limit=10, filters=filters)

        # Assert
        assert len(result["items"]) == 0
        assert result["total"] == 0

    async def test_get_sessions_paginated_with_exception(self, real_sync_service, mock_sync_session_repository):
        """Test get_sessions_paginated when repository raises exception."""
        # Arrange
        mock_sync_session_repository.get_latest_sessions.side_effect = Exception("Database error")

        # Act
        result = await real_sync_service.get_sessions_paginated(page=1, limit=10, filters={})

        # Assert
        assert result["items"] == []
        assert result["total"] == 0
        assert result["page"] == 1
        assert result["limit"] == 10

    async def test_get_session_by_id_found(self, real_sync_service, mock_sync_session_repository, sample_sync_session):
        """Test get_session_by_id when session is found."""
        # Arrange
        session_id = str(sample_sync_session.id)
        mock_sync_session_repository.get_by_id.return_value = sample_sync_session

        # Act
        result = await real_sync_service.get_session_by_id(session_id)

        # Assert
        assert result is not None
        assert result["id"] == session_id
        assert result["session_type"] == "incremental"
        assert result["status"] == "completed"
        assert result["success"] is True
        assert result["duration_seconds"] == 330.0
        mock_sync_session_repository.get_by_id.assert_called_once_with(sample_sync_session.id)

    async def test_get_session_by_id_not_found(self, real_sync_service, mock_sync_session_repository):
        """Test get_session_by_id when session is not found."""
        # Arrange
        session_id = str(uuid.uuid4())
        mock_sync_session_repository.get_by_id.return_value = None

        # Act
        result = await real_sync_service.get_session_by_id(session_id)

        # Assert
        assert result is None
        mock_sync_session_repository.get_by_id.assert_called_once()

    async def test_get_session_by_id_invalid_uuid(self, real_sync_service):
        """Test get_session_by_id with invalid UUID format."""
        # Act
        result = await real_sync_service.get_session_by_id("invalid-uuid")

        # Assert
        assert result is None

    async def test_get_session_by_id_with_exception(self, real_sync_service, mock_sync_session_repository):
        """Test get_session_by_id when repository raises exception."""
        # Arrange
        session_id = str(uuid.uuid4())
        mock_sync_session_repository.get_by_id.side_effect = Exception("Database error")

        # Act
        result = await real_sync_service.get_session_by_id(session_id)

        # Assert
        assert result is None

    async def test_create_sync_session_success(self, real_sync_service, mock_sync_session_repository, temp_excel_file):
        """Test create_sync_session with successful creation."""
        # Arrange
        mock_sync_session_repository.get_running_session.return_value = None
        file_path = temp_excel_file  # use real temporary file
        session_type = "incremental"

        # Act
        result = await real_sync_service.create_sync_session(file_path, session_type, force=False)

        # Assert
        assert result["session_type"] == session_type
        assert result["status"] == "pending"
        assert result["file_path"] == file_path
        assert result["success"] is False  # Not yet completed
        assert "id" in result
        assert "started_at" in result
        mock_sync_session_repository.get_running_session.assert_called_once()

    async def test_create_sync_session_with_running_session_error(self, real_sync_service, mock_sync_session_repository, sample_sync_session, temp_excel_file):
        """Test create_sync_session when another session is running."""
        # Arrange
        sample_sync_session.status = Status.PENDING  # Running session
        mock_sync_session_repository.get_running_session.return_value = sample_sync_session
        file_path = temp_excel_file

        # Act & Assert
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await real_sync_service.create_sync_session(file_path, "incremental", force=False)
        assert exc_info.value.status_code == 400
        assert "Another sync session is already running" in exc_info.value.detail

    async def test_create_sync_session_with_force(self, real_sync_service, mock_sync_session_repository, sample_sync_session, temp_excel_file):
        """Test create_sync_session with force=True ignores running sessions."""
        # Arrange
        sample_sync_session.status = Status.PENDING  # Running session
        mock_sync_session_repository.get_running_session.return_value = sample_sync_session
        file_path = temp_excel_file

        # Act
        result = await real_sync_service.create_sync_session(file_path, "full", force=True)

        # Assert
        assert result["session_type"] == "full"
        assert result["status"] == "pending"
        # Should not check for running session when force=True
        mock_sync_session_repository.get_running_session.assert_not_called()

    async def test_get_session_logs_empty(self, real_sync_service):
        """Test get_session_logs returns empty list."""
        # Act
        result = await real_sync_service.get_session_logs("session-123")

        # Assert
        assert result == []

    async def test_get_sync_statistics_empty_database(self, real_sync_service, mock_sync_session_repository):
        """Test get_sync_statistics with empty database."""
        # Arrange
        mock_sync_session_repository.get_latest_sessions.return_value = []

        # Act
        result = await real_sync_service.get_sync_statistics()

        # Assert
        assert result["total_sessions"] == 0
        assert result["successful_sessions"] == 0
        assert result["failed_sessions"] == 0
        assert result["success_rate"] == 0
        assert result["average_duration_seconds"] == 0

    async def test_get_sync_statistics_with_data(self, real_sync_service, mock_sync_session_repository):
        """Test get_sync_statistics with session data."""
        # Arrange
        successful_session = SyncSession(sync_type=SyncType.INCREMENTAL)
        successful_session.result = SyncResult.SUCCESS
        successful_session.started_at = datetime(2024, 1, 15, 3, 0, 0)
        successful_session.finished_at = datetime(2024, 1, 15, 3, 5, 0)

        failed_session = SyncSession(sync_type=SyncType.FULL)
        failed_session.result = SyncResult.FAILED
        failed_session.started_at = datetime(2024, 1, 14, 3, 0, 0)
        failed_session.finished_at = datetime(2024, 1, 14, 3, 2, 30)

        mock_sync_session_repository.get_latest_sessions.return_value = [successful_session, failed_session]

        # Act
        result = await real_sync_service.get_sync_statistics()

        # Assert
        assert result["total_sessions"] == 2
        assert result["successful_sessions"] == 1
        assert result["failed_sessions"] == 1
        assert result["success_rate"] == 50.0
        assert result["average_duration_seconds"] == 225.0  # (300 + 150) / 2
        assert result["last_successful_sync"] == datetime(2024, 1, 15, 3, 5, 0)
        assert result["last_failed_sync"] == datetime(2024, 1, 14, 3, 2, 30)

    async def test_get_sync_statistics_with_exception(self, real_sync_service, mock_sync_session_repository):
        """Test get_sync_statistics when repository raises exception."""
        # Arrange
        mock_sync_session_repository.get_latest_sessions.side_effect = Exception("Database error")

        # Act
        result = await real_sync_service.get_sync_statistics()

        # Assert
        assert result["total_sessions"] == 0
        assert result["successful_sessions"] == 0
        assert result["failed_sessions"] == 0
        assert result["success_rate"] == 0

    async def test_domain_session_to_api_format_basic(self, real_sync_service, sample_sync_session):
        """Test _domain_session_to_api_format with basic session."""
        # Act
        result = await real_sync_service._domain_session_to_api_format(sample_sync_session)

        # Assert
        assert result["id"] == str(sample_sync_session.id)
        assert result["session_type"] == "incremental"
        assert result["status"] == "completed"
        assert result["success"] is True
        assert result["started_at"] == datetime(2024, 1, 15, 3, 0, 0)
        assert result["finished_at"] == datetime(2024, 1, 15, 3, 5, 30)
        assert result["duration_seconds"] == 330.0
        assert result["error_message"] is None
        assert result["created_at"] == datetime(2024, 1, 15, 3, 0, 0)

    async def test_domain_session_to_api_format_detailed(self, real_sync_service, sample_sync_session):
        """Test _domain_session_to_api_format with detailed=True."""
        # Arrange
        sample_sync_session.source_file_path = "/data/test.xlsx"
        sample_sync_session.source_file_hash = "abc123"  # Исправлено: правильное поле
        sample_sync_session.source_file_size = 1024000   # Исправлено: правильное поле

        # Act
        result = await real_sync_service._domain_session_to_api_format(sample_sync_session, detailed=True)

        # Assert
        assert "file_path" in result
        assert result["file_path"] == "/data/test.xlsx"
        assert "file_hash" in result
        assert result["file_hash"] == "abc123"
        assert "file_size" in result
        assert result["file_size"] == 1024000
        assert "parsing_duration_seconds" in result
        assert "change_detection_duration_seconds" in result
        assert "database_duration_seconds" in result
        assert "metadata" in result

    async def test_domain_session_to_api_format_with_processing_stats(self, real_sync_service, sample_sync_session):
        """Test _domain_session_to_api_format with processing statistics."""
        # Arrange - устанавливаем статистику в stats объекте
        sample_sync_session.stats.total_deals = 25
        sample_sync_session.stats.total_items = 75
        sample_sync_session.stats.processed_deals = 20
        sample_sync_session.stats.failed_deals = 5
        sample_sync_session.stats.processed_items = 70
        sample_sync_session.stats.failed_items = 5
        sample_sync_session.stats.new_records = 10
        sample_sync_session.stats.updated_records = 15
        sample_sync_session.stats.deleted_records = 2
        sample_sync_session.stats.errors = ["Error 1", "Error 2"]
        sample_sync_session.stats.warnings = ["Warning 1"]

        # Act
        result = await real_sync_service._domain_session_to_api_format(sample_sync_session)

        # Assert
        assert result["total_deals_processed"] == 25
        assert result["total_items_processed"] == 75
        assert result["processed_deals"] == 20
        assert result["failed_deals"] == 5
        assert result["processed_items"] == 70
        assert result["failed_items"] == 5
        assert result["new_records"] == 10
        assert result["updated_records"] == 15
        assert result["deleted_records"] == 2
        assert result["errors_count"] == 2
        assert result["warnings_count"] == 1

    async def test_pagination_logic(self, real_sync_service, mock_sync_session_repository):
        """Test pagination logic with multiple sessions."""
        # Arrange
        sessions = []
        for i in range(25):  # Create 25 sessions
            session = SyncSession(sync_type=SyncType.INCREMENTAL)
            session.id = uuid.uuid4()
            session.started_at = datetime(2024, 1, 15, 3, 0, 0)  # Устанавливаем время начала
            session.complete_success()  # Корректно завершаем сессию
            sessions.append(session)

        mock_sync_session_repository.get_latest_sessions.return_value = sessions

        # Act - Get second page with 10 items per page
        result = await real_sync_service.get_sessions_paginated(page=2, limit=10, filters={})

        # Assert
        assert len(result["items"]) == 10  # Should have 10 items on page 2
        assert result["total"] == 25
        assert result["page"] == 2
        assert result["limit"] == 10
        assert result["pages"] == 3  # ceil(25/10) = 3

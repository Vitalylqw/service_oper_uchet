"""
Unit tests for RealHealthService.

Tests the real health service that provides actual system monitoring
including database connectivity and system metrics.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.database.connection import DatabaseManager
from src.presentation.api.services.real_health_service import RealHealthService


@pytest.mark.unit
class TestRealHealthService:
    """Test RealHealthService functionality."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        manager = AsyncMock(spec=DatabaseManager)
        manager.config = MagicMock()
        manager.config.db_type = "sqlite"
        return manager

    @pytest.fixture
    def real_health_service(self, mock_db_manager):
        """Create RealHealthService instance with mocked database manager."""
        return RealHealthService(mock_db_manager)

    async def test_get_database_status_healthy(self, real_health_service, mock_db_manager):
        """Test get_database_status when database is healthy."""
        # Arrange
        mock_db_manager.test_connection.return_value = True

        # Act
        result = await real_health_service.get_database_status()

        # Assert
        assert result["status"] == "healthy"
        assert result["database_type"] == "sqlite"
        assert "response_time_ms" in result
        assert "last_check" in result
        assert result["details"] == "Database connection successful"
        assert isinstance(result["response_time_ms"], (int, float))

        # Verify database manager was called
        mock_db_manager.test_connection.assert_called_once()

    async def test_get_database_status_unhealthy(self, real_health_service, mock_db_manager):
        """Test get_database_status when database is unhealthy."""
        # Arrange
        mock_db_manager.test_connection.return_value = False

        # Act
        result = await real_health_service.get_database_status()

        # Assert
        assert result["status"] == "unhealthy"
        assert result["database_type"] == "sqlite"
        assert "response_time_ms" in result
        assert result["details"] == "Database connection failed"
        mock_db_manager.test_connection.assert_called_once()

    async def test_get_database_status_error(self, real_health_service, mock_db_manager):
        """Test get_database_status when exception occurs."""
        # Arrange
        mock_db_manager.test_connection.side_effect = Exception("Connection timeout")

        # Act
        result = await real_health_service.get_database_status()

        # Assert
        assert result["status"] == "error"
        assert result["database_type"] == "sqlite"
        assert result["response_time_ms"] is None
        assert "Connection timeout" in result["details"]

    @patch('src.presentation.api.services.real_health_service.psutil')
    async def test_get_system_metrics_success(self, mock_psutil, real_health_service):
        """Test get_system_metrics with successful collection."""
        # Arrange
        mock_psutil.cpu_percent.return_value = 25.5
        mock_psutil.cpu_count.return_value = 8

        mock_memory = MagicMock()
        mock_memory.percent = 60.0
        mock_memory.total = 16 * 1024**3  # 16GB
        mock_memory.available = 6.4 * 1024**3  # 6.4GB
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_disk = MagicMock()
        mock_disk.percent = 45.0
        mock_disk.total = 500 * 1024**3  # 500GB
        mock_disk.free = 275 * 1024**3  # 275GB
        mock_psutil.disk_usage.return_value = mock_disk

        mock_process = MagicMock()
        mock_process_memory = MagicMock()
        mock_process_memory.rss = 128 * 1024**2  # 128MB
        mock_process.memory_info.return_value = mock_process_memory
        mock_process.cpu_percent.return_value = 5.2
        mock_psutil.Process.return_value = mock_process

        # Mock database connection check
        real_health_service._check_db_connection_quick = AsyncMock(return_value=True)

        # Act
        result = await real_health_service.get_system_metrics()

        # Assert
        assert result["cpu_percent"] == 25.5
        assert result["cpu_count"] == 8
        assert result["memory_percent"] == 60.0
        assert result["memory_total_gb"] == 16.0
        assert result["memory_available_gb"] == 6.4
        assert result["disk_percent"] == 45.0
        assert result["disk_total_gb"] == 500.0
        assert result["disk_free_gb"] == 275.0
        assert result["process_memory_mb"] == 128.0
        assert result["process_cpu_percent"] == 5.2
        assert result["database_connections"] == 1
        assert result["active_sessions"] == 0
        assert "uptime_seconds" in result
        assert "uptime_formatted" in result
        assert "collected_at" in result

    @patch('src.presentation.api.services.real_health_service.psutil')
    async def test_get_system_metrics_exception(self, mock_psutil, real_health_service):
        """Test get_system_metrics when exception occurs."""
        # Arrange
        mock_psutil.cpu_percent.side_effect = Exception("psutil error")

        # Act
        result = await real_health_service.get_system_metrics()

        # Assert
        assert "error" in result
        assert "psutil error" in result["error"]
        assert "collected_at" in result

    async def test_get_service_status_all_healthy(self, real_health_service):
        """Test get_service_status when all components are healthy."""
        # Arrange
        real_health_service.get_database_status = AsyncMock(return_value={
            "status": "healthy",
            "details": "Database OK"
        })
        real_health_service._check_file_system = AsyncMock(return_value={
            "status": "healthy",
            "details": "File system OK"
        })
        real_health_service._check_memory_usage = AsyncMock(return_value={
            "status": "healthy",
            "details": "Memory OK"
        })

        # Act
        result = await real_health_service.get_service_status()

        # Assert
        assert result["overall_status"] == "healthy"
        assert result["components"]["api"]["status"] == "healthy"
        assert result["components"]["database"]["status"] == "healthy"
        assert result["components"]["file_system"]["status"] == "healthy"
        assert result["components"]["memory"]["status"] == "healthy"
        assert "last_check" in result
        assert "uptime" in result

    async def test_get_service_status_some_unhealthy(self, real_health_service):
        """Test get_service_status when some components are unhealthy."""
        # Arrange
        real_health_service.get_database_status = AsyncMock(return_value={
            "status": "unhealthy",
            "details": "Database connection failed"
        })
        real_health_service._check_file_system = AsyncMock(return_value={
            "status": "healthy",
            "details": "File system OK"
        })
        real_health_service._check_memory_usage = AsyncMock(return_value={
            "status": "healthy",
            "details": "Memory OK"
        })

        # Act
        result = await real_health_service.get_service_status()

        # Assert
        assert result["overall_status"] == "unhealthy"
        assert result["components"]["database"]["status"] == "unhealthy"

    async def test_get_service_status_exception(self, real_health_service):
        """Test get_service_status when exception occurs."""
        # Arrange
        real_health_service.get_database_status = AsyncMock(side_effect=Exception("Service error"))

        # Act
        result = await real_health_service.get_service_status()

        # Assert
        assert result["overall_status"] == "error"
        assert "Service error" in result["error"]

    async def test_check_db_connection_quick_success(self, real_health_service, mock_db_manager):
        """Test _check_db_connection_quick with successful connection."""
        # Arrange
        mock_db_manager.test_connection.return_value = True

        # Act
        result = await real_health_service._check_db_connection_quick()

        # Assert
        assert result is True

    async def test_check_db_connection_quick_failure(self, real_health_service, mock_db_manager):
        """Test _check_db_connection_quick with failed connection."""
        # Arrange
        mock_db_manager.test_connection.side_effect = Exception("Connection failed")

        # Act
        result = await real_health_service._check_db_connection_quick()

        # Assert
        assert result is False

    @patch('tempfile.NamedTemporaryFile')
    @patch('pathlib.Path')
    async def test_check_file_system_success(self, mock_path, mock_temp_file, real_health_service):
        """Test _check_file_system with successful file operations."""
        # Arrange
        mock_temp_file.return_value.__enter__.return_value = MagicMock()

        mock_data_dir = MagicMock()
        mock_data_dir.exists.return_value = True
        mock_data_dir.absolute.return_value = "/test/data"
        mock_path.return_value = mock_data_dir

        mock_test_file = MagicMock()
        mock_data_dir.__truediv__.return_value = mock_test_file

        # Act
        result = await real_health_service._check_file_system()

        # Assert
        assert result["status"] == "healthy"
        assert result["writable"] is True
        assert "File system access normal" in result["details"]

    @patch('tempfile.NamedTemporaryFile')
    async def test_check_file_system_failure(self, mock_temp_file, real_health_service):
        """Test _check_file_system with file operation failure."""
        # Arrange
        mock_temp_file.side_effect = Exception("Permission denied")

        # Act
        result = await real_health_service._check_file_system()

        # Assert
        assert result["status"] == "unhealthy"
        assert result["writable"] is False
        assert "Permission denied" in result["details"]

    @patch('src.presentation.api.services.real_health_service.psutil')
    async def test_check_memory_usage_healthy(self, mock_psutil, real_health_service):
        """Test _check_memory_usage with healthy memory usage."""
        # Arrange
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_memory.available = 8 * 1024**3  # 8GB
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_process = MagicMock()
        mock_process_memory = MagicMock()
        mock_process_memory.rss = 64 * 1024**2  # 64MB
        mock_process.memory_info.return_value = mock_process_memory
        mock_psutil.Process.return_value = mock_process

        # Act
        result = await real_health_service._check_memory_usage()

        # Assert
        assert result["status"] == "healthy"
        assert result["system_memory_percent"] == 50.0
        assert result["process_memory_mb"] == 64.0
        assert result["available_gb"] == 8.0
        assert "normal" in result["details"]

    @patch('src.presentation.api.services.real_health_service.psutil')
    async def test_check_memory_usage_warning(self, mock_psutil, real_health_service):
        """Test _check_memory_usage with warning level memory usage."""
        # Arrange
        mock_memory = MagicMock()
        mock_memory.percent = 85.0  # Above warning threshold
        mock_memory.available = 2 * 1024**3  # 2GB
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_process = MagicMock()
        mock_process_memory = MagicMock()
        mock_process_memory.rss = 512 * 1024**2  # 512MB
        mock_process.memory_info.return_value = mock_process_memory
        mock_psutil.Process.return_value = mock_process

        # Act
        result = await real_health_service._check_memory_usage()

        # Assert
        assert result["status"] == "warning"
        assert result["system_memory_percent"] == 85.0
        assert "high" in result["details"]

    @patch('src.presentation.api.services.real_health_service.psutil')
    async def test_check_memory_usage_critical(self, mock_psutil, real_health_service):
        """Test _check_memory_usage with critical memory usage."""
        # Arrange
        mock_memory = MagicMock()
        mock_memory.percent = 95.0  # Above critical threshold
        mock_memory.available = 0.5 * 1024**3  # 0.5GB
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_process = MagicMock()
        mock_process_memory = MagicMock()
        mock_process_memory.rss = 1024 * 1024**2  # 1GB
        mock_process.memory_info.return_value = mock_process_memory
        mock_psutil.Process.return_value = mock_process

        # Act
        result = await real_health_service._check_memory_usage()

        # Assert
        assert result["status"] == "critical"
        assert result["system_memory_percent"] == 95.0
        assert "critical" in result["details"]

    def test_format_uptime_various_durations(self, real_health_service):
        """Test _format_uptime with various time durations."""
        # Test seconds only
        assert real_health_service._format_uptime(45) == "45s"

        # Test minutes and seconds
        assert real_health_service._format_uptime(125) == "2m 5s"

        # Test hours, minutes and seconds
        assert real_health_service._format_uptime(3665) == "1h 1m 5s"

        # Test days, hours, minutes and seconds
        assert real_health_service._format_uptime(90061) == "1d 1h 1m 1s"

        # Test multiple days
        assert real_health_service._format_uptime(172861) == "2d 0h 1m 1s"

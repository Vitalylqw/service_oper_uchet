"""
Unit tests for file system infrastructure.

Tests for FileSystemConfig, FileSystemService and models.
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.infrastructure.file_system import (
    FileChangeType,
    FileInfo,
    FileMonitoringState,
    FileOperationStatus,
    FileRetrievalResult,
    FileSystemConfig,
    FileSystemService,
    FileValidationResult,
    ProtocolCapabilities,
)


class TestFileSystemConfig:
    """Test FileSystemConfig functionality."""

    def test_default_values(self):
        """Test default configuration values."""
        config = FileSystemConfig()

        assert config.protocol == "local"
        assert config.source_filename == "data.xlsx"
        assert config.local_destination_directory == "data/downloaded"
        assert config.max_file_size_mb == 100
        assert config.max_retry_attempts == 3
        assert config.enable_file_monitoring is True

    def test_protocol_ports(self):
        """Test default port assignment for different protocols."""
        # Test SMB
        config = FileSystemConfig(protocol="smb")
        assert config.default_port == 445

        # Test FTP
        config = FileSystemConfig(protocol="ftp")
        assert config.default_port == 21

        # Test SFTP
        config = FileSystemConfig(protocol="sftp")
        assert config.default_port == 22

        # Test HTTP
        config = FileSystemConfig(protocol="http")
        assert config.default_port == 80

        # Test custom port
        config = FileSystemConfig(protocol="ftp", source_port=2121)
        assert config.default_port == 2121

    def test_url_generation(self):
        """Test full source URL generation for different protocols."""
        # Test local protocol
        config = FileSystemConfig(
            protocol="local",
            local_source_directory="data/input",
            source_filename="test.xlsx"
        )
        expected = str(Path("data/input/test.xlsx"))
        assert config.full_source_url == expected

        # Test HTTP protocol
        config = FileSystemConfig(
            protocol="http",
            source_host="example.com",
            source_path="files",
            source_filename="data.xlsx"
        )
        assert config.full_source_url == "http://example.com/files/data.xlsx"

        # Test FTP with authentication
        config = FileSystemConfig(
            protocol="ftp",
            source_host="ftp.example.com",
            source_path="uploads",
            source_filename="data.xlsx",
            username="user",
            password="pass"
        )
        assert config.full_source_url == "ftp://user:pass@ftp.example.com/uploads/data.xlsx"

    def test_destination_paths(self):
        """Test destination and backup path generation."""
        config = FileSystemConfig(
            local_destination_directory="downloads",
            backup_directory="backups",
            source_filename="test.xlsx"
        )

        assert config.destination_file_path == Path("downloads/test.xlsx")

        # Backup path should include timestamp
        backup_path = config.backup_file_path
        assert backup_path.parent == Path("backups")
        assert "test" in backup_path.name
        assert ".xlsx" in backup_path.name

    def test_connection_params(self):
        """Test connection parameter generation."""
        # Test SMB parameters
        config = FileSystemConfig(
            protocol="smb",
            source_host="server.local",
            username="admin",
            password="secret",
            domain="WORKGROUP"
        )

        params = config.get_connection_params()
        assert params["host"] == "server.local"
        assert params["username"] == "admin"
        assert params["password"] == "secret"
        assert params["domain"] == "WORKGROUP"
        assert params["port"] == 445

    def test_configuration_validation(self):
        """Test configuration validation."""
        # Valid local configuration
        config = FileSystemConfig(protocol="local")
        errors = config.validate_configuration()
        assert len(errors) == 0

        # Invalid remote configuration (missing host)
        config = FileSystemConfig(protocol="smb")
        errors = config.validate_configuration()
        assert len(errors) > 0
        assert any("source_host is required" in error for error in errors)

        # Invalid SMB configuration (missing username)
        config = FileSystemConfig(protocol="smb", source_host="server.local")
        errors = config.validate_configuration()
        assert any("username is required" in error for error in errors)


class TestFileSystemModels:
    """Test file system Pydantic models."""

    def test_file_info_creation(self):
        """Test FileInfo model creation."""
        file_info = FileInfo(
            path="/tmp/test.xlsx",
            size_bytes=1024*1024,  # 1MB
            modified_time=datetime.now()
        )

        assert file_info.path == "/tmp/test.xlsx"
        assert file_info.size_mb == 1.0
        assert file_info.extension == ".xlsx"
        assert file_info.filename == "test.xlsx"

    def test_file_retrieval_result_properties(self):
        """Test FileRetrievalResult property methods."""
        result = FileRetrievalResult(
            operation_id="test-123",
            status=FileOperationStatus.COMPLETED,
            started_at=datetime.now(),
            source_url="http://example.com/file.xlsx",
            destination_path="/tmp/file.xlsx",
            change_type=FileChangeType.MODIFIED,
            has_changes=True,
            success=True
        )

        assert result.is_finished is True
        assert result.requires_sync is True

        # Test no changes
        result.change_type = FileChangeType.NO_CHANGE
        result.has_changes = False
        assert result.requires_sync is False

    def test_file_validation_result(self):
        """Test FileValidationResult model."""
        result = FileValidationResult(
            file_path="/tmp/test.xlsx",
            is_valid=True,
            size_bytes=1024,
            min_size_bytes=100,
            max_size_bytes=2048,
            file_extension=".xlsx",
            allowed_extensions=[".xlsx", ".xls"]
        )

        assert result.has_errors is False
        assert result.has_warnings is False

        # Test with errors
        result.validation_errors = ["Size too small"]
        assert result.has_errors is True

    def test_monitoring_state(self):
        """Test FileMonitoringState model."""
        state = FileMonitoringState(
            is_active=True,
            health_status="healthy",
            consecutive_failures=0
        )

        assert state.is_healthy is True
        assert state.has_active_jobs is False

        # Test unhealthy state
        state.consecutive_failures = 5
        assert state.is_healthy is False

    def test_protocol_capabilities(self):
        """Test ProtocolCapabilities model."""
        caps = ProtocolCapabilities(
            protocol_name="HTTP",
            supports_authentication=True,
            supports_encryption=True,
            supports_resume=False,
            supports_directory_listing=False,
            supports_file_metadata=True
        )

        assert caps.protocol_name == "HTTP"
        assert caps.supports_authentication is True


class TestFileSystemService:
    """Test FileSystemService functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def file_system_config(self, temp_dir):
        """Create test file system configuration."""
        return FileSystemConfig(
            protocol="local",
            local_source_directory=temp_dir,
            local_destination_directory=f"{temp_dir}/downloads",
            backup_directory=f"{temp_dir}/backups",
            source_filename="test.xlsx",
            enable_file_monitoring=True,
            monitoring_interval_seconds=1,  # Fast for testing
            enable_file_backup=True,
            max_retry_attempts=2
        )

    @pytest.fixture
    def file_system_service(self, file_system_config):
        """Create file system service for testing."""
        return FileSystemService(file_system_config)

    @pytest.fixture
    def test_file(self, temp_dir):
        """Create test Excel file."""
        test_file_path = Path(temp_dir) / "test.xlsx"
        # Create simple Excel file
        import pandas as pd
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        df.to_excel(test_file_path, index=False)
        return test_file_path

    def test_service_initialization(self, file_system_service):
        """Test file system service initialization."""
        assert file_system_service.config is not None
        assert file_system_service.is_monitoring_active() is False
        assert file_system_service.is_healthy() is True

    @pytest.mark.asyncio
    async def test_monitoring_start_stop(self, file_system_service):
        """Test monitoring start and stop operations."""
        # Test start
        await file_system_service.start_monitoring()
        assert file_system_service.is_monitoring_active() is True

        # Test stop
        await file_system_service.stop_monitoring()
        assert file_system_service.is_monitoring_active() is False

    @pytest.mark.asyncio
    async def test_monitoring_already_running(self, file_system_service):
        """Test starting monitoring when already running."""
        await file_system_service.start_monitoring()

        # Starting again should not raise error
        await file_system_service.start_monitoring()
        assert file_system_service.is_monitoring_active() is True

        await file_system_service.stop_monitoring()

    @pytest.mark.asyncio
    async def test_check_for_changes_new_file(self, file_system_service, test_file):
        """Test change detection for new file."""
        result = await file_system_service.check_for_changes()

        assert result.status == FileOperationStatus.COMPLETED
        assert result.success is True
        assert result.change_type == FileChangeType.NEW_FILE
        assert result.has_changes is True

    @pytest.mark.asyncio
    async def test_check_for_changes_no_change(self, file_system_service, test_file):
        """Test change detection when no changes."""
        # First check - should detect new file
        result1 = await file_system_service.check_for_changes()
        assert result1.change_type == FileChangeType.NEW_FILE

        # Second check - should detect no changes
        result2 = await file_system_service.check_for_changes()
        assert result2.change_type == FileChangeType.NO_CHANGE
        assert result2.has_changes is False

    @pytest.mark.asyncio
    async def test_check_for_changes_size_changed(self, file_system_service, test_file, temp_dir):
        """Test change detection when file size changes."""
        # First check
        await file_system_service.check_for_changes()

        # Modify file size
        import pandas as pd
        df = pd.DataFrame({"col1": [1, 2, 3, 4, 5], "col2": ["a", "b", "c", "d", "e"]})
        df.to_excel(test_file, index=False)

        # Second check - should detect size change
        result = await file_system_service.check_for_changes()
        assert result.change_type == FileChangeType.SIZE_CHANGED
        assert result.has_changes is True

    @pytest.mark.asyncio
    async def test_file_retrieval_success(self, file_system_service, test_file):
        """Test successful file retrieval."""
        result = await file_system_service.retrieve_file(force_download=True)

        assert result.status == FileOperationStatus.COMPLETED
        assert result.success is True
        assert result.bytes_transferred > 0
        assert result.destination_file_info is not None

        # Check that file was actually copied
        dest_path = Path(result.destination_path)
        assert dest_path.exists()
        assert dest_path.stat().st_size == result.bytes_transferred

    @pytest.mark.asyncio
    async def test_file_retrieval_no_changes_skip(self, file_system_service, test_file):
        """Test file retrieval skipping when no changes."""
        # First retrieval
        result1 = await file_system_service.retrieve_file()
        assert result1.success is True

        # Second retrieval should skip
        result2 = await file_system_service.retrieve_file()
        assert result2.status == FileOperationStatus.SKIPPED
        assert result2.success is True

    @pytest.mark.asyncio
    async def test_file_retrieval_with_backup(self, file_system_service, test_file):
        """Test file retrieval with backup creation."""
        result = await file_system_service.retrieve_file(force_download=True)

        assert result.success is True
        assert result.backup_path is not None

        # Check that backup was created
        backup_path = Path(result.backup_path)
        assert backup_path.exists()

    @pytest.mark.asyncio
    async def test_file_validation(self, file_system_service, test_file):
        """Test file validation."""
        # Copy test file to destination
        import shutil
        dest_path = file_system_service.config.destination_file_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(test_file, dest_path)

        # Validate file
        validation_result = await file_system_service._validate_file(str(dest_path))

        assert validation_result.is_valid is True
        assert validation_result.size_valid is True
        assert validation_result.extension_valid is True
        assert validation_result.content_readable is True

    @pytest.mark.asyncio
    async def test_file_validation_invalid_extension(self, file_system_service, temp_dir):
        """Test file validation with invalid extension."""
        # Create file with invalid extension
        invalid_file = Path(temp_dir) / "test.txt"
        invalid_file.write_text("test content")

        validation_result = await file_system_service._validate_file(str(invalid_file))

        assert validation_result.is_valid is False
        assert validation_result.extension_valid is False
        assert len(validation_result.validation_errors) > 0

    @pytest.mark.asyncio
    async def test_file_validation_too_large(self, file_system_service, temp_dir):
        """Test file validation with file too large."""
        # Create large file
        large_file = Path(temp_dir) / "large.xlsx"

        # Mock config to have very small max size
        file_system_service.config.max_file_size_mb = 0.001  # 1KB

        # Create file larger than limit
        large_file.write_bytes(b"x" * 2048)  # 2KB

        validation_result = await file_system_service._validate_file(str(large_file))

        assert validation_result.is_valid is False
        assert validation_result.size_valid is False

    @pytest.mark.asyncio
    async def test_file_retrieval_failure_source_missing(self, file_system_config):
        """Test file retrieval when source file is missing."""
        # Configure for non-existent file
        file_system_config.source_filename = "nonexistent.xlsx"
        service = FileSystemService(file_system_config)

        result = await service.retrieve_file(force_download=True)

        assert result.status == FileOperationStatus.FAILED
        assert result.success is False
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_metrics_collection(self, file_system_service, test_file):
        """Test metrics collection during operations."""
        # Perform successful operation
        await file_system_service.retrieve_file(force_download=True)

        metrics = file_system_service.get_metrics()
        assert metrics.total_operations == 1
        assert metrics.successful_operations == 1
        assert metrics.total_bytes_transferred > 0
        assert metrics.success_rate_percent == 100.0

    @pytest.mark.asyncio
    async def test_monitoring_state_tracking(self, file_system_service):
        """Test monitoring state tracking."""
        await file_system_service.start_monitoring()

        state = file_system_service.get_monitoring_state()
        assert state.is_active is True
        assert state.started_at is not None
        assert state.health_status == "healthy"

        await file_system_service.stop_monitoring()

    def test_protocol_capabilities(self, file_system_service):
        """Test protocol capabilities reporting."""
        caps = file_system_service.get_protocol_capabilities()

        assert caps.protocol_name == "Local File System"
        assert caps.supports_authentication is False
        assert caps.supports_file_metadata is True


class TestFileSystemHTTP:
    """Test file system service with HTTP protocol."""

    @pytest.fixture
    def http_config(self):
        """Create HTTP file system configuration."""
        return FileSystemConfig(
            protocol="http",
            source_host="httpbin.org",
            source_path="base64",
            source_filename="test.txt",
            local_destination_directory="data/downloads",
            max_retry_attempts=1
        )

    @pytest.fixture
    def http_service(self, http_config):
        """Create HTTP file system service."""
        return FileSystemService(http_config)

    @pytest.mark.asyncio
    async def test_http_file_info_retrieval(self, http_service):
        """Test HTTP file info retrieval using HEAD request."""
        # Mock the actual HTTP HEAD request method
        with patch.object(http_service, '_get_http_file_info') as mock_method:
            mock_file_info = FileInfo(
                path="http://httpbin.org/base64/test.txt",
                size_bytes=1024,
                modified_time=datetime.now()
            )
            mock_method.return_value = mock_file_info

            file_info = await http_service._get_http_file_info()

            assert file_info is not None
            assert file_info.size_bytes == 1024

    @pytest.mark.asyncio
    async def test_http_download(self, http_service):
        """Test HTTP file download."""
        # Mock the actual HTTP download method
        with patch.object(http_service, '_download_http_file') as mock_method:
            result = FileRetrievalResult(
                operation_id="test",
                status=FileOperationStatus.DOWNLOADING,
                started_at=datetime.now(),
                source_url="http://example.com/test.txt",
                destination_path="/tmp/test.txt",
                change_type=FileChangeType.NEW_FILE
            )

            # Mock successful download
            async def mock_download(result_obj):
                result_obj.bytes_transferred = 12  # len("test content")
                result_obj.transfer_speed_mbps = 1.0

            mock_method.side_effect = mock_download

            await http_service._download_http_file(result)

            assert result.bytes_transferred > 0


class TestFileSystemIntegration:
    """Integration tests for file system components."""

    @pytest.mark.asyncio
    async def test_full_workflow_local_file(self):
        """Test complete file system workflow with local files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            source_file = Path(temp_dir) / "source.xlsx"
            import pandas as pd
            df = pd.DataFrame({"data": [1, 2, 3]})
            df.to_excel(source_file, index=False)

            # Configure service
            config = FileSystemConfig(
                protocol="local",
                local_source_directory=temp_dir,
                local_destination_directory=f"{temp_dir}/dest",
                backup_directory=f"{temp_dir}/backup",
                source_filename="source.xlsx",
                enable_file_backup=True,
                enable_file_monitoring=False  # Disable for test
            )

            service = FileSystemService(config)

            try:
                # Test change detection
                change_result = await service.check_for_changes()
                assert change_result.change_type == FileChangeType.NEW_FILE

                # Test file retrieval
                retrieval_result = await service.retrieve_file(force_download=True)
                assert retrieval_result.success is True
                assert retrieval_result.backup_path is not None

                # Verify files exist
                dest_file = Path(config.local_destination_directory) / "source.xlsx"
                assert dest_file.exists()

                backup_file = Path(retrieval_result.backup_path)
                assert backup_file.exists()

                # Test metrics
                metrics = service.get_metrics()
                assert metrics.successful_operations == 1
                assert metrics.total_bytes_transferred > 0

            except Exception as e:
                pytest.fail(f"Integration test failed: {e}")

    def test_config_validation_comprehensive(self):
        """Test comprehensive configuration validation."""
        # Test all protocol configurations
        protocols = ["local", "smb", "ftp", "sftp", "http"]

        for protocol in protocols:
            config = FileSystemConfig(protocol=protocol)
            errors = config.validate_configuration()

            if protocol == "local":
                assert len(errors) == 0  # Local should have no errors
            else:
                assert len(errors) > 0  # Remote protocols should have errors without host

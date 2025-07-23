"""
File System Service for retrieving files from various sources.

Supports multiple protocols (SMB, FTP, SFTP, HTTP, local) with change monitoring.
"""

from __future__ import annotations

import asyncio
import shutil
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import aiofiles
import aiohttp
from loguru import logger
from tenacity import (
    AsyncRetrying,
    RetryError,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import FileSystemConfig
from .models import (
    FileChangeType,
    FileInfo,
    FileMonitoringState,
    FileOperationStatus,
    FileRetrievalResult,
    FileSystemMetrics,
    FileValidationResult,
    ProtocolCapabilities,
)


class FileSystemService:
    """
    File system service for retrieving files from various sources.

    Features:
    - Multiple protocol support (local, HTTP, SMB, FTP, SFTP)
    - File change monitoring with different detection methods
    - Automatic retry with exponential backoff
    - File validation and integrity checking
    - Backup and versioning support
    - Comprehensive metrics and monitoring
    """

    def __init__(self, config: FileSystemConfig) -> None:
        """Initialize file system service."""
        self.config = config

        # State management
        self._monitoring_state = FileMonitoringState()
        self._metrics = FileSystemMetrics(
            period_start=datetime.now(),
            period_end=datetime.now() + timedelta(days=1)
        )

        # File tracking
        self._previous_file_info: dict[str, FileInfo] = {}
        self._monitoring_task: asyncio.Task | None = None

        # Ensure directories exist
        self._ensure_directories()

        logger.info(f"FileSystemService initialized with protocol: {config.protocol}")

    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        if self.config.create_destination_directory:
            Path(self.config.local_destination_directory).mkdir(parents=True, exist_ok=True)

        if self.config.enable_file_backup:
            Path(self.config.backup_directory).mkdir(parents=True, exist_ok=True)

    async def start_monitoring(self) -> None:
        """Start file monitoring if enabled."""
        if not self.config.enable_file_monitoring:
            logger.info("File monitoring is disabled")
            return

        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("File monitoring is already running")
            return

        logger.info("Starting file monitoring...")

        self._monitoring_state.is_active = True
        self._monitoring_state.started_at = datetime.now()
        self._monitoring_state.health_status = "healthy"

        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        logger.info("✅ File monitoring started successfully")

    async def stop_monitoring(self) -> None:
        """Stop file monitoring."""
        if not self._monitoring_task:
            logger.info("File monitoring is not running")
            return

        logger.info("Stopping file monitoring...")

        self._monitoring_state.is_active = False

        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        self._monitoring_task = None
        logger.info("✅ File monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        try:
            while self._monitoring_state.is_active:
                await self._perform_monitoring_check()

                # Calculate next check time
                next_check = datetime.now() + timedelta(seconds=self.config.monitoring_interval_seconds)
                self._monitoring_state.next_check_at = next_check

                # Wait for next check
                await asyncio.sleep(self.config.monitoring_interval_seconds)

        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            self._monitoring_state.health_status = "error"
            self._monitoring_state.last_error = str(e)
            self._monitoring_state.last_error_time = datetime.now()

    async def _perform_monitoring_check(self) -> None:
        """Perform a single monitoring check."""
        try:
            self._monitoring_state.last_check_at = datetime.now()
            self._monitoring_state.total_checks += 1

            # Check for file changes
            result = await self.check_for_changes()

            if result.has_changes:
                logger.info(f"File changes detected: {result.change_type}")
                self._monitoring_state.changes_detected += 1

                # Optionally trigger automatic download
                # This could be configured as auto_download_on_change
                # For now, we just log the detection

            # Reset consecutive failures on successful check
            self._monitoring_state.consecutive_failures = 0

        except Exception as e:
            logger.error(f"Error during monitoring check: {e}")
            self._monitoring_state.consecutive_failures += 1
            self._monitoring_state.last_error = str(e)
            self._monitoring_state.last_error_time = datetime.now()

            # Update health status if too many failures
            if self._monitoring_state.consecutive_failures >= 3:
                self._monitoring_state.health_status = "unhealthy"

    async def check_for_changes(self) -> FileRetrievalResult:
        """Check for file changes without downloading."""
        operation_id = str(uuid.uuid4())

        result = FileRetrievalResult(
            operation_id=operation_id,
            status=FileOperationStatus.PENDING,
            started_at=datetime.now(),
            source_url=self.config.full_source_url,
            destination_path=str(self.config.destination_file_path),
            change_type=FileChangeType.NO_CHANGE,
        )

        try:
            # Get current file info from source
            source_info = await self._get_source_file_info()
            result.source_file_info = source_info

            # Get previous file info
            source_key = self.config.full_source_url
            previous_info = self._previous_file_info.get(source_key)
            result.previous_file_info = previous_info

            # Detect changes
            change_type = self._detect_changes(source_info, previous_info)
            result.change_type = change_type
            result.has_changes = change_type != FileChangeType.NO_CHANGE

            # Update previous file info
            if source_info:
                self._previous_file_info[source_key] = source_info

            result.status = FileOperationStatus.COMPLETED
            result.success = True
            result.completed_at = datetime.now()

            logger.info(f"Change detection completed: {change_type}")

        except Exception as e:
            result.status = FileOperationStatus.FAILED
            result.success = False
            result.error_message = str(e)
            result.completed_at = datetime.now()

            logger.error(f"Change detection failed: {e}")

        finally:
            if result.completed_at:
                result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

        return result

    async def retrieve_file(self, force_download: bool = False) -> FileRetrievalResult:
        """Retrieve file from source with retry logic."""
        operation_id = str(uuid.uuid4())

        result = FileRetrievalResult(
            operation_id=operation_id,
            status=FileOperationStatus.PENDING,
            started_at=datetime.now(),
            source_url=self.config.full_source_url,
            destination_path=str(self.config.destination_file_path),
            change_type=FileChangeType.NO_CHANGE,
            max_attempts=self.config.max_retry_attempts,
        )

        logger.info(f"🚀 Starting file retrieval {operation_id}")
        logger.info(f"Source: {result.source_url}")
        logger.info(f"Destination: {result.destination_path}")

        try:
            # Execute with retry logic
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.config.max_retry_attempts),
                wait=wait_exponential(
                    multiplier=self.config.retry_delay_seconds,
                    max=300,  # Max 5 minutes between retries
                ),
                retry=retry_if_exception_type(Exception),
                before_sleep=before_sleep_log(logger, "WARNING"),
                reraise=True,
            ):
                with attempt:
                    result.attempt_number = attempt.retry_state.attempt_number
                    result.status = FileOperationStatus.DOWNLOADING

                    # Check for changes first (unless forced)
                    if not force_download:
                        change_result = await self.check_for_changes()
                        result.change_type = change_result.change_type
                        result.has_changes = change_result.has_changes
                        result.source_file_info = change_result.source_file_info

                        if not result.has_changes:
                            result.status = FileOperationStatus.SKIPPED
                            result.success = True
                            logger.info("File has no changes, skipping download")
                            return result

                    # Perform actual download
                    await self._download_file(result)

                    # Validate downloaded file
                    if self.config.validate_file_integrity:
                        validation_result = await self._validate_file(result.destination_path)
                        result.validation_passed = validation_result.is_valid
                        result.validation_errors = validation_result.validation_errors

                        if not validation_result.is_valid:
                            raise ValueError(f"File validation failed: {', '.join(validation_result.validation_errors)}")

                    # Create backup if enabled
                    if self.config.enable_file_backup:
                        backup_path = await self._create_backup(result.destination_path)
                        result.backup_path = str(backup_path)
                        logger.info(f"Backup created: {backup_path}")

            # Download completed successfully
            result.status = FileOperationStatus.COMPLETED
            result.success = True
            result.completed_at = datetime.now()

            # Update metrics
            self._update_success_metrics(result)
            self._monitoring_state.successful_retrievals += 1

            logger.info(f"✅ File retrieval {operation_id} completed successfully")

        except RetryError as e:
            # All retry attempts failed
            result.status = FileOperationStatus.FAILED
            result.success = False
            result.completed_at = datetime.now()
            result.error_message = f"File retrieval failed after {self.config.max_retry_attempts} attempts: {str(e.last_attempt.exception())}"
            result.error_details = {
                "exception_type": type(e.last_attempt.exception()).__name__,
                "last_attempt": str(e.last_attempt.exception()),
                "total_attempts": self.config.max_retry_attempts,
            }

            logger.error(f"❌ File retrieval {operation_id} failed after {self.config.max_retry_attempts} attempts")

            # Update metrics
            self._update_failure_metrics(result)
            self._monitoring_state.failed_retrievals += 1

        except Exception as e:
            # Unexpected error
            result.status = FileOperationStatus.FAILED
            result.success = False
            result.completed_at = datetime.now()
            result.error_message = f"Unexpected error: {str(e)}"
            result.error_details = {"exception_type": type(e).__name__, "details": str(e)}

            logger.error(f"❌ Unexpected error in file retrieval {operation_id}: {e}")

            # Update metrics
            self._update_failure_metrics(result)
            self._monitoring_state.failed_retrievals += 1

        finally:
            if result.completed_at:
                result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

        return result

    async def _get_source_file_info(self) -> FileInfo | None:
        """Get file information from source."""
        if self.config.protocol == "local":
            return await self._get_local_file_info()
        elif self.config.protocol == "http":
            return await self._get_http_file_info()
        else:
            # For other protocols, return None (would be implemented with actual protocol clients)
            logger.warning(f"File info retrieval not implemented for protocol: {self.config.protocol}")
            return None

    async def _get_local_file_info(self) -> FileInfo | None:
        """Get file information from local filesystem."""
        try:
            file_path = Path(self.config.full_source_url)
            if not file_path.exists():
                return None

            stat = file_path.stat()
            return FileInfo(
                path=str(file_path),
                size_bytes=stat.st_size,
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                created_time=datetime.fromtimestamp(stat.st_ctime),
            )
        except Exception as e:
            logger.error(f"Error getting local file info: {e}")
            return None

    async def _get_http_file_info(self) -> FileInfo | None:
        """Get file information from HTTP source using HEAD request."""
        try:
            headers = self.config.http_headers.copy()
            if self.config.http_auth_type == "bearer" and self.config.http_auth_token:
                headers["Authorization"] = f"Bearer {self.config.http_auth_token}"

            timeout = aiohttp.ClientTimeout(total=self.config.connection_timeout_seconds)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.head(
                    self.config.full_source_url,
                    headers=headers,
                    ssl=self.config.http_verify_ssl
                ) as response:
                    response.raise_for_status()

                    # Extract file information from headers
                    size_bytes = int(response.headers.get("Content-Length", 0))

                    # Try to parse last modified from headers
                    modified_time = datetime.now()
                    if "Last-Modified" in response.headers:
                        try:
                            from email.utils import parsedate_to_datetime
                            modified_time = parsedate_to_datetime(response.headers["Last-Modified"])
                        except Exception:
                            pass

                    return FileInfo(
                        path=self.config.full_source_url,
                        size_bytes=size_bytes,
                        modified_time=modified_time,
                    )

        except Exception as e:
            logger.error(f"Error getting HTTP file info: {e}")
            return None

    def _detect_changes(self, current_info: FileInfo | None, previous_info: FileInfo | None) -> FileChangeType:
        """Detect changes between current and previous file info."""
        if current_info is None:
            return FileChangeType.FILE_MISSING

        if previous_info is None:
            return FileChangeType.NEW_FILE

        # Check based on configured detection method
        method = self.config.file_change_detection_method

        if method in ["size", "both"] and current_info.size_bytes != previous_info.size_bytes:
            return FileChangeType.SIZE_CHANGED

        if method in ["timestamp", "both"] and current_info.modified_time != previous_info.modified_time:
            return FileChangeType.TIMESTAMP_CHANGED

        if method == "hash":
            # For hash comparison, we would need to download and compare hashes
            # This is more expensive but more accurate
            logger.warning("Hash-based change detection not implemented yet")

        return FileChangeType.NO_CHANGE

    async def _download_file(self, result: FileRetrievalResult) -> None:
        """Download file based on configured protocol."""
        if self.config.protocol == "local":
            await self._download_local_file(result)
        elif self.config.protocol == "http":
            await self._download_http_file(result)
        else:
            # Placeholder for other protocols
            raise NotImplementedError(f"Download not implemented for protocol: {self.config.protocol}")

    async def _download_local_file(self, result: FileRetrievalResult) -> None:
        """Download (copy) file from local filesystem."""
        source_path = Path(self.config.full_source_url)
        dest_path = Path(result.destination_path)

        start_time = time.time()

        # Use async file operations for large files
        if source_path.stat().st_size > 10 * 1024 * 1024:  # 10MB
            async with aiofiles.open(source_path, "rb") as src:
                async with aiofiles.open(dest_path, "wb") as dst:
                    while chunk := await src.read(64 * 1024):  # 64KB chunks
                        await dst.write(chunk)
                        result.bytes_transferred += len(chunk)
        else:
            # Use synchronous copy for smaller files
            shutil.copy2(source_path, dest_path)
            result.bytes_transferred = source_path.stat().st_size

        # Calculate transfer speed
        duration = time.time() - start_time
        if duration > 0:
            mb_per_second = (result.bytes_transferred / (1024 * 1024)) / duration
            result.transfer_speed_mbps = round(mb_per_second, 2)

        # Get destination file info
        result.destination_file_info = FileInfo(
            path=str(dest_path),
            size_bytes=dest_path.stat().st_size,
            modified_time=datetime.fromtimestamp(dest_path.stat().st_mtime),
            created_time=datetime.fromtimestamp(dest_path.stat().st_ctime),
        )

    async def _download_http_file(self, result: FileRetrievalResult) -> None:
        """Download file from HTTP source."""
        headers = self.config.http_headers.copy()
        if self.config.http_auth_type == "bearer" and self.config.http_auth_token:
            headers["Authorization"] = f"Bearer {self.config.http_auth_token}"

        timeout = aiohttp.ClientTimeout(
            total=self.config.read_timeout_seconds,
            connect=self.config.connection_timeout_seconds
        )

        start_time = time.time()

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                self.config.full_source_url,
                headers=headers,
                ssl=self.config.http_verify_ssl
            ) as response:
                response.raise_for_status()

                dest_path = Path(result.destination_path)

                async with aiofiles.open(dest_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(64 * 1024):  # 64KB chunks
                        await f.write(chunk)
                        result.bytes_transferred += len(chunk)

        # Calculate transfer speed
        duration = time.time() - start_time
        if duration > 0:
            mb_per_second = (result.bytes_transferred / (1024 * 1024)) / duration
            result.transfer_speed_mbps = round(mb_per_second, 2)

        # Get destination file info
        dest_path = Path(result.destination_path)
        result.destination_file_info = FileInfo(
            path=str(dest_path),
            size_bytes=dest_path.stat().st_size,
            modified_time=datetime.fromtimestamp(dest_path.stat().st_mtime),
            created_time=datetime.fromtimestamp(dest_path.stat().st_ctime),
        )

    async def _validate_file(self, file_path: str) -> FileValidationResult:
        """Validate downloaded file."""
        file_path_obj = Path(file_path)

        result = FileValidationResult(
            file_path=file_path,
            is_valid=True,
            size_bytes=0,
            min_size_bytes=self.config.min_file_size_bytes,
            max_size_bytes=int(self.config.max_file_size_mb * 1024 * 1024),
            file_extension="",
            allowed_extensions=self.config.expected_file_extensions,
        )

        try:
            # Check if file exists
            if not file_path_obj.exists():
                result.is_valid = False
                result.validation_errors.append("File does not exist")
                return result

            # Size validation
            stat = file_path_obj.stat()
            result.size_bytes = stat.st_size

            if result.size_bytes < result.min_size_bytes:
                result.size_valid = False
                result.is_valid = False
                result.validation_errors.append(f"File too small: {result.size_bytes} < {result.min_size_bytes} bytes")

            if result.size_bytes > result.max_size_bytes:
                result.size_valid = False
                result.is_valid = False
                result.validation_errors.append(f"File too large: {result.size_bytes} > {result.max_size_bytes} bytes")

            # Extension validation
            result.file_extension = file_path_obj.suffix.lower()
            if result.allowed_extensions and result.file_extension not in result.allowed_extensions:
                result.extension_valid = False
                result.is_valid = False
                result.validation_errors.append(f"Invalid extension: {result.file_extension} not in {result.allowed_extensions}")

            # Content validation (basic readability check)
            try:
                if result.file_extension in [".xlsx", ".xls"]:
                    # Try to open as Excel file
                    import pandas as pd
                    pd.read_excel(file_path, nrows=1)  # Just read first row to check
                else:
                    # Try to read as text/binary
                    with open(file_path, "rb") as f:
                        f.read(1024)  # Read first 1KB

            except Exception as e:
                result.content_readable = False
                result.is_valid = False
                result.content_errors.append(str(e))
                result.validation_errors.append(f"Content validation failed: {e}")

        except Exception as e:
            result.is_valid = False
            result.validation_errors.append(f"Validation error: {e}")

        return result

    async def _create_backup(self, file_path: str) -> Path:
        """Create backup of file with timestamp."""
        source_path = Path(file_path)
        backup_path = self.config.backup_file_path

        # Ensure backup directory exists
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file to backup location
        shutil.copy2(source_path, backup_path)

        return backup_path

    def _update_success_metrics(self, result: FileRetrievalResult) -> None:
        """Update metrics for successful operation."""
        self._metrics.total_operations += 1
        self._metrics.successful_operations += 1
        self._metrics.total_bytes_transferred += result.bytes_transferred

        # Update protocol usage
        protocol = self.config.protocol
        self._metrics.protocol_usage[protocol] = self._metrics.protocol_usage.get(protocol, 0) + 1

        # Update transfer speed
        if result.transfer_speed_mbps > 0:
            if self._metrics.average_transfer_speed_mbps == 0:
                self._metrics.average_transfer_speed_mbps = result.transfer_speed_mbps
            else:
                # Simple moving average
                self._metrics.average_transfer_speed_mbps = (
                    self._metrics.average_transfer_speed_mbps + result.transfer_speed_mbps
                ) / 2

        # Update operation times
        if result.duration_seconds:
            if self._metrics.average_operation_time_seconds == 0:
                self._metrics.average_operation_time_seconds = result.duration_seconds
                self._metrics.fastest_operation_seconds = result.duration_seconds
                self._metrics.slowest_operation_seconds = result.duration_seconds
            else:
                # Update average
                total_ops = self._metrics.successful_operations
                total_time = self._metrics.average_operation_time_seconds * (total_ops - 1)
                self._metrics.average_operation_time_seconds = (total_time + result.duration_seconds) / total_ops

                # Update min/max
                self._metrics.fastest_operation_seconds = min(self._metrics.fastest_operation_seconds, result.duration_seconds)
                self._metrics.slowest_operation_seconds = max(self._metrics.slowest_operation_seconds, result.duration_seconds)

    def _update_failure_metrics(self, result: FileRetrievalResult) -> None:
        """Update metrics for failed operation."""
        self._metrics.total_operations += 1
        self._metrics.failed_operations += 1

        # Update error tracking
        if result.error_details.get("exception_type"):
            error_type = result.error_details["exception_type"]
            if error_type not in self._metrics.most_common_errors:
                self._metrics.most_common_errors.append(error_type)

        # Update error rate
        if self._metrics.total_operations > 0:
            self._metrics.error_rate_percent = (self._metrics.failed_operations / self._metrics.total_operations) * 100.0

    # Public API methods

    def get_monitoring_state(self) -> FileMonitoringState:
        """Get current monitoring state."""
        return self._monitoring_state

    def get_metrics(self) -> FileSystemMetrics:
        """Get file system metrics."""
        return self._metrics

    def get_protocol_capabilities(self) -> ProtocolCapabilities:
        """Get capabilities of current protocol."""
        protocol = self.config.protocol

        if protocol == "local":
            return ProtocolCapabilities(
                protocol_name="Local File System",
                supports_authentication=False,
                supports_encryption=False,
                supports_resume=False,
                supports_directory_listing=True,
                supports_file_metadata=True,
                features={"fast": True, "reliable": True},
                recommended_for=["development", "testing", "local files"],
            )
        elif protocol == "http":
            return ProtocolCapabilities(
                protocol_name="HTTP/HTTPS",
                supports_authentication=True,
                supports_encryption=True,
                supports_resume=False,
                supports_directory_listing=False,
                supports_file_metadata=True,
                auth_methods=["bearer", "basic"],
                features={"widely_supported": True, "simple": True},
                recommended_for=["web APIs", "cloud storage", "simple downloads"],
            )
        else:
            return ProtocolCapabilities(
                protocol_name=protocol.upper(),
                supports_authentication=True,
                supports_encryption=True,
                supports_resume=False,
                supports_directory_listing=True,
                supports_file_metadata=True,
                limitations=["Not implemented yet"],
            )

    def is_monitoring_active(self) -> bool:
        """Check if monitoring is active."""
        return self._monitoring_state.is_active

    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        return self._monitoring_state.is_healthy

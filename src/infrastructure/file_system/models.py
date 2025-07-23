"""
Models for file system operations.

Contains Pydantic models for file retrieval results, monitoring and metrics.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, computed_field


class FileOperationStatus(str, Enum):
    """Status of file operation."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    VALIDATED = "validated"
    BACKUP_CREATED = "backup_created"


class FileChangeType(str, Enum):
    """Type of file change detected."""

    NEW_FILE = "new_file"
    MODIFIED = "modified"
    SIZE_CHANGED = "size_changed"
    TIMESTAMP_CHANGED = "timestamp_changed"
    HASH_CHANGED = "hash_changed"
    NO_CHANGE = "no_change"
    FILE_MISSING = "file_missing"


class FileInfo(BaseModel):
    """Information about a file."""

    path: str = Field(..., description="File path")
    size_bytes: int = Field(..., description="File size in bytes")
    modified_time: datetime = Field(..., description="Last modified time")
    created_time: datetime | None = Field(None, description="Creation time")
    hash_md5: str | None = Field(None, description="MD5 hash of file content")
    hash_sha256: str | None = Field(None, description="SHA256 hash of file content")

    @computed_field
    @property
    def size_mb(self) -> float:
        """File size in megabytes."""
        return round(self.size_bytes / (1024 * 1024), 2)

    @computed_field
    @property
    def extension(self) -> str:
        """File extension."""
        return Path(self.path).suffix.lower()

    @computed_field
    @property
    def filename(self) -> str:
        """File name without path."""
        return Path(self.path).name

    def calculate_hash(self, algorithm: str = "md5") -> str:
        """Calculate file hash."""
        if not Path(self.path).exists():
            raise FileNotFoundError(f"File not found: {self.path}")

        hash_obj = hashlib.md5() if algorithm == "md5" else hashlib.sha256()

        with open(self.path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)

        return hash_obj.hexdigest()

    def update_hashes(self) -> None:
        """Update file hashes."""
        if Path(self.path).exists():
            self.hash_md5 = self.calculate_hash("md5")
            self.hash_sha256 = self.calculate_hash("sha256")


class FileRetrievalResult(BaseModel):
    """Result of file retrieval operation."""

    # Operation details
    operation_id: str = Field(..., description="Unique operation identifier")
    status: FileOperationStatus = Field(..., description="Operation status")
    started_at: datetime = Field(..., description="Operation start time")
    completed_at: datetime | None = Field(None, description="Operation completion time")
    duration_seconds: float | None = Field(None, description="Operation duration")

    # Source and destination
    source_url: str = Field(..., description="Source file URL")
    destination_path: str = Field(..., description="Local destination path")
    backup_path: str | None = Field(None, description="Backup file path")

    # File information
    source_file_info: FileInfo | None = Field(None, description="Source file information")
    destination_file_info: FileInfo | None = Field(None, description="Downloaded file information")
    previous_file_info: FileInfo | None = Field(None, description="Previous file information")

    # Change detection
    change_type: FileChangeType = Field(..., description="Type of change detected")
    has_changes: bool = Field(default=False, description="Whether file has changes")
    change_details: dict[str, Any] = Field(default_factory=dict, description="Detailed change information")

    # Transfer metrics
    bytes_transferred: int = Field(default=0, description="Bytes transferred")
    transfer_speed_mbps: float = Field(default=0.0, description="Transfer speed in MB/s")

    # Validation results
    validation_passed: bool = Field(default=False, description="File validation result")
    validation_errors: list[str] = Field(default_factory=list, description="Validation errors")

    # Error information
    success: bool = Field(default=False, description="Whether operation succeeded")
    error_message: str | None = Field(None, description="Error message if failed")
    error_details: dict[str, Any] = Field(default_factory=dict, description="Detailed error information")

    # Retry information
    attempt_number: int = Field(default=1, description="Current attempt number")
    max_attempts: int = Field(default=3, description="Maximum allowed attempts")

    @computed_field
    @property
    def transfer_size_mb(self) -> float:
        """Transfer size in megabytes."""
        return round(self.bytes_transferred / (1024 * 1024), 2)

    @property
    def is_finished(self) -> bool:
        """Check if operation has finished."""
        return self.status in {
            FileOperationStatus.COMPLETED,
            FileOperationStatus.FAILED,
            FileOperationStatus.SKIPPED
        }

    @property
    def requires_sync(self) -> bool:
        """Check if file changes require synchronization."""
        return (
            self.has_changes
            and self.change_type != FileChangeType.NO_CHANGE
            and self.success
        )


class FileMonitoringState(BaseModel):
    """State of file monitoring."""

    # Monitoring status
    is_active: bool = Field(default=False, description="Whether monitoring is active")
    started_at: datetime | None = Field(None, description="Monitoring start time")
    last_check_at: datetime | None = Field(None, description="Last monitoring check time")
    next_check_at: datetime | None = Field(None, description="Next scheduled check time")

    # Monitored files
    monitored_files: dict[str, FileInfo] = Field(
        default_factory=dict, description="Currently monitored files"
    )

    # Detection statistics
    total_checks: int = Field(default=0, description="Total monitoring checks")
    changes_detected: int = Field(default=0, description="Number of changes detected")
    successful_retrievals: int = Field(default=0, description="Successful file retrievals")
    failed_retrievals: int = Field(default=0, description="Failed file retrievals")

    # Error tracking
    consecutive_failures: int = Field(default=0, description="Consecutive failure count")
    last_error: str | None = Field(None, description="Last error message")
    last_error_time: datetime | None = Field(None, description="Last error time")

    # Health status
    health_status: str = Field(default="healthy", description="Overall health status")

    @property
    def is_healthy(self) -> bool:
        """Check if monitoring is in healthy state."""
        return (
            self.health_status == "healthy"
            and self.consecutive_failures < 3
        )

    @property
    def has_active_jobs(self) -> bool:
        """Check if there are active jobs."""
        return len(self.monitored_files) > 0


class FileSystemMetrics(BaseModel):
    """File system operation metrics."""

    # Time period
    period_start: datetime = Field(..., description="Metrics period start")
    period_end: datetime = Field(..., description="Metrics period end")

    # Operation statistics
    total_operations: int = Field(default=0, description="Total file operations")
    successful_operations: int = Field(default=0, description="Successful operations")
    failed_operations: int = Field(default=0, description="Failed operations")
    skipped_operations: int = Field(default=0, description="Skipped operations")

    # Transfer metrics
    total_bytes_transferred: int = Field(default=0, description="Total bytes transferred")
    average_transfer_speed_mbps: float = Field(default=0.0, description="Average transfer speed")
    largest_file_mb: float = Field(default=0.0, description="Largest file transferred")

    # File change metrics
    files_with_changes: int = Field(default=0, description="Files with detected changes")
    new_files_detected: int = Field(default=0, description="New files detected")
    modified_files_detected: int = Field(default=0, description="Modified files detected")

    # Performance metrics
    average_operation_time_seconds: float = Field(default=0.0, description="Average operation time")
    fastest_operation_seconds: float = Field(default=0.0, description="Fastest operation time")
    slowest_operation_seconds: float = Field(default=0.0, description="Slowest operation time")

    # Error analysis
    most_common_errors: list[str] = Field(default_factory=list, description="Most common error types")
    error_rate_percent: float = Field(default=0.0, description="Error rate percentage")

    # Protocol-specific metrics
    protocol_usage: dict[str, int] = Field(default_factory=dict, description="Usage by protocol")
    protocol_success_rates: dict[str, float] = Field(default_factory=dict, description="Success rates by protocol")

    @computed_field
    @property
    def total_mb_transferred(self) -> float:
        """Total megabytes transferred."""
        return round(self.total_bytes_transferred / (1024 * 1024), 2)

    @computed_field
    @property
    def success_rate_percent(self) -> float:
        """Success rate percentage."""
        if self.total_operations == 0:
            return 0.0
        return (self.successful_operations / self.total_operations) * 100.0


class FileValidationResult(BaseModel):
    """Result of file validation."""

    file_path: str = Field(..., description="Path to validated file")
    is_valid: bool = Field(..., description="Whether file is valid")

    # Size validation
    size_valid: bool = Field(default=True, description="Size validation result")
    size_bytes: int = Field(..., description="Actual file size")
    min_size_bytes: int = Field(..., description="Minimum allowed size")
    max_size_bytes: int = Field(..., description="Maximum allowed size")

    # Extension validation
    extension_valid: bool = Field(default=True, description="Extension validation result")
    file_extension: str = Field(..., description="Actual file extension")
    allowed_extensions: list[str] = Field(..., description="Allowed extensions")

    # Content validation
    content_readable: bool = Field(default=True, description="Whether file content is readable")
    content_errors: list[str] = Field(default_factory=list, description="Content validation errors")

    # Integrity validation
    integrity_valid: bool = Field(default=True, description="File integrity validation result")
    hash_matches: bool | None = Field(None, description="Whether hash matches expected")
    expected_hash: str | None = Field(None, description="Expected file hash")
    actual_hash: str | None = Field(None, description="Actual file hash")

    # Overall validation
    validation_errors: list[str] = Field(default_factory=list, description="All validation errors")
    validation_warnings: list[str] = Field(default_factory=list, description="Validation warnings")

    @property
    def has_errors(self) -> bool:
        """Check if validation has errors."""
        return not self.is_valid or len(self.validation_errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if validation has warnings."""
        return len(self.validation_warnings) > 0


class ProtocolCapabilities(BaseModel):
    """Capabilities of a file transfer protocol."""

    protocol_name: str = Field(..., description="Protocol name")
    supports_authentication: bool = Field(..., description="Supports authentication")
    supports_encryption: bool = Field(..., description="Supports encryption")
    supports_resume: bool = Field(..., description="Supports resume downloads")
    supports_directory_listing: bool = Field(..., description="Supports directory listing")
    supports_file_metadata: bool = Field(..., description="Supports file metadata")

    # Authentication methods
    auth_methods: list[str] = Field(default_factory=list, description="Supported auth methods")

    # Protocol-specific features
    features: dict[str, bool] = Field(default_factory=dict, description="Protocol-specific features")
    limitations: list[str] = Field(default_factory=list, description="Known limitations")

    # Performance characteristics
    typical_speed_range: str = Field(default="", description="Typical speed range")
    recommended_for: list[str] = Field(default_factory=list, description="Recommended use cases")

"""
Models for synchronization orchestration results.

Contains Pydantic models for representing synchronization results and summaries.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..change_detector.models import ChangeDetectionResult
from ..excel_parser.models import ParseResult


class SyncSummary(BaseModel):
    """
    Summary of synchronization operation.

    Contains high-level metrics and status information.
    """

    # Timing
    started_at: datetime = Field(..., description="Sync start time")
    finished_at: datetime | None = Field(default=None, description="Sync finish time")
    duration_seconds: float = Field(default=0.0, description="Total sync duration")

    # File processing
    file_path: str = Field(..., description="Path to processed Excel file")
    file_size_bytes: int = Field(default=0, description="Size of processed file")
    file_hash: str = Field(..., description="Hash of processed file")

    # Data counts
    total_deals_processed: int = Field(default=0, description="Total deals processed")
    total_items_processed: int = Field(default=0, description="Total items processed")

    # Change statistics
    insertions_count: int = Field(default=0, description="Number of insertions")
    updates_count: int = Field(default=0, description="Number of updates")
    deletions_count: int = Field(default=0, description="Number of deletions")

    # Status
    success: bool = Field(default=False, description="Whether sync was successful")
    error_message: str | None = Field(default=None, description="Error message if failed")

    # Performance metrics
    parsing_duration_seconds: float = Field(default=0.0, description="Time spent parsing")
    change_detection_duration_seconds: float = Field(
        default=0.0, description="Time spent on change detection"
    )
    database_update_duration_seconds: float = Field(
        default=0.0, description="Time spent updating database"
    )

    @property
    def total_changes(self) -> int:
        """Total number of changes applied."""
        return self.insertions_count + self.updates_count + self.deletions_count

    @property
    def has_changes(self) -> bool:
        """Check if any changes were applied."""
        return self.total_changes > 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total_processed = self.total_deals_processed + self.total_items_processed
        if total_processed == 0:
            return 0.0

        errors = (
            self.insertions_count + self.updates_count + self.deletions_count
            if not self.success
            else 0
        )
        return ((total_processed - errors) / total_processed) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timing": {
                "started_at": self.started_at.isoformat(),
                "finished_at": self.finished_at.isoformat() if self.finished_at else None,
                "duration_seconds": self.duration_seconds,
                "parsing_duration": self.parsing_duration_seconds,
                "change_detection_duration": self.change_detection_duration_seconds,
                "database_update_duration": self.database_update_duration_seconds,
            },
            "file": {
                "path": self.file_path,
                "size_bytes": self.file_size_bytes,
                "hash": self.file_hash,
            },
            "data": {
                "deals_processed": self.total_deals_processed,
                "items_processed": self.total_items_processed,
            },
            "changes": {
                "insertions": self.insertions_count,
                "updates": self.updates_count,
                "deletions": self.deletions_count,
                "total": self.total_changes,
            },
            "status": {
                "success": self.success,
                "error_message": self.error_message,
                "success_rate": self.success_rate,
            },
        }


class SyncResult(BaseModel):
    """
    Complete result of synchronization operation.

    Contains detailed information about all aspects of the sync process.
    """

    # Session information
    sync_session_id: str = Field(..., description="Unique sync session identifier")
    sync_type: str = Field(..., description="Type of sync (full/incremental)")

    # Summary
    summary: SyncSummary = Field(..., description="High-level sync summary")

    # Detailed results
    parse_result: ParseResult | None = Field(default=None, description="Excel parsing result")
    change_detection_result: ChangeDetectionResult | None = Field(
        default=None, description="Change detection result"
    )

    # Events and audit
    events_created: list[dict[str, Any]] = Field(
        default_factory=list, description="List of events created during sync"
    )

    # Warnings and errors
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
    errors: list[str] = Field(default_factory=list, description="Error messages")

    @property
    def has_errors(self) -> bool:
        """Check if sync had errors."""
        return len(self.errors) > 0 or not self.summary.success

    @property
    def has_warnings(self) -> bool:
        """Check if sync had warnings."""
        return len(self.warnings) > 0

    def add_warning(self, message: str) -> None:
        """Add warning message."""
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        """Add error message."""
        self.errors.append(message)
        self.summary.success = False
        if not self.summary.error_message:
            self.summary.error_message = message

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get detailed performance metrics."""
        metrics = {
            "total_duration": self.summary.duration_seconds,
            "parsing_duration": self.summary.parsing_duration_seconds,
            "change_detection_duration": self.summary.change_detection_duration_seconds,
            "database_update_duration": self.summary.database_update_duration_seconds,
        }

        # Calculate percentages
        total = self.summary.duration_seconds
        if total > 0:
            metrics["parsing_percentage"] = (self.summary.parsing_duration_seconds / total) * 100
            metrics["change_detection_percentage"] = (
                self.summary.change_detection_duration_seconds / total
            ) * 100
            metrics["database_update_percentage"] = (
                self.summary.database_update_duration_seconds / total
            ) * 100

        # Add rates
        if self.summary.duration_seconds > 0:
            metrics["deals_per_second"] = (
                self.summary.total_deals_processed / self.summary.duration_seconds
            )
            metrics["items_per_second"] = (
                self.summary.total_items_processed / self.summary.duration_seconds
            )
            metrics["changes_per_second"] = (
                self.summary.total_changes / self.summary.duration_seconds
            )

        return metrics

    def to_report_dict(self) -> dict[str, Any]:
        """Convert to comprehensive report dictionary."""
        report = {
            "session": {
                "id": self.sync_session_id,
                "type": self.sync_type,
            },
            "summary": self.summary.to_dict(),
            "performance": self.get_performance_metrics(),
            "quality": {
                "warnings_count": len(self.warnings),
                "errors_count": len(self.errors),
                "has_issues": self.has_warnings or self.has_errors,
            },
        }

        # Add parsing stats if available
        if self.parse_result:
            report["parsing"] = {
                "total_deals": self.parse_result.total_deals,
                "total_items": self.parse_result.total_items,
                "success_rate_deals": self.parse_result.stats.success_rate_deals,
                "success_rate_items": self.parse_result.stats.success_rate_items,
                "errors": self.parse_result.stats.errors[:5],  # First 5 errors
                "warnings": self.parse_result.stats.warnings[:5],  # First 5 warnings
            }

        # Add change detection stats if available
        if self.change_detection_result:
            report["change_detection"] = self.change_detection_result.to_summary_dict()

        return report


class SyncConfiguration(BaseModel):
    """
    Configuration for synchronization operation.

    Contains settings that control sync behavior.
    """

    # Sync type and scope
    sync_type: str = Field(..., description="Type of sync (full/incremental)")
    incremental_period_months: int = Field(
        default=3, description="Months to include in incremental sync"
    )

    # Performance settings
    batch_size: int = Field(default=100, description="Batch size for database operations")
    max_retry_attempts: int = Field(
        default=3, description="Maximum retry attempts for failed operations"
    )

    # Validation settings
    enable_1c_validation: bool = Field(default=True, description="Enable validation with 1C system")
    enable_financial_validation: bool = Field(
        default=True, description="Enable financial validation"
    )

    # Event Store settings
    create_events: bool = Field(default=True, description="Create events in event store")
    update_read_models: bool = Field(default=True, description="Update read models")

    # Error handling
    continue_on_errors: bool = Field(
        default=True, description="Continue processing on non-critical errors"
    )
    rollback_on_failure: bool = Field(default=True, description="Rollback transaction on failure")

    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable performance metrics collection")
    log_level: str = Field(default="INFO", description="Logging level")

    def is_full_sync(self) -> bool:
        """Check if this is a full sync."""
        return self.sync_type.lower() == "full"

    def is_incremental_sync(self) -> bool:
        """Check if this is an incremental sync."""
        return self.sync_type.lower() == "incremental"

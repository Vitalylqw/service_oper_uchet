"""
Models for scheduler operations.

Contains Pydantic models for job execution results, metrics and scheduling state.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobExecutionStatus(str, Enum):
    """Status of job execution."""

    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class SyncJobType(str, Enum):
    """Type of synchronization job."""

    INCREMENTAL = "incremental"
    FULL = "full"
    MANUAL = "manual"
    FILE_TRIGGERED = "file_triggered"


class JobExecutionResult(BaseModel):
    """Result of job execution."""

    # Job identification
    job_id: str = Field(..., description="Unique job identifier")
    job_name: str = Field(..., description="Human-readable job name")
    job_type: SyncJobType = Field(..., description="Type of sync job")

    # Execution details
    status: JobExecutionStatus = Field(..., description="Execution status")
    started_at: datetime = Field(..., description="Job start time")
    completed_at: datetime | None = Field(None, description="Job completion time")
    duration_seconds: float | None = Field(None, description="Execution duration")

    # Retry information
    attempt_number: int = Field(default=1, description="Current attempt number")
    max_attempts: int = Field(default=3, description="Maximum allowed attempts")
    next_retry_at: datetime | None = Field(None, description="Next retry scheduled time")

    # Results and errors
    sync_session_id: str | None = Field(None, description="Associated sync session ID")
    success: bool = Field(default=False, description="Whether job completed successfully")
    error_message: str | None = Field(None, description="Error message if failed")
    error_details: dict[str, Any] = Field(default_factory=dict, description="Detailed error information")

    # Metrics
    records_processed: int = Field(default=0, description="Number of records processed")
    changes_detected: int = Field(default=0, description="Number of changes detected")
    events_created: int = Field(default=0, description="Number of events created")

    # Context
    triggered_by: str = Field(default="scheduler", description="What triggered this job")
    file_path: str | None = Field(None, description="File path if applicable")
    configuration: dict[str, Any] = Field(default_factory=dict, description="Job configuration")

    @property
    def is_finished(self) -> bool:
        """Check if job has finished (either success or failure)."""
        return self.status in {JobExecutionStatus.COMPLETED, JobExecutionStatus.FAILED, JobExecutionStatus.CANCELLED}

    @property
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return (
            self.status == JobExecutionStatus.FAILED
            and self.attempt_number < self.max_attempts
        )

    @property
    def is_successful(self) -> bool:
        """Check if job completed successfully."""
        return self.status == JobExecutionStatus.COMPLETED and self.success


class SchedulerMetrics(BaseModel):
    """Scheduler performance metrics."""

    # Time period
    period_start: datetime = Field(..., description="Metrics period start")
    period_end: datetime = Field(..., description="Metrics period end")

    # Job statistics
    total_jobs_scheduled: int = Field(default=0, description="Total jobs scheduled")
    total_jobs_completed: int = Field(default=0, description="Total jobs completed successfully")
    total_jobs_failed: int = Field(default=0, description="Total jobs failed")
    total_jobs_retried: int = Field(default=0, description="Total job retries")
    total_jobs_cancelled: int = Field(default=0, description="Total jobs cancelled")

    # Performance metrics
    average_execution_time_seconds: float = Field(default=0.0, description="Average job execution time")
    max_execution_time_seconds: float = Field(default=0.0, description="Maximum job execution time")
    min_execution_time_seconds: float = Field(default=0.0, description="Minimum job execution time")

    # Sync-specific metrics
    total_sync_sessions: int = Field(default=0, description="Total sync sessions created")
    total_records_processed: int = Field(default=0, description="Total records processed")
    total_changes_detected: int = Field(default=0, description="Total changes detected")
    total_events_created: int = Field(default=0, description="Total events created")

    # Error analysis
    consecutive_failures: int = Field(default=0, description="Current consecutive failures")
    failure_rate_percent: float = Field(default=0.0, description="Failure rate percentage")
    most_common_errors: list[str] = Field(default_factory=list, description="Most common error types")

    # Health indicators
    scheduler_healthy: bool = Field(default=True, description="Overall scheduler health")
    last_successful_sync: datetime | None = Field(None, description="Last successful sync time")
    last_full_sync: datetime | None = Field(None, description="Last full sync time")

    @property
    def success_rate_percent(self) -> float:
        """Calculate success rate percentage."""
        total_finished = self.total_jobs_completed + self.total_jobs_failed + self.total_jobs_cancelled
        if total_finished == 0:
            return 0.0
        return (self.total_jobs_completed / total_finished) * 100.0


class SchedulerState(BaseModel):
    """Current state of the scheduler."""

    # Scheduler status
    is_running: bool = Field(default=False, description="Whether scheduler is running")
    is_enabled: bool = Field(default=True, description="Whether scheduler is enabled")
    started_at: datetime | None = Field(None, description="Scheduler start time")
    last_heartbeat: datetime = Field(default_factory=datetime.now, description="Last heartbeat time")

    # Active jobs
    active_jobs: list[str] = Field(default_factory=list, description="Currently active job IDs")
    queued_jobs: list[str] = Field(default_factory=list, description="Queued job IDs")

    # Next scheduled jobs
    next_incremental_sync: datetime | None = Field(None, description="Next incremental sync time")
    next_full_sync: datetime | None = Field(None, description="Next full sync time")

    # Error state
    consecutive_failures: int = Field(default=0, description="Consecutive failure count")
    last_error: str | None = Field(None, description="Last error message")
    last_error_time: datetime | None = Field(None, description="Last error time")

    # Health monitoring
    health_status: str = Field(default="healthy", description="Overall health status")
    alerts_sent: int = Field(default=0, description="Number of alerts sent")
    last_alert_sent: datetime | None = Field(None, description="Last alert sent time")

    @property
    def is_healthy(self) -> bool:
        """Check if scheduler is in healthy state."""
        return (
            self.is_running
            and self.is_enabled
            and self.health_status == "healthy"
            and self.consecutive_failures < 3
        )

    @property
    def has_active_jobs(self) -> bool:
        """Check if there are active jobs."""
        return len(self.active_jobs) > 0


class JobScheduleInfo(BaseModel):
    """Information about scheduled job."""

    job_id: str = Field(..., description="Job identifier")
    job_name: str = Field(..., description="Job name")
    job_type: SyncJobType = Field(..., description="Job type")

    # Schedule details
    cron_expression: str = Field(..., description="Cron expression for scheduling")
    next_run_time: datetime | None = Field(None, description="Next scheduled run time")
    timezone: str = Field(default="Europe/Moscow", description="Job timezone")

    # Job configuration
    enabled: bool = Field(default=True, description="Whether job is enabled")
    max_instances: int = Field(default=1, description="Maximum concurrent instances")
    misfire_grace_time: int = Field(default=300, description="Misfire grace time in seconds")

    # Execution history
    last_execution: JobExecutionResult | None = Field(None, description="Last execution result")
    total_executions: int = Field(default=0, description="Total number of executions")
    consecutive_failures: int = Field(default=0, description="Consecutive failure count")

    @property
    def is_overdue(self) -> bool:
        """Check if job is overdue for execution."""
        if not self.next_run_time:
            return False
        return datetime.now() > self.next_run_time

"""
Scheduler configuration.

Contains settings for APScheduler and Windows Task Scheduler integration.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class SchedulerConfig(BaseSettings):
    """Scheduler configuration settings."""

    # Basic scheduler settings
    scheduler_enabled: bool = Field(default=True, description="Enable automatic scheduling")
    scheduler_timezone: str = Field(default="Europe/Moscow", description="Scheduler timezone")
    scheduler_job_defaults: dict[str, int] = Field(
        default_factory=lambda: {
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 300,  # 5 minutes
        },
        description="Default job settings",
    )

    # Sync schedule settings
    daily_sync_time: str = Field(default="03:00", description="Daily sync time (HH:MM)")
    daily_sync_enabled: bool = Field(default=True, description="Enable daily incremental sync")

    full_sync_schedule: str = Field(
        default="weekly", description="Full sync frequency (daily/weekly/monthly)"
    )
    full_sync_day: str = Field(default="sunday", description="Day for weekly full sync")
    full_sync_time: str = Field(default="02:00", description="Full sync time (HH:MM)")

    # Retry configuration
    max_retry_attempts: int = Field(default=3, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(default=300, description="Initial retry delay in seconds")
    retry_exponential_backoff: bool = Field(default=True, description="Use exponential backoff")
    retry_max_delay_seconds: int = Field(default=3600, description="Maximum retry delay in seconds")

    # Error handling
    continue_on_sync_failure: bool = Field(
        default=False, description="Continue scheduling after sync failure"
    )
    alert_on_failure: bool = Field(default=True, description="Send alerts on sync failure")
    max_consecutive_failures: int = Field(
        default=5, description="Max consecutive failures before disabling"
    )

    # File monitoring
    file_monitoring_enabled: bool = Field(default=True, description="Enable file change monitoring")
    file_monitoring_interval_seconds: int = Field(
        default=300, description="File monitoring interval"
    )

    # Job persistence
    job_store_type: str = Field(
        default="memory", description="Job store type (memory/redis/postgresql)"
    )
    job_store_url: str = Field(default="", description="Job store connection URL")

    # Windows Task Scheduler (backup/watchdog)
    windows_task_scheduler_enabled: bool = Field(
        default=False, description="Enable Windows Task Scheduler watchdog"
    )
    windows_task_name: str = Field(default="ServiceOperUchet_Sync", description="Windows task name")
    python_executable_path: str = Field(
        default="", description="Python executable path for Windows task"
    )
    script_path: str = Field(default="", description="Script path for Windows task")

    # Logging and monitoring
    log_job_execution: bool = Field(default=True, description="Log job execution details")
    collect_metrics: bool = Field(default=True, description="Collect scheduler metrics")
    metrics_retention_days: int = Field(default=30, description="Metrics retention period")

    model_config = ConfigDict(
        env_prefix="SCHEDULER_",
        env_file=".env",
        extra="allow"  # Allow extra fields from env files
    )

    @property
    def full_sync_cron_expression(self) -> str:
        """Get cron expression for full sync based on frequency."""
        hour, minute = self.full_sync_time.split(":")

        # Remove leading zeros for consistent formatting
        hour = str(int(hour))
        minute = str(int(minute))

        if self.full_sync_schedule == "daily":
            return f"{minute} {hour} * * *"
        elif self.full_sync_schedule == "weekly":
            # Map day names to weekday numbers (0=Monday, 6=Sunday)
            weekdays = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }
            weekday = weekdays.get(self.full_sync_day.lower(), 6)  # Default to Sunday
            return f"{minute} {hour} * * {weekday}"
        elif self.full_sync_schedule == "monthly":
            return f"{minute} {hour} 1 * *"  # First day of month
        else:
            # Default to weekly Sunday
            return f"{minute} {hour} * * 6"

    @property
    def daily_sync_cron_expression(self) -> str:
        """Get cron expression for daily incremental sync."""
        hour, minute = self.daily_sync_time.split(":")
        # Remove leading zeros for consistent formatting
        hour = str(int(hour))
        minute = str(int(minute))
        return f"{minute} {hour} * * *"

    def get_python_executable(self) -> str:
        """Get Python executable path for cross-platform compatibility."""
        if self.python_executable_path:
            return self.python_executable_path

        # Try to find Python executable automatically
        import sys
        return str(Path(sys.executable))

    def get_script_path(self) -> str:
        """Get script path for cross-platform compatibility."""
        if self.script_path:
            return self.script_path

        # Default to project root script - use Path for cross-platform compatibility
        return str(Path(__file__).parent.parent.parent.parent / "scripts" / "sync_scheduler.py")

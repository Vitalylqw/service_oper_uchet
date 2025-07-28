"""
Scheduler Service for automated synchronization jobs.

Manages APScheduler with retry logic and integration with sync orchestrator.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from tenacity import (
    AsyncRetrying,
    RetryError,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from application.sync_orchestrator import SyncConfiguration, SyncOrchestratorService

from .config import SchedulerConfig
from .models import (
    JobExecutionResult,
    JobExecutionStatus,
    JobScheduleInfo,
    SchedulerMetrics,
    SchedulerState,
    SyncJobType,
)


class SchedulerService:
    """
    Scheduler service for automated sync operations.

    Features:
    - APScheduler for job scheduling
    - Tenacity for retry logic with exponential backoff
    - Integration with SyncOrchestratorService
    - Job execution monitoring and metrics
    - Error handling and alerting
    - Health monitoring
    """

    def __init__(
        self,
        config: SchedulerConfig,
        sync_orchestrator: SyncOrchestratorService | None = None,
    ) -> None:
        """Initialize scheduler service."""
        self.config = config
        self.sync_orchestrator = sync_orchestrator

        # Scheduler state
        self._scheduler: AsyncIOScheduler | None = None
        self._is_running = False
        self._state = SchedulerState()
        self._metrics = SchedulerMetrics(
            period_start=datetime.now(), period_end=datetime.now() + timedelta(days=1)
        )

        # Job execution tracking
        self._job_results: dict[str, JobExecutionResult] = {}
        self._active_jobs: set[str] = set()

        logger.info("SchedulerService initialized")

    async def start(self) -> None:
        """Start the scheduler service."""
        if self._is_running:
            logger.warning("Scheduler is already running")
            return

        logger.info("Starting scheduler service...")

        try:
            # Initialize APScheduler
            self._scheduler = AsyncIOScheduler(
                jobstores={"default": MemoryJobStore()},
                executors={"default": AsyncIOExecutor()},
                job_defaults=self.config.scheduler_job_defaults,
                timezone=self.config.scheduler_timezone,
            )

            # Add event listeners
            self._scheduler.add_listener(
                self._on_job_executed, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
            )

            # Start scheduler
            self._scheduler.start()

            # Schedule sync jobs if enabled
            if self.config.scheduler_enabled:
                await self._schedule_sync_jobs()

            # Update state
            self._state.is_running = True
            self._state.is_enabled = self.config.scheduler_enabled
            self._state.started_at = datetime.now()
            self._state.health_status = "healthy"
            self._is_running = True

            logger.info("✅ Scheduler service started successfully")

        except Exception as e:
            logger.error(f"❌ Failed to start scheduler service: {e}")
            self._state.health_status = "failed"
            raise

    async def stop(self) -> None:
        """Stop the scheduler service."""
        if not self._is_running:
            logger.warning("Scheduler is not running")
            return

        logger.info("Stopping scheduler service...")

        try:
            if self._scheduler:
                self._scheduler.shutdown(wait=True)
                self._scheduler = None

            self._state.is_running = False
            self._is_running = False

            logger.info("✅ Scheduler service stopped successfully")

        except Exception as e:
            logger.error(f"❌ Error stopping scheduler service: {e}")
            raise

    async def _schedule_sync_jobs(self) -> None:
        """Schedule automatic sync jobs."""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")

        # Schedule daily incremental sync
        if self.config.daily_sync_enabled:
            job_id = "daily_incremental_sync"
            self._scheduler.add_job(
                func=self._execute_sync_job,
                args=[SyncJobType.INCREMENTAL, "Daily incremental sync"],
                trigger="cron",
                id=job_id,
                name="Daily Incremental Sync",
                hour=int(self.config.daily_sync_time.split(":")[0]),
                minute=int(self.config.daily_sync_time.split(":")[1]),
                misfire_grace_time=self.config.scheduler_job_defaults.get(
                    "misfire_grace_time", 300
                ),
                max_instances=1,
            )
            logger.info(f"Scheduled daily incremental sync at {self.config.daily_sync_time}")

        # Schedule full sync based on frequency
        if self.config.full_sync_schedule != "manual":
            job_id = "full_sync"
            hour, minute = self.config.full_sync_time.split(":")

            if self.config.full_sync_schedule == "weekly":
                weekdays = {
                    "monday": 0,
                    "tuesday": 1,
                    "wednesday": 2,
                    "thursday": 3,
                    "friday": 4,
                    "saturday": 5,
                    "sunday": 6,
                }
                weekday = weekdays.get(self.config.full_sync_day.lower(), 6)

                self._scheduler.add_job(
                    func=self._execute_sync_job,
                    args=[SyncJobType.FULL, "Weekly full sync"],
                    trigger="cron",
                    id=job_id,
                    name="Weekly Full Sync",
                    hour=int(hour),
                    minute=int(minute),
                    day_of_week=weekday,
                    misfire_grace_time=self.config.scheduler_job_defaults.get(
                        "misfire_grace_time", 300
                    ),
                    max_instances=1,
                )
                logger.info(
                    f"Scheduled weekly full sync on {self.config.full_sync_day} at {self.config.full_sync_time}"
                )

    async def _execute_sync_job(self, job_type: SyncJobType, job_name: str) -> JobExecutionResult:
        """Execute a synchronization job with retry logic."""
        job_id = str(uuid.uuid4())
        start_time = datetime.now()

        # Create initial job result
        result = JobExecutionResult(
            job_id=job_id,
            job_name=job_name,
            job_type=job_type,
            status=JobExecutionStatus.RUNNING,
            started_at=start_time,
            triggered_by="scheduler",
        )

        self._job_results[job_id] = result
        self._active_jobs.add(job_id)
        self._state.active_jobs = list(self._active_jobs)

        logger.info(f"🚀 Starting sync job {job_id} ({job_type.value}): {job_name}")

        try:
            # Execute with retry logic
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.config.max_retry_attempts),
                wait=wait_exponential(
                    multiplier=self.config.retry_delay_seconds,
                    max=self.config.retry_max_delay_seconds,
                )
                if self.config.retry_exponential_backoff
                else wait_exponential(
                    min=self.config.retry_delay_seconds, max=self.config.retry_delay_seconds
                ),
                retry=retry_if_exception_type(Exception),
                before_sleep=before_sleep_log(logger, "WARNING"),
                reraise=True,
            ):
                with attempt:
                    result.attempt_number = attempt.retry_state.attempt_number
                    result.status = (
                        JobExecutionStatus.RETRYING
                        if attempt.retry_state.attempt_number > 1
                        else JobExecutionStatus.RUNNING
                    )

                    # Execute sync operation
                    sync_result = await self._execute_sync_operation(job_type)

                    # Update result with sync operation details
                    result.sync_session_id = sync_result.sync_session_id
                    result.records_processed = sync_result.summary.total_deals_processed
                    result.changes_detected = (
                        getattr(sync_result.change_detection_result, "total_changes", 0)
                        if sync_result.change_detection_result
                        else 0
                    )
                    result.events_created = (
                        len(sync_result.events_created) if sync_result.events_created else 0
                    )
                    result.file_path = sync_result.summary.file_path

            # Job completed successfully
            result.status = JobExecutionStatus.COMPLETED
            result.success = True
            result.completed_at = datetime.now()
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

            logger.info(
                f"✅ Sync job {job_id} completed successfully in {result.duration_seconds:.2f}s"
            )

            # Update metrics
            self._update_success_metrics(result)

            # Reset consecutive failures
            self._state.consecutive_failures = 0
            self._state.health_status = "healthy"

        except RetryError as e:
            # All retry attempts failed
            result.status = JobExecutionStatus.FAILED
            result.success = False
            result.completed_at = datetime.now()
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
            result.error_message = f"Job failed after {self.config.max_retry_attempts} attempts: {str(e.last_attempt.exception())}"
            result.error_details = {
                "exception_type": type(e.last_attempt.exception()).__name__,
                "last_attempt": str(e.last_attempt.exception()),
                "total_attempts": self.config.max_retry_attempts,
            }

            logger.error(
                f"❌ Sync job {job_id} failed after {self.config.max_retry_attempts} attempts: {result.error_message}"
            )

            # Update error state and metrics
            self._update_failure_metrics(result)
            await self._handle_job_failure(result)

        except Exception as e:
            # Unexpected error (catch-all that shouldn't be reached with proper retry logic)
            result.status = JobExecutionStatus.FAILED
            result.success = False
            result.completed_at = datetime.now()
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

            # Check if this was actually a retry failure that wasn't caught properly
            if result.attempt_number >= self.config.max_retry_attempts:
                result.error_message = (
                    f"Job failed after {self.config.max_retry_attempts} attempts: {str(e)}"
                )
            else:
                result.error_message = f"Unexpected error: {str(e)}"

            result.error_details = {"exception_type": type(e).__name__, "details": str(e)}

            logger.error(f"❌ Unexpected error in sync job {job_id}: {e}")

            # Update error state and metrics
            self._update_failure_metrics(result)
            await self._handle_job_failure(result)

        finally:
            # Clean up
            self._active_jobs.discard(job_id)
            self._state.active_jobs = list(self._active_jobs)
            self._state.last_heartbeat = datetime.now()

        return result

    async def _execute_sync_operation(self, job_type: SyncJobType) -> Any:
        """Execute the actual sync operation."""
        if not self.sync_orchestrator:
            raise RuntimeError("SyncOrchestratorService not configured")

        # Create sync configuration based on job type
        config = SyncConfiguration(
            sync_type=job_type.value,
            incremental_period_months=3 if job_type == SyncJobType.INCREMENTAL else 12,
            max_retry_attempts=1,  # Retry is handled at scheduler level
            continue_on_errors=True,
            rollback_on_failure=True,
        )

        # For now, we need to get file path from file system service
        # This will be implemented when file system service is ready
        file_path = "data/excel_file.xlsx"  # Placeholder

        # Execute sync through orchestrator
        return await self.sync_orchestrator.execute_sync(file_path, config)

    def _update_success_metrics(self, result: JobExecutionResult) -> None:
        """Update metrics for successful job execution."""
        self._metrics.total_jobs_completed += 1
        self._metrics.total_sync_sessions += 1
        self._metrics.total_records_processed += result.records_processed
        self._metrics.total_changes_detected += result.changes_detected
        self._metrics.total_events_created += result.events_created

        # Update execution time metrics
        if result.duration_seconds:
            if self._metrics.total_jobs_completed == 1:
                self._metrics.average_execution_time_seconds = result.duration_seconds
                self._metrics.min_execution_time_seconds = result.duration_seconds
                self._metrics.max_execution_time_seconds = result.duration_seconds
            else:
                # Update average
                total_time = self._metrics.average_execution_time_seconds * (
                    self._metrics.total_jobs_completed - 1
                )
                self._metrics.average_execution_time_seconds = (
                    total_time + result.duration_seconds
                ) / self._metrics.total_jobs_completed

                # Update min/max
                self._metrics.min_execution_time_seconds = min(
                    self._metrics.min_execution_time_seconds, result.duration_seconds
                )
                self._metrics.max_execution_time_seconds = max(
                    self._metrics.max_execution_time_seconds, result.duration_seconds
                )

        # Update last successful sync
        self._metrics.last_successful_sync = result.completed_at
        if result.job_type == SyncJobType.FULL:
            self._metrics.last_full_sync = result.completed_at

    def _update_failure_metrics(self, result: JobExecutionResult) -> None:
        """Update metrics for failed job execution."""
        self._metrics.total_jobs_failed += 1
        self._state.consecutive_failures += 1
        self._state.last_error = result.error_message
        self._state.last_error_time = result.completed_at

        # Update failure rate
        total_jobs = self._metrics.total_jobs_completed + self._metrics.total_jobs_failed
        if total_jobs > 0:
            self._metrics.failure_rate_percent = (
                self._metrics.total_jobs_failed / total_jobs
            ) * 100.0

        # Add to common errors
        if result.error_details.get("exception_type"):
            error_type = result.error_details["exception_type"]
            if error_type not in self._metrics.most_common_errors:
                self._metrics.most_common_errors.append(error_type)

    async def _handle_job_failure(self, result: JobExecutionResult) -> None:
        """Handle job failure - alerting and health checks."""
        # Check if scheduler should be disabled due to consecutive failures
        if self._state.consecutive_failures >= self.config.max_consecutive_failures:
            logger.error(
                f"Disabling scheduler due to {self._state.consecutive_failures} consecutive failures"
            )
            self._state.health_status = "disabled"
            self._state.is_enabled = False

        # Send alert if configured
        if self.config.alert_on_failure:
            await self._send_failure_alert(result)

    async def _send_failure_alert(self, result: JobExecutionResult) -> None:
        """Send failure alert (placeholder for notifications integration)."""
        # This will be implemented when notifications service is ready
        logger.warning(f"📧 Alert: Sync job {result.job_id} failed - {result.error_message}")
        self._state.alerts_sent += 1
        self._state.last_alert_sent = datetime.now()

    def _on_job_executed(self, event) -> None:
        """Handle APScheduler job execution events."""
        job_id = event.job_id
        if hasattr(event, "exception") and event.exception:
            logger.error(f"APScheduler job {job_id} failed: {event.exception}")
        else:
            logger.info(f"APScheduler job {job_id} executed successfully")

    # Public API methods

    async def trigger_sync(
        self, job_type: SyncJobType, job_name: str = "Manual sync"
    ) -> JobExecutionResult:
        """Manually trigger a sync job."""
        logger.info(f"Manually triggering {job_type.value} sync")
        return await self._execute_sync_job(job_type, job_name)

    def get_state(self) -> SchedulerState:
        """Get current scheduler state."""
        return self._state

    def get_metrics(self) -> SchedulerMetrics:
        """Get scheduler metrics."""
        return self._metrics

    def get_scheduled_jobs(self) -> list[JobScheduleInfo]:
        """Get information about scheduled jobs."""
        if not self._scheduler:
            return []

        jobs = []
        for job in self._scheduler.get_jobs():
            job_info = JobScheduleInfo(
                job_id=job.id,
                job_name=job.name,
                job_type=SyncJobType.INCREMENTAL if "incremental" in job.id else SyncJobType.FULL,
                cron_expression=str(job.trigger),
                next_run_time=job.next_run_time,
                enabled=True,  # APScheduler jobs are enabled if they exist
                total_executions=len(
                    [r for r in self._job_results.values() if r.job_name == job.name]
                ),
            )

            # Add last execution if available
            last_results = [r for r in self._job_results.values() if r.job_name == job.name]
            if last_results:
                job_info.last_execution = max(last_results, key=lambda x: x.started_at)
                job_info.consecutive_failures = self._state.consecutive_failures

            jobs.append(job_info)

        return jobs

    def get_job_results(self, limit: int = 100) -> list[JobExecutionResult]:
        """Get recent job execution results."""
        results = list(self._job_results.values())
        results.sort(key=lambda x: x.started_at, reverse=True)
        return results[:limit]

    async def pause_scheduler(self) -> None:
        """Pause the scheduler."""
        if self._scheduler:
            self._scheduler.pause()
            self._state.is_enabled = False
            logger.info("Scheduler paused")

    async def resume_scheduler(self) -> None:
        """Resume the scheduler."""
        if self._scheduler:
            self._scheduler.resume()
            self._state.is_enabled = True
            self._state.health_status = "healthy"
            logger.info("Scheduler resumed")

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._is_running and bool(self._scheduler)

    def is_healthy(self) -> bool:
        """Check if scheduler is healthy."""
        return self._state.is_healthy

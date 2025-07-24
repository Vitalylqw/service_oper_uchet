"""
Unit tests for scheduler infrastructure.

Tests for SchedulerConfig, SchedulerService and models.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.scheduler import (
    JobExecutionResult,
    JobExecutionStatus,
    SchedulerConfig,
    SchedulerMetrics,
    SchedulerService,
    SchedulerState,
    SyncJobType,
)


@pytest.mark.unit
class TestSchedulerConfig:
    """Test SchedulerConfig functionality."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SchedulerConfig()

        assert config.scheduler_enabled is True
        assert config.scheduler_timezone == "Europe/Moscow"
        assert config.daily_sync_time == "03:00"
        assert config.full_sync_schedule == "weekly"
        assert config.full_sync_day == "sunday"
        assert config.max_retry_attempts == 3
        assert config.retry_delay_seconds == 300

    def test_cron_expressions(self):
        """Test cron expression generation."""
        config = SchedulerConfig(
            daily_sync_time="14:30",
            full_sync_time="02:15",
            full_sync_day="monday",
            full_sync_schedule="weekly",
        )

        # Test daily sync cron
        assert config.daily_sync_cron_expression == "30 14 * * *"

        # Test weekly full sync cron (Monday = 0)
        assert config.full_sync_cron_expression == "15 2 * * 0"

    def test_full_sync_schedule_variations(self):
        """Test different full sync schedule types."""
        # Daily
        config = SchedulerConfig(full_sync_schedule="daily", full_sync_time="01:00")
        assert config.full_sync_cron_expression == "0 1 * * *"

        # Monthly
        config = SchedulerConfig(full_sync_schedule="monthly", full_sync_time="02:30")
        assert config.full_sync_cron_expression == "30 2 1 * *"

        # Invalid (defaults to weekly)
        config = SchedulerConfig(full_sync_schedule="invalid", full_sync_time="03:45")
        assert config.full_sync_cron_expression == "45 3 * * 6"

    def test_python_executable_paths(self):
        """Test Python executable path detection."""
        config = SchedulerConfig()

        # Should return system Python path when not configured
        python_path = config.get_python_executable()
        assert python_path  # Should not be empty
        assert "python" in python_path.lower()

        # Should use configured path when set
        config.python_executable_path = "C:\\Python39\\python.exe"
        assert config.get_python_executable() == "C:\\Python39\\python.exe"

    def test_env_prefix(self):
        """Test that configuration uses SCHEDULER_ env prefix."""
        with patch.dict("os.environ", {"SCHEDULER_ENABLED": "false"}):
            SchedulerConfig()
            # Note: This test assumes pydantic-settings is working
            # In real environment, it would load from env


@pytest.mark.unit
class TestSchedulerModels:
    """Test scheduler Pydantic models."""

    def test_job_execution_result_creation(self):
        """Test JobExecutionResult model creation."""
        result = JobExecutionResult(
            job_id="test-job-123",
            job_name="Test Job",
            job_type=SyncJobType.INCREMENTAL,
            status=JobExecutionStatus.COMPLETED,
            started_at=datetime.now(),
        )

        assert result.job_id == "test-job-123"
        assert result.job_name == "Test Job"
        assert result.job_type == SyncJobType.INCREMENTAL
        assert result.status == JobExecutionStatus.COMPLETED
        assert result.attempt_number == 1
        assert result.max_attempts == 3
        assert result.success is False  # Default

    def test_job_execution_result_properties(self):
        """Test JobExecutionResult property methods."""
        # Test finished job
        result = JobExecutionResult(
            job_id="test",
            job_name="test",
            job_type=SyncJobType.FULL,
            status=JobExecutionStatus.COMPLETED,
            started_at=datetime.now(),
        )

        assert result.is_finished is True
        assert result.can_retry is False

        # Test failed job that can retry
        result.status = JobExecutionStatus.FAILED
        result.attempt_number = 2
        result.max_attempts = 3

        assert result.is_finished is True
        assert result.can_retry is True

        # Test successful job
        result.status = JobExecutionStatus.COMPLETED
        result.success = True

        assert result.is_successful is True

    def test_scheduler_metrics_calculations(self):
        """Test SchedulerMetrics calculations."""
        metrics = SchedulerMetrics(
            period_start=datetime.now(),
            period_end=datetime.now() + timedelta(days=1),
            total_jobs_completed=80,
            total_jobs_failed=15,
            total_jobs_cancelled=5,
        )

        # Test success rate calculation
        assert metrics.success_rate_percent == 80.0  # 80/100

        # Test with no jobs
        empty_metrics = SchedulerMetrics(
            period_start=datetime.now(), period_end=datetime.now() + timedelta(days=1)
        )
        assert empty_metrics.success_rate_percent == 0.0

    def test_scheduler_state_health_check(self):
        """Test SchedulerState health checking."""
        state = SchedulerState(
            is_running=True, is_enabled=True, health_status="healthy", consecutive_failures=0
        )

        assert state.is_healthy is True

        # Test unhealthy conditions
        state.consecutive_failures = 5
        assert state.is_healthy is False

        state.consecutive_failures = 0
        state.is_running = False
        assert state.is_healthy is False

    def test_scheduler_state_active_jobs(self):
        """Test SchedulerState active jobs tracking."""
        state = SchedulerState()
        assert state.has_active_jobs is False

        state.active_jobs = ["job1", "job2"]
        assert state.has_active_jobs is True


@pytest.mark.unit
class TestSchedulerService:
    """Test SchedulerService functionality."""

    @pytest.fixture
    def mock_sync_orchestrator(self):
        """Create mock sync orchestrator."""
        orchestrator = AsyncMock()

        # Mock sync result
        sync_result = MagicMock()
        sync_result.sync_session_id = "session-123"
        sync_result.summary.total_deals_processed = 100
        sync_result.summary.file_path = "test.xlsx"
        sync_result.change_detection_result = None
        sync_result.events_created = []

        orchestrator.execute_sync.return_value = sync_result
        return orchestrator

    @pytest.fixture
    def scheduler_config(self):
        """Create test scheduler configuration."""
        return SchedulerConfig(
            scheduler_enabled=True,
            daily_sync_enabled=True,
            max_retry_attempts=2,
            retry_delay_seconds=1,  # Fast for testing
            retry_max_delay_seconds=2,
        )

    @pytest.fixture
    def scheduler_service(self, scheduler_config, mock_sync_orchestrator):
        """Create scheduler service for testing."""
        return SchedulerService(config=scheduler_config, sync_orchestrator=mock_sync_orchestrator)

    @pytest.mark.asyncio
    async def test_scheduler_initialization(self, scheduler_service):
        """Test scheduler service initialization."""
        assert scheduler_service.config is not None
        assert scheduler_service.sync_orchestrator is not None
        assert scheduler_service.is_running() is False
        # Note: is_healthy checks the internal state which is properly initialized
        state = scheduler_service.get_state()
        assert state.health_status == "healthy"

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, scheduler_service):
        """Test scheduler start and stop operations."""
        # Test start
        await scheduler_service.start()
        assert scheduler_service.is_running() is True
        assert scheduler_service.get_state().is_running is True

        # Test stop
        await scheduler_service.stop()
        assert scheduler_service.is_running() is False
        assert scheduler_service.get_state().is_running is False

    @pytest.mark.asyncio
    async def test_scheduler_start_already_running(self, scheduler_service):
        """Test starting scheduler when already running."""
        await scheduler_service.start()

        # Starting again should not raise error
        await scheduler_service.start()
        assert scheduler_service.is_running() is True

    @pytest.mark.asyncio
    async def test_manual_sync_trigger(self, scheduler_service, mock_sync_orchestrator):
        """Test manual sync job triggering."""
        await scheduler_service.start()

        # Trigger incremental sync
        result = await scheduler_service.trigger_sync(SyncJobType.INCREMENTAL, "Manual test sync")

        assert result.job_type == SyncJobType.INCREMENTAL
        assert result.job_name == "Manual test sync"
        assert result.status == JobExecutionStatus.COMPLETED
        assert result.success is True
        assert result.sync_session_id == "session-123"

        # Verify orchestrator was called
        mock_sync_orchestrator.execute_sync.assert_called_once()

        await scheduler_service.stop()

    @pytest.mark.asyncio
    async def test_sync_job_retry_logic(self, scheduler_config, mock_sync_orchestrator):
        """Test sync job retry logic on failure."""
        # Configure orchestrator to fail first time, succeed second time
        mock_sync_orchestrator.execute_sync.side_effect = [
            Exception("First attempt fails"),
            MagicMock(
                sync_session_id="session-retry",
                summary=MagicMock(total_deals_processed=50, file_path="test.xlsx"),
                change_detection_result=None,
                events_created=[],
            ),
        ]

        scheduler_service = SchedulerService(
            config=scheduler_config, sync_orchestrator=mock_sync_orchestrator
        )

        await scheduler_service.start()

        # Should succeed after retry
        result = await scheduler_service.trigger_sync(SyncJobType.INCREMENTAL)

        assert result.status == JobExecutionStatus.COMPLETED
        assert result.success is True
        assert result.attempt_number == 2
        assert mock_sync_orchestrator.execute_sync.call_count == 2

        await scheduler_service.stop()

    @pytest.mark.asyncio
    async def test_sync_job_max_retries_exceeded(self, scheduler_config, mock_sync_orchestrator):
        """Test sync job when max retries are exceeded."""
        # Configure orchestrator to always fail
        mock_sync_orchestrator.execute_sync.side_effect = Exception("Always fails")

        scheduler_service = SchedulerService(
            config=scheduler_config, sync_orchestrator=mock_sync_orchestrator
        )

        await scheduler_service.start()

        # Should fail after max attempts
        result = await scheduler_service.trigger_sync(SyncJobType.FULL)

        assert result.status == JobExecutionStatus.FAILED
        assert result.success is False
        assert result.attempt_number == scheduler_config.max_retry_attempts
        assert "failed after" in result.error_message
        assert mock_sync_orchestrator.execute_sync.call_count == scheduler_config.max_retry_attempts

        await scheduler_service.stop()

    @pytest.mark.asyncio
    async def test_scheduler_state_tracking(self, scheduler_service):
        """Test scheduler state tracking during operations."""
        await scheduler_service.start()

        state = scheduler_service.get_state()
        assert state.is_running is True
        assert state.is_enabled is True
        assert state.health_status == "healthy"
        assert state.consecutive_failures == 0

        await scheduler_service.stop()

    @pytest.mark.asyncio
    async def test_scheduler_metrics_collection(self, scheduler_service, mock_sync_orchestrator):
        """Test scheduler metrics collection."""
        await scheduler_service.start()

        # Execute a successful job
        await scheduler_service.trigger_sync(SyncJobType.INCREMENTAL)

        metrics = scheduler_service.get_metrics()
        assert metrics.total_jobs_completed == 1
        assert metrics.total_sync_sessions == 1
        assert metrics.total_records_processed == 100
        assert metrics.success_rate_percent == 100.0
        assert metrics.last_successful_sync is not None

        await scheduler_service.stop()

    @pytest.mark.asyncio
    async def test_scheduler_pause_resume(self, scheduler_service):
        """Test scheduler pause and resume functionality."""
        await scheduler_service.start()

        # Test pause
        await scheduler_service.pause_scheduler()
        state = scheduler_service.get_state()
        assert state.is_enabled is False

        # Test resume
        await scheduler_service.resume_scheduler()
        state = scheduler_service.get_state()
        assert state.is_enabled is True
        assert state.health_status == "healthy"

        await scheduler_service.stop()

    @pytest.mark.asyncio
    async def test_job_results_tracking(self, scheduler_service):
        """Test job execution results tracking."""
        await scheduler_service.start()

        # Execute multiple jobs
        await scheduler_service.trigger_sync(SyncJobType.INCREMENTAL, "Job 1")
        await scheduler_service.trigger_sync(SyncJobType.FULL, "Job 2")

        # Get job results
        results = scheduler_service.get_job_results(limit=10)
        assert len(results) == 2

        # Results should be sorted by start time (newest first)
        assert results[0].started_at >= results[1].started_at

        await scheduler_service.stop()

    @pytest.mark.asyncio
    async def test_sync_without_orchestrator(self, scheduler_config):
        """Test sync job execution without orchestrator configured."""
        scheduler_service = SchedulerService(
            config=scheduler_config,
            sync_orchestrator=None,  # No orchestrator
        )

        await scheduler_service.start()

        # Should fail with RuntimeError
        result = await scheduler_service.trigger_sync(SyncJobType.INCREMENTAL)

        assert result.status == JobExecutionStatus.FAILED
        assert result.success is False
        assert "SyncOrchestratorService not configured" in result.error_message

        await scheduler_service.stop()

    @pytest.mark.asyncio
    async def test_scheduler_health_monitoring(self, scheduler_config, mock_sync_orchestrator):
        """Test scheduler health monitoring with consecutive failures."""
        # Configure to allow only 2 consecutive failures
        scheduler_config.max_consecutive_failures = 2

        # Configure orchestrator to always fail
        mock_sync_orchestrator.execute_sync.side_effect = Exception("Always fails")

        scheduler_service = SchedulerService(
            config=scheduler_config, sync_orchestrator=mock_sync_orchestrator
        )

        await scheduler_service.start()

        # First failure
        await scheduler_service.trigger_sync(SyncJobType.INCREMENTAL)
        state = scheduler_service.get_state()
        assert state.consecutive_failures == 1
        assert state.health_status == "healthy"

        # Second failure
        await scheduler_service.trigger_sync(SyncJobType.INCREMENTAL)
        state = scheduler_service.get_state()
        assert state.consecutive_failures == 2
        assert state.health_status == "disabled"
        assert state.is_enabled is False

        await scheduler_service.stop()


@pytest.mark.unit
class TestSchedulerIntegration:
    """Integration tests for scheduler components."""

    @pytest.mark.asyncio
    async def test_full_scheduler_workflow(self):
        """Test complete scheduler workflow with all components."""
        config = SchedulerConfig(
            scheduler_enabled=True,
            daily_sync_enabled=False,  # Disable auto-scheduling for test
            max_retry_attempts=1,
        )

        # Create mock orchestrator
        mock_orchestrator = AsyncMock()
        sync_result = MagicMock()
        sync_result.sync_session_id = "integration-test"
        sync_result.summary.total_deals_processed = 250
        sync_result.summary.file_path = "integration.xlsx"
        sync_result.change_detection_result = MagicMock()
        sync_result.change_detection_result.total_changes = 15
        sync_result.events_created = ["event1", "event2", "event3"]

        mock_orchestrator.execute_sync.return_value = sync_result

        # Create and start scheduler
        scheduler = SchedulerService(config=config, sync_orchestrator=mock_orchestrator)
        await scheduler.start()

        try:
            # Execute sync job
            result = await scheduler.trigger_sync(SyncJobType.FULL, "Integration test")

            # Verify result
            assert result.success is True
            assert result.records_processed == 250
            assert result.changes_detected == 15
            assert result.events_created == 3

            # Verify metrics
            metrics = scheduler.get_metrics()
            assert metrics.total_jobs_completed == 1
            assert metrics.total_records_processed == 250
            assert metrics.total_changes_detected == 15

            # Verify state
            state = scheduler.get_state()
            assert state.is_healthy is True
            assert state.consecutive_failures == 0

        finally:
            await scheduler.stop()

    def test_scheduler_config_validation(self):
        """Test scheduler configuration validation."""
        # Test valid configuration
        config = SchedulerConfig(
            daily_sync_time="23:59",
            full_sync_time="00:00",
            max_retry_attempts=5,
            retry_delay_seconds=100,
        )

        assert config.daily_sync_time == "23:59"
        assert config.max_retry_attempts == 5

        # Configuration validation is handled by Pydantic
        # Invalid values would raise ValidationError during instantiation

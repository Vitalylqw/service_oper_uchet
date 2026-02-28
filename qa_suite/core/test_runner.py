"""
Test Runner for QA Suite.

Orchestrates test scenario execution including Excel generation,
sync execution, and result validation.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from src.application.change_detector import ChangeDetectorService
from src.application.excel_parser import ExcelParserService
from src.application.sync_orchestrator import SyncOrchestratorService
from src.application.sync_orchestrator.models import SyncConfiguration
from src.infrastructure.database.connection import DatabaseConfig, DatabaseManager
from src.infrastructure.database.event_store import EventStoreImplementation
from src.infrastructure.database.repositories import (
    DealRepositoryImplementation,
    SyncSessionRepositoryImplementation,
)
from src.infrastructure.workers.read_model_builder import ReadModelBuilder

from .db_manager import DBManager, compute_aggregate_diff
from .excel_builder import ExcelBuilder, create_base_state_file
from .models import (
    ActionType,
    AggregateMetrics,
    ScenarioResult,
    ScenarioStatus,
    TestRunReport,
    TestScenario,
    ValidationResult,
)
from .scenario_loader import ScenarioLoader


class TestRunner:
    """
    Runner for executing test scenarios.

    Coordinates Excel file generation, sync execution, and validation.
    """

    def __init__(
        self,
        scenarios_dir: Path,
        fixtures_dir: Path,
        temp_dir: Path,
        reports_dir: Path,
        database_url: str,
        continue_on_error: bool = True,
        cleanup_temp_files: bool = True,
    ) -> None:
        """
        Initialize TestRunner.

        Args:
            scenarios_dir: Directory containing scenario YAML files.
            fixtures_dir: Directory containing fixture Excel files.
            temp_dir: Directory for temporary files.
            reports_dir: Directory for output reports.
            database_url: Async database connection URL.
            continue_on_error: Continue running after scenario failure.
            cleanup_temp_files: Clean up temporary files after tests.
        """
        self._scenarios_dir = scenarios_dir
        self._fixtures_dir = fixtures_dir
        self._temp_dir = temp_dir
        self._reports_dir = reports_dir
        self._database_url = database_url
        self._continue_on_error = continue_on_error
        self._cleanup_temp_files = cleanup_temp_files

        self._scenario_loader = ScenarioLoader(scenarios_dir)
        self._db_manager = DBManager(database_url)

        # Ensure directories exist
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._reports_dir.mkdir(parents=True, exist_ok=True)
        self._fixtures_dir.mkdir(parents=True, exist_ok=True)

    async def run_all_scenarios(
        self, filter_category: Optional[str] = None
    ) -> TestRunReport:
        """
        Run all enabled scenarios.

        Args:
            filter_category: Optional category to filter scenarios.

        Returns:
            TestRunReport with all results.
        """
        scenarios = self._scenario_loader.load_all_scenarios()

        if filter_category:
            scenarios = [s for s in scenarios if s.category.value == filter_category]

        # Filter enabled only
        scenarios = [s for s in scenarios if s.enabled]

        logger.info(f"Running {len(scenarios)} scenarios")

        report = TestRunReport()

        # Get initial aggregates
        initial_aggregates = await self._db_manager.get_aggregates()
        report.aggregates_before = initial_aggregates.to_dict()

        for scenario in scenarios:
            try:
                result = await self.run_scenario(scenario)
                report.add_result(result)

                if result.status == ScenarioStatus.FAILED and not self._continue_on_error:
                    logger.warning("Stopping due to scenario failure")
                    break

            except Exception as e:
                logger.error(f"Scenario {scenario.id} crashed: {e}")
                result = ScenarioResult(
                    scenario_id=scenario.id,
                    scenario_name=scenario.name,
                    status=ScenarioStatus.ERROR,
                    error_message=str(e),
                )
                result.complete(ScenarioStatus.ERROR, error_message=str(e))
                report.add_result(result)

                if not self._continue_on_error:
                    break

        # Get final aggregates
        final_aggregates = await self._db_manager.get_aggregates()
        report.aggregates_after = final_aggregates.to_dict()
        report.aggregate_diff = compute_aggregate_diff(
            initial_aggregates, final_aggregates
        )

        return report

    async def run_scenario(self, scenario: TestScenario) -> ScenarioResult:
        """
        Run a single test scenario.

        Args:
            scenario: The scenario to execute.

        Returns:
            ScenarioResult with execution details.
        """
        logger.info(f"Running scenario: {scenario.id} - {scenario.name}")

        result = ScenarioResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            status=ScenarioStatus.RUNNING,
        )

        try:
            # Setup phase
            if scenario.clear_db_before:
                await self._db_manager.clear_all_data()
                logger.debug("Cleared database before scenario")

            # Get metrics before
            metrics_before = await self._db_manager.get_aggregates()

            # Create working Excel file
            work_file = await self._prepare_excel_file(scenario)

            # Sync base state first if required
            if scenario.sync_base_first and scenario.base_state:
                base_file = self._fixtures_dir / scenario.base_state
                if base_file.exists():
                    logger.debug(f"Syncing base state: {base_file}")
                    await self._execute_sync(base_file)

            # Apply scenario actions to Excel
            await self._apply_actions(work_file, scenario)

            # Execute sync
            sync_result = await self._execute_sync(work_file)

            # Get metrics after
            metrics_after = await self._db_manager.get_aggregates()

            # Validate results
            from .validators import ResultValidator

            validator = ResultValidator(self._db_manager)
            validation = await validator.validate_all(
                scenario.expected,
                sync_result,
                metrics_before,
                metrics_after,
            )

            # Determine status
            status = (
                ScenarioStatus.PASSED if validation.passed else ScenarioStatus.FAILED
            )

            result.sync_result_summary = {
                "insertions": sync_result.summary.insertions_count,
                "updates": sync_result.summary.updates_count,
                "deletions": sync_result.summary.deletions_count,
                "success": sync_result.summary.success,
            }

            result.complete(status, validation=validation)

            # Cleanup
            if self._cleanup_temp_files and work_file.exists():
                work_file.unlink()

            log_status = "PASSED" if validation.passed else "FAILED"
            logger.info(f"Scenario {scenario.id}: {log_status}")

        except Exception as e:
            logger.error(f"Scenario {scenario.id} failed with error: {e}")
            import traceback

            traceback.print_exc()
            result.complete(ScenarioStatus.ERROR, error_message=str(e))

        return result

    async def run_scenario_by_id(self, scenario_id: str) -> ScenarioResult:
        """
        Run a specific scenario by ID.

        Args:
            scenario_id: Unique scenario identifier.

        Returns:
            ScenarioResult or error result if not found.
        """
        scenario = self._scenario_loader.load_scenario_by_id(scenario_id)
        if not scenario:
            return ScenarioResult(
                scenario_id=scenario_id,
                scenario_name="Unknown",
                status=ScenarioStatus.ERROR,
                error_message=f"Scenario {scenario_id} not found",
            )
        return await self.run_scenario(scenario)

    async def _prepare_excel_file(self, scenario: TestScenario) -> Path:
        """Prepare the Excel file for the scenario."""
        work_file = self._temp_dir / f"{scenario.id}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"

        if scenario.base_state:
            base_file = self._fixtures_dir / scenario.base_state
            if base_file.exists():
                shutil.copy2(base_file, work_file)
                logger.debug(f"Copied base state from {base_file}")
            else:
                # Create base state if it doesn't exist
                create_base_state_file(work_file)
                logger.debug(f"Created new base state file")
        else:
            # Create empty workbook
            builder = ExcelBuilder.create_new()
            builder.save(work_file)

        return work_file

    async def _apply_actions(self, excel_path: Path, scenario: TestScenario) -> None:
        """Apply scenario actions to Excel file."""
        if not scenario.actions:
            return

        builder = ExcelBuilder.from_file(excel_path)

        for action in scenario.actions:
            logger.debug(f"Applying action: {action.type.value}")

            if action.type == ActionType.ADD_SHEET:
                builder.add_sheet(action.sheet_name, action.deals or None)

            elif action.type == ActionType.REMOVE_SHEET:
                builder.remove_sheet(action.sheet_name)

            elif action.type == ActionType.ADD_DEAL:
                if action.deals:
                    for deal in action.deals:
                        builder.add_deal(action.sheet_name, deal)

            elif action.type == ActionType.REMOVE_DEAL:
                builder.remove_deal(action.sheet_name, action.deal_key)

            elif action.type == ActionType.UPDATE_DEAL_FIELD:
                builder.update_deal_field(
                    action.sheet_name,
                    action.deal_key,
                    action.field_name,
                    action.field_value,
                )

            elif action.type == ActionType.ADD_POSITION:
                if action.items:
                    for item in action.items:
                        builder.add_position(action.sheet_name, action.deal_key, item)

            elif action.type == ActionType.REMOVE_POSITION:
                builder.remove_position(
                    action.sheet_name,
                    action.deal_key,
                    action.position_number,
                )

            elif action.type == ActionType.UPDATE_POSITION_FIELD:
                builder.update_position_field(
                    action.sheet_name,
                    action.deal_key,
                    action.position_number,
                    action.field_name,
                    action.field_value,
                )

        builder.save(excel_path)

    async def _execute_sync(self, excel_path: Path) -> Any:
        """Execute synchronization using SyncOrchestratorService."""
        config = DatabaseConfig()
        db_manager = DatabaseManager(config)

        async with db_manager.get_async_session() as session:
            # Initialize services
            deal_repo = DealRepositoryImplementation(session)
            change_detector = ChangeDetectorService(deal_repo)
            event_store = EventStoreImplementation(session)
            sync_session_repo = SyncSessionRepositoryImplementation(session)
            parser = ExcelParserService()
            read_model_builder = ReadModelBuilder(session, event_store)

            orchestrator = SyncOrchestratorService(
                excel_parser=parser,
                change_detector=change_detector,
                event_store=event_store,
                sync_session_repository=sync_session_repo,
                read_model_builder=read_model_builder,
            )

            sync_config = SyncConfiguration(
                sync_type="full",
                max_retry_attempts=1,
                continue_on_errors=True,
                rollback_on_failure=False,
                create_events=True,
                update_read_models=True,
            )

            result = await orchestrator.execute_sync(str(excel_path), sync_config)
            await session.commit()

            return result

    async def ensure_base_state_exists(self) -> Path:
        """Ensure base_state.xlsx exists in fixtures directory."""
        base_state_path = self._fixtures_dir / "base_state.xlsx"
        if not base_state_path.exists():
            logger.info("Creating base_state.xlsx fixture")
            create_base_state_file(base_state_path)
        return base_state_path

    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self._db_manager.close()

        if self._cleanup_temp_files:
            # Clean temp directory
            for f in self._temp_dir.glob("*.xlsx"):
                try:
                    f.unlink()
                except Exception:
                    pass

"""Core module for QA Suite."""

from .models import (
    ActionType,
    AggregateMetrics,
    DBSnapshot,
    DealData,
    ExpectedChanges,
    ExpectedDBState,
    ExpectedEvents,
    ExpectedResult,
    ItemData,
    ScenarioAction,
    ScenarioCategory,
    ScenarioResult,
    ScenarioStatus,
    TestRunReport,
    TestScenario,
    ValidationCheck,
    ValidationResult,
)

from .excel_builder import ExcelBuilder, create_base_state_file
from .db_manager import DBManager, compute_aggregate_diff
from .scenario_loader import ScenarioLoader, create_scenario_template
from .test_runner import TestRunner
from .validators import ResultValidator, AggregateValidator
from .reporters import JSONReporter, HTMLReporter, ReportManager

__all__ = [
    # Models
    "ActionType",
    "AggregateMetrics",
    "DBSnapshot",
    "DealData",
    "ExpectedChanges",
    "ExpectedDBState",
    "ExpectedEvents",
    "ExpectedResult",
    "ItemData",
    "ScenarioAction",
    "ScenarioCategory",
    "ScenarioResult",
    "ScenarioStatus",
    "TestRunReport",
    "TestScenario",
    "ValidationCheck",
    "ValidationResult",
    # Excel Builder
    "ExcelBuilder",
    "create_base_state_file",
    # DB Manager
    "DBManager",
    "compute_aggregate_diff",
    # Scenario Loader
    "ScenarioLoader",
    "create_scenario_template",
    # Test Runner
    "TestRunner",
    # Validators
    "ResultValidator",
    "AggregateValidator",
    # Reporters
    "JSONReporter",
    "HTMLReporter",
    "ReportManager",
]

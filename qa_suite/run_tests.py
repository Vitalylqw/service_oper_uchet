#!/usr/bin/env python3
"""
QA Suite Test Runner.

Main entry point for running integration tests.

Usage:
    python run_tests.py                     # Run all tests
    python run_tests.py --scenario TEST_INS_01  # Run specific scenario
    python run_tests.py --category INSERT   # Run scenarios by category
    python run_tests.py --clear-db          # Clear database before run
"""

import argparse
import asyncio
import os
import sys
import json
import time
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent
qa_suite_root = Path(__file__).parent
src_root = project_root / "src"

# #region agent log
try:
    with open("/workspaces/service_oper_uchet/.cursor/debug.log", "a") as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"path_fix","location":"qa_suite/run_tests.py:path_setup","message":"Configuring paths","data":{"project_root":str(project_root),"src_root":str(src_root)},"timestamp":int(time.time()*1000)}) + "\n")
except Exception: pass
# #endregion

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(qa_suite_root) not in sys.path:
    sys.path.insert(0, str(qa_suite_root))
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

# #region agent log
try:
    with open("/workspaces/service_oper_uchet/.cursor/debug.log", "a") as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"path_fix","location":"qa_suite/run_tests.py:path_setup_done","message":"Paths configured","data":{"sys_path":sys.path},"timestamp":int(time.time()*1000)}) + "\n")
except Exception: pass
# #endregion

from loguru import logger

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    colorize=True,
)


def setup_environment():
    """Load environment from config.env."""
    config_file = project_root / "config.env"
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key, value)
                    os.environ.setdefault(key.lower(), value)

        # Set PostgreSQL env vars with DB_ prefix for pydantic-settings
        os.environ["DB_DB_TYPE"] = "postgresql"
        os.environ["DB_DB_HOST"] = os.environ.get("DB_HOST", "so_pg")
        os.environ["DB_DB_PORT"] = os.environ.get("DB_PORT", "5432")
        os.environ["DB_DB_NAME"] = os.environ.get("DB_NAME", "so_uchet")
        os.environ["DB_DB_USER"] = os.environ.get("DB_USER", "so_user")
        os.environ["DB_DB_PASSWORD"] = os.environ.get("DB_PASSWORD", "so_pass")

        logger.info("Loaded environment from config.env")


async def run_all_tests(category: str = None, clear_db: bool = False):
    """Run all test scenarios."""
    from config.settings import get_settings
    from core.test_runner import TestRunner
    from core.reporters import ReportManager
    from core.excel_builder import create_base_state_file

    settings = get_settings()

    # Ensure base state file exists
    base_state_path = settings.fixtures_dir / "base_state.xlsx"
    if not base_state_path.exists():
        logger.info("Creating base_state.xlsx fixture...")
        create_base_state_file(base_state_path)

    runner = TestRunner(
        scenarios_dir=settings.scenarios_dir,
        fixtures_dir=settings.fixtures_dir,
        temp_dir=settings.temp_dir,
        reports_dir=settings.reports_dir,
        database_url=settings.database_url,
        continue_on_error=settings.continue_on_error,
        cleanup_temp_files=settings.cleanup_temp_files,
    )

    try:
        if clear_db:
            from core.db_manager import DBManager
            db_manager = DBManager(settings.database_url)
            await db_manager.clear_all_data()
            logger.info("Cleared database")

        logger.info("Starting test run...")
        report = await runner.run_all_scenarios(filter_category=category)

        # Generate reports
        reporter = ReportManager(settings.reports_dir)
        paths = reporter.generate_all_reports(report)

        # Print summary
        print("\n" + "=" * 60)
        print("TEST RUN SUMMARY")
        print("=" * 60)
        print(f"Total Scenarios: {report.total_scenarios}")
        print(f"Passed:          {report.passed}")
        print(f"Failed:          {report.failed}")
        print(f"Errors:          {report.errors}")
        print(f"Success Rate:    {report.success_rate:.1f}%")
        print(f"Duration:        {report.duration_ms / 1000:.2f}s")
        print("=" * 60)
        print(f"\nReports saved to:")
        for fmt, path in paths.items():
            print(f"  {fmt.upper()}: {path}")
        print()

        return report.failed == 0 and report.errors == 0

    finally:
        await runner.cleanup()


async def run_single_scenario(scenario_id: str, clear_db: bool = False):
    """Run a single scenario by ID."""
    from config.settings import get_settings
    from core.test_runner import TestRunner
    from core.excel_builder import create_base_state_file

    settings = get_settings()

    # Ensure base state file exists
    base_state_path = settings.fixtures_dir / "base_state.xlsx"
    if not base_state_path.exists():
        logger.info("Creating base_state.xlsx fixture...")
        create_base_state_file(base_state_path)

    runner = TestRunner(
        scenarios_dir=settings.scenarios_dir,
        fixtures_dir=settings.fixtures_dir,
        temp_dir=settings.temp_dir,
        reports_dir=settings.reports_dir,
        database_url=settings.database_url,
    )

    try:
        if clear_db:
            from core.db_manager import DBManager
            db_manager = DBManager(settings.database_url)
            await db_manager.clear_all_data()
            logger.info("Cleared database")

        result = await runner.run_scenario_by_id(scenario_id)

        # Print result
        print("\n" + "=" * 60)
        print(f"SCENARIO: {result.scenario_id}")
        print(f"Name:     {result.scenario_name}")
        print(f"Status:   {result.status.value}")
        if result.duration_ms:
            print(f"Duration: {result.duration_ms}ms")
        if result.error_message:
            print(f"Error:    {result.error_message}")
        if result.validation:
            print(f"Checks:   {len(result.validation.checks)}")
            for check in result.validation.checks:
                symbol = "[+]" if check.passed else "[X]"
                print(f"  {symbol} {check.check_name}: expected={check.expected}, actual={check.actual}")
        print("=" * 60)

        return result.status.value == "PASSED"

    finally:
        await runner.cleanup()


async def clear_database():
    """Clear all test data from database."""
    from config.settings import get_settings
    from core.db_manager import DBManager

    settings = get_settings()
    db_manager = DBManager(settings.database_url)

    await db_manager.clear_all_data()
    logger.info("Database cleared successfully")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="QA Suite Integration Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_tests.py                      # Run all tests
    python run_tests.py --scenario TEST_INS_01   # Run specific scenario
    python run_tests.py --category INSERT    # Run by category
    python run_tests.py --clear-db           # Clear database first
    python run_tests.py --clear-db-only      # Only clear database
        """,
    )

    parser.add_argument(
        "--scenario",
        type=str,
        help="Run specific scenario by ID",
    )

    parser.add_argument(
        "--category",
        type=str,
        choices=["INSERT", "UPDATE", "DELETE", "MIXED", "EDGE"],
        help="Run scenarios by category",
    )

    parser.add_argument(
        "--clear-db",
        action="store_true",
        help="Clear database before running tests",
    )

    parser.add_argument(
        "--clear-db-only",
        action="store_true",
        help="Only clear database, don't run tests",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    setup_environment()
    args = parse_args()

    try:
        if args.clear_db_only:
            asyncio.run(clear_database())
            return 0

        if args.scenario:
            success = asyncio.run(
                run_single_scenario(args.scenario, clear_db=args.clear_db)
            )
        else:
            success = asyncio.run(
                run_all_tests(category=args.category, clear_db=args.clear_db)
            )

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\nTest run interrupted.")
        return 130
    except Exception as e:
        logger.error(f"Test run failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

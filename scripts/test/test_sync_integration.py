#!/usr/bin/env python3
"""
Integration script for the synchronization workflow.

The script exercises:
1. Excel parsing
2. Change detection
3. Event creation
4. Read model updates
5. Basic post-sync verification
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import os
import sys
from pathlib import Path

from loguru import logger
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# `application.excel_parser.models` expects `application.domain`.
if "domain" not in sys.modules:
    importlib.import_module("domain")
if "application.domain" not in sys.modules:
    sys.modules["application.domain"] = sys.modules["domain"]


def setup_logging(log_level: str = "INFO") -> None:
    """Configure console logging for the integration script."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
        colorize=False,
    )


def setup_postgresql_environment() -> None:
    """Load PostgreSQL settings from `config.env` into the environment."""
    config_file = PROJECT_ROOT / "config.env"

    if config_file.exists():
        logger.info("Loading PostgreSQL configuration from {}", config_file)

        with config_file.open("r", encoding="utf-8") as file_obj:
            for raw_line in file_obj:
                line = raw_line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value
                    os.environ[key.lower()] = value
                    logger.debug("Set env var: {}={}", key, value)

        os.environ["DB_TYPE"] = "postgresql"
        os.environ["db_type"] = "postgresql"
        os.environ["DB_DB_TYPE"] = "postgresql"
        os.environ["DB_DB_HOST"] = os.environ.get("DB_HOST", "so_pg")
        os.environ["DB_DB_PORT"] = os.environ.get("DB_PORT", "5432")
        os.environ["DB_DB_NAME"] = os.environ.get("DB_NAME", "so_uchet")
        os.environ["DB_DB_USER"] = os.environ.get("DB_USER", "so_user")
        os.environ["DB_DB_PASSWORD"] = os.environ.get("DB_PASSWORD", "so_pass")
        os.environ["DB_DB_POOL_SIZE"] = os.environ.get("DB_POOL_SIZE", "10")
        os.environ["DB_DB_POOL_MAX_OVERFLOW"] = os.environ.get(
            "DB_POOL_MAX_OVERFLOW", "20"
        )
        os.environ["DB_DB_POOL_TIMEOUT"] = os.environ.get("DB_POOL_TIMEOUT", "30")
        os.environ["DB_DB_POOL_RECYCLE"] = os.environ.get("DB_POOL_RECYCLE", "3600")
        os.environ["DB_DB_CONNECT_TIMEOUT"] = os.environ.get("DB_CONNECT_TIMEOUT", "10")
        os.environ["DB_DB_QUERY_TIMEOUT"] = os.environ.get("DB_QUERY_TIMEOUT", "60")

        logger.info("PostgreSQL environment configured")
        return

    logger.warning("Config file not found: {}", config_file)
    logger.info("Using default PostgreSQL settings")


def get_interactive_choice() -> tuple[str, list[str], str]:
    """Ask the operator for sync mode and logging level."""
    print("\n" + "=" * 60)
    print("SYNC INTEGRATION TEST - INTERACTIVE MODE")
    print("=" * 60)

    print("\nChoose synchronization type:")
    print("1. Full synchronization")
    print("2. Partial synchronization")

    while True:
        try:
            choice = input("\nEnter 1 or 2: ").strip()
            if choice == "1":
                sync_type = "full"
                break
            if choice == "2":
                sync_type = "partial"
                break
            print("Invalid choice. Enter 1 or 2.")
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            raise SystemExit(0) from None

    partial_periods: list[str] = []
    if sync_type == "partial":
        print("\nEnter periods separated by commas, for example: 'Январь 2025, Февраль 2025'")
        while True:
            try:
                periods_input = input("Periods (Enter for all available): ").strip()
                if not periods_input:
                    break

                partial_periods = [
                    period.strip() for period in periods_input.split(",") if period.strip()
                ]
                if partial_periods:
                    break

                print("Enter at least one period.")
            except KeyboardInterrupt:
                print("\n\nCancelled.")
                raise SystemExit(0) from None

    print("\nChoose log level:")
    print("1. INFO")
    print("2. DEBUG")

    while True:
        try:
            log_choice = input("\nEnter 1 or 2: ").strip()
            if log_choice == "1":
                log_level = "INFO"
                break
            if log_choice == "2":
                log_level = "DEBUG"
                break
            print("Invalid choice. Enter 1 or 2.")
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            raise SystemExit(0) from None

    print("\n" + "=" * 60)
    print("CONFIRMATION")
    print(f"  Sync type: {sync_type}")
    if sync_type == "partial":
        periods_value = ", ".join(partial_periods) if partial_periods else "all available"
        print(f"  Periods: {periods_value}")
    print(f"  Log level: {log_level}")
    print("=" * 60)

    while True:
        try:
            confirm = input("\nStart test? (y/n): ").strip().lower()
            if confirm in {"y", "yes", "да", "д"}:
                return sync_type, partial_periods, log_level
            if confirm in {"n", "no", "нет", "н"}:
                print("Cancelled.")
                raise SystemExit(0)
            print("Enter 'y' to continue or 'n' to cancel.")
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            raise SystemExit(0) from None


async def test_sync(sync_type: str = "full", partial_periods: list[str] | None = None) -> bool:
    """Run the orchestrator against the real Excel file."""
    try:
        from application.change_detector import ChangeDetectorService
        from application.excel_parser import ExcelParserService
        from application.sync_orchestrator import SyncOrchestratorService
        from application.sync_orchestrator.models import SyncConfiguration
        from infrastructure.database.connection import DatabaseConfig, DatabaseManager
        from infrastructure.database.event_store import EventStoreImplementation
        from infrastructure.database.repositories import (
            DealRepositoryImplementation,
            SyncSessionRepositoryImplementation,
        )
        from infrastructure.workers.read_model_builder import ReadModelBuilder

        logger.info("Testing {} synchronization process", sync_type)

        config = DatabaseConfig()
        logger.info(
            "Database config: type={}, host={}, port={}, db={}",
            config.db_type,
            config.db_host,
            config.db_port,
            config.db_name,
        )

        db_manager = DatabaseManager(config)

        async with db_manager.get_async_session() as session:
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

            excel_file = PROJECT_ROOT / "data" / "real_data_for_testing" / "Data_source_excel.xlsx"
            if not excel_file.exists():
                logger.error("Excel file not found: {}", excel_file)
                return False

            sync_config = SyncConfiguration(
                sync_type=sync_type,
                partial_periods=partial_periods or [],
                max_retry_attempts=1,
                continue_on_errors=True,
                rollback_on_failure=False,
                create_events=True,
                update_read_models=True,
            )

            logger.info("Starting {} sync for file: {}", sync_type, excel_file)
            if sync_type == "partial" and partial_periods:
                logger.info("Target periods: {}", ", ".join(partial_periods))
            else:
                logger.info("Processing all available periods")

            result = await orchestrator.execute_sync(str(excel_file), sync_config)
            await session.commit()

            logger.info("{} synchronization completed", sync_type.capitalize())
            logger.info("Summary:")
            logger.info("  Success: {}", result.summary.success)
            logger.info("  Insertions: {}", result.summary.insertions_count)
            logger.info("  Updates: {}", result.summary.updates_count)
            logger.info("  Deletions: {}", result.summary.deletions_count)

            errors_count = len(result.summary.errors) if hasattr(result.summary, "errors") else 0
            logger.info("  Errors: {}", errors_count)
            return result.summary.success

    except Exception as exc:
        logger.exception("{} synchronization failed: {}", sync_type.capitalize(), exc)
        return False


async def test_data_verification() -> bool:
    """Verify that sync populated key tables."""
    try:
        from infrastructure.database.connection import DatabaseConfig, DatabaseManager

        logger.info("Verifying data after sync")

        config = DatabaseConfig()
        db_manager = DatabaseManager(config)

        async with db_manager.get_async_session() as session:
            deals_result = await session.execute(text("SELECT COUNT(*) FROM read_deals"))
            deals_count = deals_result.scalar()
            logger.info("Total deals in database: {}", deals_count)
            if not deals_count or deals_count <= 0:
                logger.error("Verification failed: read_deals is empty after sync")
                return False

            recent_deals_result = await session.execute(
                text(
                    """
                    SELECT client_name, invoice_number, total_revenue_amount
                    FROM read_deals
                    ORDER BY created_at DESC
                    LIMIT 5
                    """
                )
            )
            recent_deals = recent_deals_result.fetchall()
            logger.info("Recent deals:")
            for deal in recent_deals:
                logger.info("  - {} | {} | {}", deal[0], deal[1], deal[2])

            sessions_result = await session.execute(text("SELECT COUNT(*) FROM sync_sessions"))
            logger.info("Total sync sessions: {}", sessions_result.scalar())

            events_result = await session.execute(text("SELECT COUNT(*) FROM event_store"))
            events_count = events_result.scalar()
            logger.info("Total events: {}", events_count)
            if not events_count or events_count <= 0:
                logger.error("Verification failed: event_store is empty after sync")
                return False

            return True

    except Exception as exc:
        logger.exception("Data verification failed: {}", exc)
        return False


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test synchronization process with different types",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test/test_sync_integration.py
  python scripts/test/test_sync_integration.py --sync-type full
  python scripts/test/test_sync_integration.py --sync-type partial
  python scripts/test/test_sync_integration.py --log-level DEBUG
  python scripts/test/test_sync_integration.py --interactive
        """,
    )

    parser.add_argument(
        "--sync-type",
        choices=["full", "partial"],
        default="full",
        help="Type of synchronization to perform (default: full)",
    )
    parser.add_argument(
        "--log-level",
        choices=["INFO", "DEBUG"],
        default="INFO",
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode to choose sync type and parameters",
    )
    return parser.parse_args()


async def main() -> int:
    """Script entrypoint."""
    args = parse_arguments()

    if args.interactive:
        sync_type, partial_periods, log_level = get_interactive_choice()
    else:
        sync_type = args.sync_type
        partial_periods = []
        log_level = args.log_level

    setup_logging(log_level)
    setup_postgresql_environment()

    logger.info("Starting {} synchronization test with PostgreSQL", sync_type)
    logger.info(
        "Configuration: sync_type={}, partial_periods={}, log_level={}",
        sync_type,
        partial_periods,
        log_level,
    )

    sync_ok = await test_sync(sync_type, partial_periods)
    verify_ok = await test_data_verification()

    if sync_ok and verify_ok:
        logger.info("All {} synchronization checks passed", sync_type)
        return 0

    logger.error("Some {} synchronization checks failed", sync_type)
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

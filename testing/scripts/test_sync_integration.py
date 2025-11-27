#!/usr/bin/env python3
"""
Integration test for full synchronization process.

This script tests the complete synchronization workflow:
1. Excel file parsing
2. Change detection
3. Event creation
4. Read model updates
5. Data verification

Usage:
    python test_sync_integration.py [--sync-type full|incremental] [--period-months 12] [--log-level INFO|DEBUG]
    python test_sync_integration.py --interactive  # Interactive mode
"""

import asyncio
import sys
import argparse
import os
from pathlib import Path

# Ensure both 'src' (for top-level packages: application/domain/...) and project root (for 'src' pkg)
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Workaround for relative import in 'application.excel_parser.models' expecting 'application.domain'
try:  # Do not fail hard in scripts
    import importlib
    if 'domain' not in sys.modules:
        importlib.import_module('domain')
    if 'application.domain' not in sys.modules:
        sys.modules['application.domain'] = sys.modules['domain']
except Exception:
    pass

from loguru import logger


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration."""
    # Remove default logger
    logger.remove()
    
    # Add custom logger with specified level
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )


def setup_postgresql_environment():
    """Setup PostgreSQL environment variables from config.env."""
    config_file = Path(__file__).parent.parent.parent / "config.env"
    
    if config_file.exists():
        logger.info(f"📁 Loading PostgreSQL configuration from: {config_file}")
        
        # Read config.env and set environment variables
        with open(config_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Set both uppercase and lowercase versions for compatibility
                    os.environ[key] = value
                    os.environ[key.lower()] = value
                    logger.debug(f"🔧 Set env var: {key}={value}")
        
        # Ensure PostgreSQL is selected
        os.environ["DB_TYPE"] = "postgresql"
        os.environ["db_type"] = "postgresql"
        
        # Set variables with DB_ prefix for pydantic-settings
        # DatabaseConfig uses env_prefix="DB_" and field names like db_host, db_port
        # So it looks for DB_DB_HOST, DB_DB_PORT, etc.
        os.environ["DB_DB_TYPE"] = "postgresql"
        os.environ["DB_DB_HOST"] = os.environ.get("DB_HOST", "so_pg")
        os.environ["DB_DB_PORT"] = os.environ.get("DB_PORT", "5432")
        os.environ["DB_DB_NAME"] = os.environ.get("DB_NAME", "so_uchet")
        os.environ["DB_DB_USER"] = os.environ.get("DB_USER", "so_user")
        os.environ["DB_DB_PASSWORD"] = os.environ.get("DB_PASSWORD", "so_pass")
        os.environ["DB_DB_POOL_SIZE"] = os.environ.get("DB_POOL_SIZE", "10")
        os.environ["DB_DB_POOL_MAX_OVERFLOW"] = os.environ.get("DB_POOL_MAX_OVERFLOW", "20")
        os.environ["DB_DB_POOL_TIMEOUT"] = os.environ.get("DB_POOL_TIMEOUT", "30")
        os.environ["DB_DB_POOL_RECYCLE"] = os.environ.get("DB_POOL_RECYCLE", "3600")
        os.environ["DB_DB_CONNECT_TIMEOUT"] = os.environ.get("DB_CONNECT_TIMEOUT", "10")
        os.environ["DB_DB_QUERY_TIMEOUT"] = os.environ.get("DB_QUERY_TIMEOUT", "60")
        
        logger.info("✅ PostgreSQL environment configured")
        
        # Log current environment variables for debugging
        logger.debug(f"🔧 Environment variables set:")
        logger.debug(f"  DB_TYPE: {os.environ.get('DB_TYPE', 'NOT_SET')}")
        logger.debug(f"  db_type: {os.environ.get('db_type', 'NOT_SET')}")
        logger.debug(f"  DB_DB_TYPE: {os.environ.get('DB_DB_TYPE', 'NOT_SET')}")
        logger.debug(f"  DB_DB_HOST: {os.environ.get('DB_DB_HOST', 'NOT_SET')}")
        logger.debug(f"  DB_DB_PORT: {os.environ.get('DB_DB_PORT', 'NOT_SET')}")
        logger.debug(f"  DB_DB_NAME: {os.environ.get('DB_DB_NAME', 'NOT_SET')}")
    else:
        logger.warning(f"⚠️ Config file not found: {config_file}")
        logger.info("🔧 Using default PostgreSQL settings")


def get_interactive_choice():
    """Get user choice for sync type and parameters interactively."""
    print("\n" + "="*60)
    print("🔄 SYNC INTEGRATION TEST - INTERACTIVE MODE")
    print("="*60)
    
    # Choose sync type
    print("\n📋 Выберите тип синхронизации:")
    print("1. Полная синхронизация (весь Excel файл)")
    print("2. Частичная синхронизация (выборочные периоды)")
    
    while True:
        try:
            choice = input("\nВведите номер (1 или 2): ").strip()
            if choice == "1":
                sync_type = "full"
                break
            elif choice == "2":
                sync_type = "partial"
                break
            else:
                print("❌ Неверный выбор. Введите 1 или 2.")
        except KeyboardInterrupt:
            print("\n\n👋 Выход из программы.")
            sys.exit(0)
    
    # Get periods for partial sync
    partial_periods = []
    if sync_type == "partial":
        print(f"\n📅 Выборочные периоды для частичной синхронизации")
        print("Введите периоды через запятую (например: 'Январь 2025, Февраль 2025')")
        while True:
            try:
                periods_input = input("Периоды (Enter для всех доступных): ").strip()
                if periods_input == "":
                    partial_periods = []  # Will sync all available periods
                    break
                # Parse comma-separated periods
                partial_periods = [p.strip() for p in periods_input.split(',') if p.strip()]
                if partial_periods:
                    break
                else:
                    print("❌ Введите хотя бы один период.")
            except KeyboardInterrupt:
                print("\n\n👋 Выход из программы.")
                sys.exit(0)
    
    # Choose log level
    print("\n📝 Выберите уровень логирования:")
    print("1. INFO (основная информация)")
    print("2. DEBUG (детальные логи)")
    
    while True:
        try:
            log_choice = input("\nВведите номер (1 или 2): ").strip()
            if log_choice == "1":
                log_level = "INFO"
                break
            elif log_choice == "2":
                log_level = "DEBUG"
                break
            else:
                print("❌ Неверный выбор. Введите 1 или 2.")
        except KeyboardInterrupt:
            print("\n\n👋 Выход из программы.")
            sys.exit(0)
    
    # Confirm choice
    print("\n" + "="*60)
    print("📋 ПОДТВЕРЖДЕНИЕ ВЫБОРА:")
    print(f"   Тип синхронизации: {sync_type}")
    if sync_type == "partial":
        if partial_periods:
            print(f"   Периоды: {', '.join(partial_periods)}")
        else:
            print(f"   Периоды: все доступные")
    print(f"   Уровень логирования: {log_level}")
    print("="*60)
    
    while True:
        try:
            confirm = input("\nЗапустить тест? (y/n): ").strip().lower()
            if confirm in ['y', 'yes', 'да', 'д']:
                return sync_type, partial_periods, log_level
            elif confirm in ['n', 'no', 'нет', 'н']:
                print("👋 Отменено.")
                sys.exit(0)
            else:
                print("❌ Введите 'y' для подтверждения или 'n' для отмены.")
        except KeyboardInterrupt:
            print("\n\n👋 Выход из программы.")
            sys.exit(0)


async def test_sync(sync_type: str = "full", partial_periods: list[str] = None):
    """Test synchronization process with specified type."""
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

        logger.info(f"🔄 Testing {sync_type} synchronization process...")

        # Setup database with PostgreSQL configuration
        config = DatabaseConfig()
        logger.info(f"🔧 Database config: type={config.db_type}, host={config.db_host}, port={config.db_port}, db={config.db_name}")
        
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

            # Excel file path - use absolute path from project root
            excel_file = Path(__file__).parent.parent.parent / "data" / "real_data_for_testing" / "Data_source_excel.xlsx"

            if not excel_file.exists():
                logger.error(f"❌ Excel file not found: {excel_file}")
                return False

            # Configure sync based on type
            sync_config = SyncConfiguration(
                sync_type=sync_type,
                partial_periods=partial_periods or [],
                max_retry_attempts=1,
                continue_on_errors=True,
                rollback_on_failure=False,
                create_events=True,
                update_read_models=True,
            )

            logger.info(f"📁 Starting {sync_type} sync for file: {excel_file}")
            if sync_type == "partial" and partial_periods:
                logger.info(f"📅 Target periods: {', '.join(partial_periods)}")
            else:
                logger.info(f"📅 Processing: all available periods")

            # Execute sync
            result = await orchestrator.execute_sync(str(excel_file), sync_config)

            # Commit the transaction
            await session.commit()

            logger.info(f"✅ {sync_type.capitalize()} synchronization completed!")
            logger.info("📊 Summary:")
            logger.info(f"  - Success: {result.summary.success}")
            logger.info(f"  - Insertions: {result.summary.insertions_count}")
            logger.info(f"  - Updates: {result.summary.updates_count}")
            logger.info(f"  - Deletions: {result.summary.deletions_count}")
            
            if hasattr(result.summary, 'errors') and result.summary.errors:
                logger.info(f"  - Errors: {len(result.summary.errors)}")
            else:
                logger.info(f"  - Errors: 0")

            return result.summary.success

    except Exception as e:
        logger.error(f"❌ {sync_type.capitalize()} synchronization failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def test_data_verification():
    """Verify data after sync."""
    try:
        from infrastructure.database.connection import DatabaseConfig, DatabaseManager

        logger.info("🔍 Verifying data after sync...")

        config = DatabaseConfig()
        db_manager = DatabaseManager(config)

        async with db_manager.get_async_session() as session:
            from sqlalchemy import text

            # Check deals count
            result = await session.execute(text("SELECT COUNT(*) FROM read_deals"))
            deals_count = result.scalar()
            logger.info(f"📊 Total deals in database: {deals_count}")

            # Check recent deals
            result = await session.execute(
                text("SELECT client_name, invoice_number, total_revenue_amount FROM read_deals ORDER BY created_at DESC LIMIT 5")
            )
            recent_deals = result.fetchall()
            logger.info("📋 Recent deals:")
            for deal in recent_deals:
                logger.info(f"  - {deal[0]} | {deal[1]} | {deal[2]}")

            # Check sync sessions
            result = await session.execute(text("SELECT COUNT(*) FROM sync_sessions"))
            sessions_count = result.scalar()
            logger.info(f"📊 Total sync sessions: {sessions_count}")

            # Check events
            result = await session.execute(text("SELECT COUNT(*) FROM event_store"))
            events_count = result.scalar()
            logger.info(f"📊 Total events: {events_count}")

            return True

    except Exception as e:
        logger.error(f"❌ Data verification failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test synchronization process with different types",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_sync_integration.py                                    # Full sync (default)
  python test_sync_integration.py --sync-type full                   # Full sync
  python test_sync_integration.py --sync-type partial                # Partial sync (all periods) 
  python test_sync_integration.py --log-level DEBUG                  # Full sync with debug logs
  python test_sync_integration.py --interactive                      # Interactive mode
        """
    )
    
    parser.add_argument(
        "--sync-type",
        choices=["full", "partial"],
        default="full",
        help="Type of synchronization to perform (default: full)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["INFO", "DEBUG"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode to choose sync type and parameters"
    )
    
    return parser.parse_args()


async def main():
    """Main test function."""
    args = parse_arguments()
    
    # Interactive mode
    if args.interactive:
        sync_type, partial_periods, log_level = get_interactive_choice()
    else:
        sync_type = args.sync_type
        partial_periods = []  # For non-interactive mode, default to empty (all periods)
        log_level = args.log_level
    
    # Setup logging
    setup_logging(log_level)
    
    # Setup PostgreSQL environment
    setup_postgresql_environment()
    
    logger.info(f"🚀 Starting {sync_type} synchronization tests with PostgreSQL...")
    logger.info(f"📋 Configuration: sync_type={sync_type}, partial_periods={partial_periods}, log_level={log_level}")

    # Test 1: Sync
    success1 = await test_sync(sync_type, partial_periods)

    # Test 2: Data verification
    success2 = await test_data_verification()

    if success1 and success2:
        logger.info(f"🎉 All {sync_type} synchronization tests passed successfully!")
    else:
        logger.error(f"💥 Some {sync_type} synchronization tests failed!")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

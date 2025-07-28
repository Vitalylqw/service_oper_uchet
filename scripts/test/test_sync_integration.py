#!/usr/bin/env python3
"""
Test full synchronization with real data.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger


async def test_full_sync():
    """Test full synchronization process."""
    
    try:
        from application.change_detector import ChangeDetectorService
        from application.excel_parser import ExcelParserService
        from application.sync_orchestrator import SyncOrchestratorService
        from application.sync_orchestrator.models import SyncConfiguration
        from domain.models import SyncSession, SyncType
        from infrastructure.database.connection import DatabaseConfig, DatabaseManager
        from infrastructure.database.event_store import EventStoreImplementation
        from infrastructure.database.repositories import (
            DealRepositoryImplementation,
            SyncSessionRepositoryImplementation,
        )
        
        logger.info("🔄 Testing full synchronization process...")
        
        # Setup database
        config = DatabaseConfig()
        db_manager = DatabaseManager(config)
        
        async with db_manager.get_async_session() as session:
            # Initialize services
            deal_repo = DealRepositoryImplementation(session)
            change_detector = ChangeDetectorService(deal_repo)
            event_store = EventStoreImplementation(session)
            sync_session_repo = SyncSessionRepositoryImplementation(session)
            parser = ExcelParserService()
            
            orchestrator = SyncOrchestratorService(
                excel_parser=parser,
                change_detector=change_detector,
                event_store=event_store,
                sync_session_repository=sync_session_repo,
            )
            
            # Excel file path
            excel_file = Path("data/real_data_for_testing/Data_source_excel.xlsx")
            
            if not excel_file.exists():
                logger.error(f"❌ Excel file not found: {excel_file}")
                return False
            
            # Configure sync
            sync_config = SyncConfiguration(
                sync_type="incremental",
                incremental_period_months=12,
                max_retry_attempts=1,
                continue_on_errors=True,
                rollback_on_failure=False,
                create_events=True,
                update_read_models=True,
            )
            
            logger.info(f"📁 Starting sync for file: {excel_file}")
            
            # Execute sync
            result = await orchestrator.execute_sync(str(excel_file), sync_config)
            
            logger.info("✅ Synchronization completed!")
            logger.info("📊 Summary:")
            logger.info(f"  - Success: {result.summary.success}")
            logger.info(f"  - Insertions: {result.summary.insertions_count}")
            logger.info(f"  - Updates: {result.summary.updates_count}")
            logger.info(f"  - Deletions: {result.summary.deletions_count}")
            # Check for errors if they exist
            if hasattr(result.summary, 'errors') and result.summary.errors:
                logger.info(f"  - Errors: {len(result.summary.errors)}")
                logger.warning("⚠️ Sync errors:")
                for error in result.summary.errors[:3]:
                    logger.warning(f"  - {error}")
            else:
                logger.info("  - Errors: 0")
            
            return result.summary.success
            
    except Exception as e:
        logger.error(f"❌ Full sync test failed: {e}")
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


async def main():
    """Main test function."""
    logger.info("🚀 Starting full synchronization tests...")
    
    # Test 1: Full sync
    success1 = await test_full_sync()
    
    # Test 2: Data verification
    success2 = await test_data_verification()
    
    if success1 and success2:
        logger.info("🎉 All synchronization tests passed successfully!")
    else:
        logger.error("💥 Some synchronization tests failed!")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

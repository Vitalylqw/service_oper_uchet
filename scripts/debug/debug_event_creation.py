#!/usr/bin/env python3
"""
Debug script for event creation issues.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loguru import logger
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


async def debug_event_creation():
    """Debug event creation issues."""
    logger.info("🔍 Debugging event creation issues...")
    
    # Create database manager
    db_config = DatabaseConfig()
    db_manager = DatabaseManager(db_config)
    
    # Get database session
    async with db_manager.get_async_session() as session:
        deal_repository = DealRepositoryImplementation(session)
        sync_session_repository = SyncSessionRepositoryImplementation(session)
        event_store = EventStoreImplementation(session)
        
        # Create application services
        excel_parser = ExcelParserService()
        
        # Create orchestrator
        sync_orchestrator = SyncOrchestratorService(
            excel_parser=excel_parser,
            change_detector=None,  # Not needed for this test
            event_store=event_store,
            sync_session_repository=sync_session_repository,
        )
        
        # Path to real Excel file
        excel_file = Path("data/real_data_for_testing/Data_source_excel.xlsx")
        
        if not excel_file.exists():
            logger.error(f"❌ Excel file not found: {excel_file}")
            return
        
        logger.info(f"📁 Processing file: {excel_file}")
        
        # Create sync configuration
        config = SyncConfiguration(
            sync_type="full",
            create_events=True,
            update_read_models=False,  # Disable for this test
            rollback_on_failure=False,
        )
        
        # Execute sync
        result = await sync_orchestrator.execute_sync(str(excel_file), config)
        
        logger.info("✅ Sync completed!")
        logger.info(f"📊 Total deals processed: {result.summary.total_deals_processed}")
        logger.info(f"📊 Events created: {len(result.events_created) if result.events_created else 0}")
        
        # Check for events with invalid periods
        if result.events_created:
            invalid_period_events = []
            
            for i, event in enumerate(result.events_created):
                if event.get("event_type") == "DealCreated":
                    event_data = event.get("event_data", {})
                    period_data = event_data.get("period", {})
                    
                    if not period_data or not period_data.get("month") or not period_data.get("year"):
                        invalid_period_events.append((i, event, "Empty period data"))
                    elif period_data.get("month") == "Unknown" or period_data.get("year") == "0000":
                        invalid_period_events.append((i, event, "Invalid period values"))
            
            if invalid_period_events:
                logger.warning(f"⚠️ Found {len(invalid_period_events)} events with invalid periods:")
                for i, event, reason in invalid_period_events[:5]:  # Show first 5
                    event_data = event.get("event_data", {})
                    client_name = event_data.get("client_name", "UNKNOWN")
                    period_data = event_data.get("period", {})
                    logger.warning(f"  Event {i}: {client_name} - {reason}")
                    logger.warning(f"    Period: {period_data}")
            else:
                logger.info("✅ All events have valid periods!")


if __name__ == "__main__":
    asyncio.run(debug_event_creation())
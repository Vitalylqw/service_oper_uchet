#!/usr/bin/env python3
"""
Debug script to examine what changes are detected during sync.

This script will run sync with debug logging to see exactly what 
changes are being detected and why.
"""

import sys
import os
import asyncio
from loguru import logger

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

# Configure detailed logging
logger.remove()
logger.add(
    sys.stdout,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    filter=lambda record: "change_detector" in record["name"] or "orchestrator" in record["name"]
)

from application.sync_orchestrator import SyncOrchestratorService
from infrastructure.database import DatabaseManager


async def debug_changes():
    """Debug what changes are detected during sync."""
    logger.info("🔍 Debugging change detection...")
    
    # Configuration
    file_path = "/workspaces/service_oper_uchet/data/real_data_for_testing/Data_source_excel.xlsx"
    
    # Setup database
    logger.info("🔧 Setting up database connection...")
    db_manager = DatabaseManager(
        database_url="postgresql://postgres:postgres@so_pg:5432/so_uchet"
    )
    await db_manager.initialize()
    
    # Setup orchestrator
    orchestrator = SyncOrchestratorService(db_manager)
    
    try:
        logger.info("🔄 Running sync with detailed change detection logging...")
        
        result = await orchestrator.execute_sync(
            file_path=file_path,
            sync_type="full"
        )
        
        if result.success:
            logger.info("✅ Sync completed successfully")
            logger.info(f"📊 Summary: {result.change_summary.insertion_count} insertions, "
                       f"{result.change_summary.update_count} updates, "
                       f"{result.change_summary.deletion_count} deletions")
        else:
            logger.error(f"❌ Sync failed: {result.error}")
        
    finally:
        await db_manager.cleanup()


async def main():
    """Main function."""
    try:
        await debug_changes()
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

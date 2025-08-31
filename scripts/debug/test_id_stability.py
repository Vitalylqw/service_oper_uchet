#!/usr/bin/env python3
"""
Test script to verify ID stability between synchronizations.

This script runs multiple sync cycles and checks if Deal and DealItem IDs 
remain stable between runs.
"""

import sys
import os
import asyncio
from loguru import logger

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from application.sync_orchestrator import SyncOrchestratorService
from infrastructure.database import DatabaseManager
from infrastructure.database.repositories import ReadModelRepository


async def get_all_deal_ids(db_manager: DatabaseManager) -> dict[str, str]:
    """Get all deal_key -> id mappings from read_deals table."""
    read_repo = ReadModelRepository(db_manager.session_manager)
    
    query = """
    SELECT deal_key, id 
    FROM read_deals 
    ORDER BY deal_key
    """
    
    async with db_manager.session_manager.get_session() as session:
        result = await session.execute(query)
        rows = result.fetchall()
        
    return {row[0]: str(row[1]) for row in rows}


async def get_all_item_ids(db_manager: DatabaseManager) -> dict[str, str]:
    """Get all item hash_key -> id mappings from read_positions table."""
    read_repo = ReadModelRepository(db_manager.session_manager)
    
    query = """
    SELECT hash_key, id 
    FROM read_positions 
    ORDER BY hash_key
    """
    
    async with db_manager.session_manager.get_session() as session:
        result = await session.execute(query)
        rows = result.fetchall()
        
    return {row[0]: str(row[1]) for row in rows}


async def run_sync_cycle(orchestrator: SyncOrchestratorService, file_path: str, cycle_num: int) -> None:
    """Run one synchronization cycle."""
    logger.info(f"🔄 Running sync cycle #{cycle_num}...")
    
    result = await orchestrator.execute_sync(
        file_path=file_path,
        sync_type="full"
    )
    
    if result.success:
        logger.info(f"✅ Cycle #{cycle_num} completed successfully")
        logger.info(f"   Changes: {result.change_summary.insertion_count} insertions, "
                   f"{result.change_summary.update_count} updates, "
                   f"{result.change_summary.deletion_count} deletions")
    else:
        logger.error(f"❌ Cycle #{cycle_num} failed: {result.error}")
        raise Exception(f"Sync cycle #{cycle_num} failed")


async def test_id_stability():
    """Test ID stability across multiple sync cycles."""
    logger.info("🧪 Testing ID stability across multiple sync cycles...")
    
    # Configuration
    file_path = "/workspaces/service_oper_uchet/data/real_data_for_testing/Data_source_excel.xlsx"
    num_cycles = 3
    
    # Setup database
    logger.info("🔧 Setting up database connection...")
    db_manager = DatabaseManager(
        database_url="postgresql://postgres:postgres@so_pg:5432/so_uchet"
    )
    await db_manager.initialize()
    
    # Setup orchestrator
    orchestrator = SyncOrchestratorService(db_manager)
    
    # Store ID mappings from each cycle
    deal_ids_by_cycle = {}
    item_ids_by_cycle = {}
    
    try:
        for cycle in range(1, num_cycles + 1):
            # Run sync
            await run_sync_cycle(orchestrator, file_path, cycle)
            
            # Capture IDs after sync
            deal_ids = await get_all_deal_ids(db_manager)
            item_ids = await get_all_item_ids(db_manager)
            
            deal_ids_by_cycle[cycle] = deal_ids
            item_ids_by_cycle[cycle] = item_ids
            
            logger.info(f"📊 Cycle #{cycle}: {len(deal_ids)} deals, {len(item_ids)} items")
            
            # Compare with previous cycle
            if cycle > 1:
                logger.info(f"🔍 Comparing cycle #{cycle} with cycle #{cycle-1}...")
                
                # Compare deal IDs
                prev_deal_ids = deal_ids_by_cycle[cycle-1]
                deal_changes = []
                
                for deal_key in deal_ids:
                    if deal_key in prev_deal_ids:
                        if deal_ids[deal_key] != prev_deal_ids[deal_key]:
                            deal_changes.append({
                                "deal_key": deal_key,
                                "old_id": prev_deal_ids[deal_key],
                                "new_id": deal_ids[deal_key]
                            })
                
                # Compare item IDs  
                prev_item_ids = item_ids_by_cycle[cycle-1]
                item_changes = []
                
                for hash_key in item_ids:
                    if hash_key in prev_item_ids:
                        if item_ids[hash_key] != prev_item_ids[hash_key]:
                            item_changes.append({
                                "hash_key": hash_key,
                                "old_id": prev_item_ids[hash_key],
                                "new_id": item_ids[hash_key]
                            })
                
                # Report results
                if deal_changes:
                    logger.error(f"❌ Found {len(deal_changes)} Deal ID changes between cycles!")
                    for change in deal_changes[:5]:  # Show first 5
                        logger.error(f"   Deal '{change['deal_key']}': {change['old_id']} → {change['new_id']}")
                    if len(deal_changes) > 5:
                        logger.error(f"   ... and {len(deal_changes) - 5} more changes")
                else:
                    logger.info("✅ No Deal ID changes between cycles")
                
                if item_changes:
                    logger.error(f"❌ Found {len(item_changes)} DealItem ID changes between cycles!")
                    for change in item_changes[:5]:  # Show first 5
                        logger.error(f"   Item '{change['hash_key'][:50]}...': {change['old_id']} → {change['new_id']}")
                    if len(item_changes) > 5:
                        logger.error(f"   ... and {len(item_changes) - 5} more changes")
                else:
                    logger.info("✅ No DealItem ID changes between cycles")
        
        # Final summary
        logger.info("\n" + "="*60)
        logger.info("📊 ID STABILITY TEST SUMMARY")
        logger.info("="*60)
        
        total_deal_changes = 0
        total_item_changes = 0
        
        for cycle in range(2, num_cycles + 1):
            deal_ids = deal_ids_by_cycle[cycle]
            prev_deal_ids = deal_ids_by_cycle[cycle-1]
            
            cycle_deal_changes = 0
            cycle_item_changes = 0
            
            for deal_key in deal_ids:
                if deal_key in prev_deal_ids and deal_ids[deal_key] != prev_deal_ids[deal_key]:
                    cycle_deal_changes += 1
                    
            item_ids = item_ids_by_cycle[cycle]
            prev_item_ids = item_ids_by_cycle[cycle-1]
            
            for hash_key in item_ids:
                if hash_key in prev_item_ids and item_ids[hash_key] != prev_item_ids[hash_key]:
                    cycle_item_changes += 1
            
            total_deal_changes += cycle_deal_changes
            total_item_changes += cycle_item_changes
            
            logger.info(f"Cycle #{cycle-1} → #{cycle}: {cycle_deal_changes} deal changes, {cycle_item_changes} item changes")
        
        if total_deal_changes == 0 and total_item_changes == 0:
            logger.info("🎉 SUCCESS: All IDs remained stable across all cycles!")
        else:
            logger.error(f"❌ FAILURE: Found {total_deal_changes} deal ID changes and {total_item_changes} item ID changes")
        
        logger.info("="*60)
        
    finally:
        await db_manager.cleanup()


async def main():
    """Main function."""
    try:
        await test_id_stability()
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

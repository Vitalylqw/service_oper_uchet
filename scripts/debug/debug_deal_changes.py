#!/usr/bin/env python3
"""
Debug script to examine what exactly changes in read_deals during sync.

This script will capture deal states before and after sync and show differences.
"""

import sys
import os
import asyncio
from typing import Dict, Any
from loguru import logger

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from infrastructure.database.connection import DatabaseConfig, DatabaseManager
from application.sync_orchestrator import SyncOrchestratorService


async def capture_deals_state(db_manager: DatabaseManager) -> Dict[str, Dict[str, Any]]:
    """Capture current state of all deals in read_deals table."""
    async with db_manager.get_async_session() as session:
        from sqlalchemy import text
        
        result = await session.execute(text("""
            SELECT 
                deal_key,
                id,
                hash_key, 
                client_name,
                invoice_info,
                invoice_number,
                invoice_date,
                is_shipped,
                is_paid,
                seller,
                upd_number,
                total_revenue_amount,
                total_margin_amount,
                total_cost_amount,
                kickback_amount_amount,
                created_at,
                updated_at
            FROM read_deals
            ORDER BY deal_key
        """))
        
        deals = {}
        for row in result.fetchall():
            deal_key = row[0]
            deals[deal_key] = {
                'id': str(row[1]),
                'hash_key': row[2],
                'client_name': row[3],
                'invoice_info': row[4],
                'invoice_number': row[5],
                'invoice_date': row[6],
                'is_shipped': row[7],
                'is_paid': row[8],
                'seller': row[9],
                'upd_number': row[10],
                'total_revenue_amount': str(row[11]) if row[11] else None,
                'total_margin_amount': str(row[12]) if row[12] else None,
                'total_cost_amount': str(row[13]) if row[13] else None,
                'kickback_amount_amount': str(row[14]) if row[14] else None,
                'created_at': str(row[15]) if row[15] else None,
                'updated_at': str(row[16]) if row[16] else None,
            }
        
        return deals


def compare_deals_states(before: Dict[str, Dict[str, Any]], after: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Compare two deal states and return differences."""
    changes = {
        'id_changes': [],
        'field_changes': {},
        'new_deals': [],
        'deleted_deals': []
    }
    
    # Check for new/deleted deals
    before_keys = set(before.keys())
    after_keys = set(after.keys())
    
    changes['new_deals'] = list(after_keys - before_keys)
    changes['deleted_deals'] = list(before_keys - after_keys)
    
    # Check for changes in existing deals
    common_keys = before_keys & after_keys
    
    for deal_key in common_keys:
        before_deal = before[deal_key]
        after_deal = after[deal_key]
        
        # Check ID changes
        if before_deal['id'] != after_deal['id']:
            changes['id_changes'].append({
                'deal_key': deal_key,
                'old_id': before_deal['id'],
                'new_id': after_deal['id']
            })
        
        # Check field changes
        field_changes = {}
        for field in before_deal:
            if before_deal[field] != after_deal[field]:
                field_changes[field] = {
                    'old': before_deal[field],
                    'new': after_deal[field]
                }
        
        if field_changes:
            changes['field_changes'][deal_key] = field_changes
    
    return changes


async def debug_deal_changes():
    """Debug what changes in deals during sync."""
    logger.info("🔍 Debugging deal changes during sync...")
    
    # Configuration
    file_path = "/workspaces/service_oper_uchet/data/real_data_for_testing/Data_source_excel.xlsx"
    
    # Setup database
    config = DatabaseConfig()
    db_manager = DatabaseManager(config)
    orchestrator = SyncOrchestratorService(db_manager)
    
    try:
        # Step 1: Capture state before sync
        logger.info("📸 Capturing deal state BEFORE sync...")
        before_state = await capture_deals_state(db_manager)
        logger.info(f"   Found {len(before_state)} deals")
        
        # Step 2: Run sync
        logger.info("🔄 Running synchronization...")
        result = await orchestrator.execute_sync(
            file_path=file_path,
            sync_type="full"
        )
        
        if result.success:
            logger.info("✅ Sync completed successfully")
            logger.info(f"📊 Changes: {result.change_summary.insertion_count} insertions, "
                       f"{result.change_summary.update_count} updates, "
                       f"{result.change_summary.deletion_count} deletions")
        else:
            logger.error(f"❌ Sync failed: {result.error}")
            return
        
        # Step 3: Capture state after sync
        logger.info("📸 Capturing deal state AFTER sync...")
        after_state = await capture_deals_state(db_manager)
        logger.info(f"   Found {len(after_state)} deals")
        
        # Step 4: Compare states
        logger.info("🔍 Comparing deal states...")
        changes = compare_deals_states(before_state, after_state)
        
        # Report results
        print("\n" + "="*70)
        print("📊 DEAL CHANGES ANALYSIS")
        print("="*70)
        
        print(f"\n📋 Summary:")
        print(f"   Deals before: {len(before_state)}")
        print(f"   Deals after: {len(after_state)}")
        print(f"   New deals: {len(changes['new_deals'])}")
        print(f"   Deleted deals: {len(changes['deleted_deals'])}")
        print(f"   ID changes: {len(changes['id_changes'])}")
        print(f"   Field changes: {len(changes['field_changes'])}")
        
        # ID changes (this is what we're most concerned about)
        if changes['id_changes']:
            print(f"\n❌ ID CHANGES ({len(changes['id_changes'])}):")
            for change in changes['id_changes']:
                print(f"   Deal: {change['deal_key']}")
                print(f"   Old ID: {change['old_id']}")
                print(f"   New ID: {change['new_id']}")
                print()
        else:
            print("\n✅ NO ID CHANGES - IDs are stable!")
        
        # Field changes
        if changes['field_changes']:
            print(f"\n🔧 FIELD CHANGES ({len(changes['field_changes'])} deals):")
            for deal_key, field_changes in list(changes['field_changes'].items())[:5]:  # Show first 5
                print(f"\n   Deal: {deal_key}")
                for field, change in field_changes.items():
                    print(f"     {field}: '{change['old']}' → '{change['new']}'")
            
            if len(changes['field_changes']) > 5:
                print(f"\n   ... and {len(changes['field_changes']) - 5} more deals with changes")
        else:
            print("\n✅ NO FIELD CHANGES - All data is stable!")
        
        # New/deleted deals
        if changes['new_deals']:
            print(f"\n➕ NEW DEALS ({len(changes['new_deals'])}):")
            for deal_key in changes['new_deals'][:5]:
                print(f"   {deal_key}")
        
        if changes['deleted_deals']:
            print(f"\n➖ DELETED DEALS ({len(changes['deleted_deals'])}):")
            for deal_key in changes['deleted_deals'][:5]:
                print(f"   {deal_key}")
        
        print("\n" + "="*70)
        
        # Final assessment
        if not changes['id_changes'] and not changes['field_changes'] and not changes['new_deals'] and not changes['deleted_deals']:
            print("🎉 PERFECT: No changes detected - data is completely stable!")
        elif changes['id_changes']:
            print("❌ CRITICAL: ID changes detected - deterministic ID generation needs fixing!")
        elif changes['field_changes']:
            print("⚠️  WARNING: Field changes detected - some data is not stable between syncs")
        else:
            print("ℹ️  INFO: Only new/deleted deals - this might be expected")
        
    finally:
        await db_manager.cleanup()


async def main():
    """Main function."""
    try:
        await debug_deal_changes()
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

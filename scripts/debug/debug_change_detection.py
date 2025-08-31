#!/usr/bin/env python3
"""
Debug script to understand why change detection reports updates when no data changes.

This will help identify the root cause of unnecessary DealUpdated events.
"""

import sys
import os
import asyncio
from loguru import logger

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

# Configure detailed logging for change detection
logger.remove()
logger.add(
    sys.stdout,
    level="DEBUG",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    filter=lambda record: "change_detector" in record["name"] or "detector" in record["name"]
)

from infrastructure.database.connection import DatabaseConfig, DatabaseManager
from application.change_detector import ChangeDetectorService
from application.excel_parser import ExcelParserService


async def debug_change_detection():
    """Debug why change detection reports updates when no data changes."""
    print("🔍 Debugging change detection logic...")
    
    # Configuration
    file_path = "/workspaces/service_oper_uchet/data/real_data_for_testing/Data_source_excel.xlsx"
    
    # Setup database and services
    config = DatabaseConfig()
    db_manager = DatabaseManager(config)
    
    excel_parser = ExcelParserService()
    change_detector = ChangeDetectorService(db_manager)
    
    try:
        print("📋 Step 1: Parse Excel data...")
        parse_result = await excel_parser.parse_file(file_path)
        print(f"   Parsed {len(parse_result.deals)} deals from Excel")
        
        print("\n🔍 Step 2: Run change detection...")
        change_result = await change_detector.detect_changes(parse_result.deals)
        
        print(f"\n📊 Change detection results:")
        print(f"   Total changes: {change_result.total_changes}")
        print(f"   Insertions: {change_result.insertion_count}")
        print(f"   Updates: {change_result.update_count}")
        print(f"   Deletions: {change_result.deletion_count}")
        
        # Analyze the updates in detail
        if change_result.updates:
            print(f"\n🔬 Analyzing {len(change_result.updates)} update changes...")
            
            for i, change in enumerate(change_result.updates[:3]):  # First 3 updates
                print(f"\n--- UPDATE #{i+1} ---")
                print(f"Entity type: {change.entity_type.value}")
                print(f"Entity key: {change.entity_key}")
                print(f"Old hash: {change.old_hash}")
                print(f"New hash: {change.new_hash}")
                print(f"Hash match: {change.old_hash == change.new_hash}")
                
                if change.field_changes:
                    print(f"Field changes ({len(change.field_changes)}):")
                    for field, changes in change.field_changes.items():
                        old_val = changes.get('old_value', 'N/A')
                        new_val = changes.get('new_value', 'N/A')
                        print(f"   {field}: '{old_val}' → '{new_val}'")
                else:
                    print("No field changes detected")
                
                # Compare entities directly if available
                if change.old_entity and change.new_entity:
                    print(f"\nEntity comparison:")
                    old_entity = change.old_entity
                    new_entity = change.new_entity
                    
                    print(f"   Old entity ID: {old_entity.id}")
                    print(f"   New entity ID: {new_entity.id}")
                    print(f"   ID match: {old_entity.id == new_entity.id}")
                    
                    print(f"   Old deal_key: {old_entity.deal_key}")
                    print(f"   New deal_key: {new_entity.deal_key}")
                    print(f"   Deal key match: {old_entity.deal_key == new_entity.deal_key}")
                    
                    # Check some key fields
                    fields_to_check = ['client_name', 'invoice_number', 'total_revenue', 'total_margin']
                    for field in fields_to_check:
                        old_val = getattr(old_entity, field, 'N/A')
                        new_val = getattr(new_entity, field, 'N/A')
                        match = old_val == new_val
                        print(f"   {field}: {match} ('{old_val}' vs '{new_val}')")
        
        # Check hash generation consistency
        print(f"\n🔑 Hash consistency check...")
        if parse_result.deals:
            sample_deal = parse_result.deals[0]
            
            # Generate hash multiple times
            hash1 = sample_deal.hash_key
            hash2 = sample_deal.hash_key
            hash3 = sample_deal.hash_key
            
            print(f"   Sample deal: {sample_deal.deal_key[:50]}...")
            print(f"   Hash 1: {hash1}")
            print(f"   Hash 2: {hash2}")
            print(f"   Hash 3: {hash3}")
            print(f"   Hashes consistent: {hash1 == hash2 == hash3}")
            
            # Check ID consistency
            id1 = sample_deal.id
            id2 = sample_deal.id
            print(f"   ID 1: {id1}")
            print(f"   ID 2: {id2}")
            print(f"   IDs consistent: {id1 == id2}")
        
        print(f"\n📈 Summary:")
        if change_result.update_count > 0 and not any(change.field_changes for change in change_result.updates):
            print("❌ ISSUE FOUND: Updates detected but no field changes!")
            print("   This suggests hash comparison issue or false positives")
        elif change_result.update_count > 0:
            print("ℹ️  Updates detected with field changes - may be legitimate")
        else:
            print("✅ No updates detected - change detection working correctly")
            
    finally:
        await db_manager.cleanup()


async def main():
    """Main function."""
    try:
        await debug_change_detection()
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

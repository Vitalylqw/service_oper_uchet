#!/usr/bin/env python3
"""
Simple script to check deal state before and after sync.
"""

import sys
import os
import asyncio
import subprocess

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from infrastructure.database.connection import DatabaseConfig, DatabaseManager


async def get_deals_snapshot():
    """Get snapshot of all deals."""
    config = DatabaseConfig()
    db_manager = DatabaseManager(config)
    
    async with db_manager.get_async_session() as session:
        from sqlalchemy import text
        
        result = await session.execute(text("""
            SELECT 
                deal_key,
                LEFT(id::text, 8) as id_short,
                LEFT(hash_key, 8) as hash_short,
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
                kickback_amount_value,
                updated_at
            FROM read_deals
            ORDER BY deal_key
            LIMIT 3
        """))
        
        deals = []
        for row in result.fetchall():
            deals.append({
                'deal_key': row[0],
                'id_short': row[1],
                'hash_short': row[2],
                'client_name': row[3],
                'invoice_info': row[4],
                'invoice_number': row[5],
                'invoice_date': row[6],
                'is_shipped': row[7],
                'is_paid': row[8],
                'seller': row[9],
                'upd_number': row[10],
                'revenue': str(row[11]) if row[11] else 'None',
                'margin': str(row[12]) if row[12] else 'None',
                'cost': str(row[13]) if row[13] else 'None',
                'kickback': str(row[14]) if row[14] else 'None',
                'updated_at': str(row[15])
            })
        
        return deals


async def main():
    """Main function."""
    print("📸 Taking BEFORE snapshot...")
    before = await get_deals_snapshot()
    
    print("Sample deals BEFORE sync:")
    for deal in before:
        print(f"  {deal['deal_key'][:40]}... | ID: {deal['id_short']} | Hash: {deal['hash_short']}")
    
    print("\n🔄 Running sync...")
    result = subprocess.run(
        ["python", "testing/scripts/test_sync_integration.py"],
        capture_output=True,
        text=True,
        cwd="/workspaces/service_oper_uchet"
    )
    
    if result.returncode == 0:
        print("✅ Sync completed")
    else:
        print("❌ Sync failed")
        print(result.stderr[:500])
        return
    
    print("\n📸 Taking AFTER snapshot...")
    after = await get_deals_snapshot()
    
    print("Sample deals AFTER sync:")
    for deal in after:
        print(f"  {deal['deal_key'][:40]}... | ID: {deal['id_short']} | Hash: {deal['hash_short']}")
    
    print("\n🔍 Comparing snapshots...")
    
    # Compare by deal_key
    before_dict = {d['deal_key']: d for d in before}
    after_dict = {d['deal_key']: d for d in after}
    
    changes_found = False
    
    for deal_key in before_dict:
        if deal_key in after_dict:
            before_deal = before_dict[deal_key]
            after_deal = after_dict[deal_key]
            
            differences = []
            
            # Check all fields except updated_at
            check_fields = ['id_short', 'hash_short', 'client_name', 'invoice_info', 
                           'invoice_number', 'invoice_date', 'is_shipped', 'is_paid', 
                           'seller', 'upd_number', 'revenue', 'margin', 'cost', 'kickback']
            
            for field in check_fields:
                if before_deal[field] != after_deal[field]:
                    differences.append(f"{field}: {before_deal[field]} → {after_deal[field]}")
            
            if differences:
                changes_found = True
                print(f"\n❌ CHANGES in deal: {deal_key[:50]}...")
                for diff in differences:
                    print(f"   {diff}")
    
    if not changes_found:
        print("\n✅ NO CHANGES detected - all deals are stable!")
    
    # Check updated_at timestamps
    print(f"\n🕐 Timestamp comparison:")
    print(f"   Before sync: {before[0]['updated_at'] if before else 'N/A'}")
    print(f"   After sync:  {after[0]['updated_at'] if after else 'N/A'}")


if __name__ == "__main__":
    asyncio.run(main())

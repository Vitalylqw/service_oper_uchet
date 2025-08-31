#!/usr/bin/env python3
"""
Script to check database state between synchronizations.

This script helps understand what's happening with IDs and hashes.
"""

import sys
import os
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from infrastructure.database.connection import DatabaseConfig, DatabaseManager

async def check_database():
    """Check database state."""
    print("🔍 Checking database state...")
    
    # Setup database using same config as tests
    config = DatabaseConfig()
    db_manager = DatabaseManager(config)
    
    async with db_manager.get_async_session() as session:
        from sqlalchemy import text
        
        # Check read_deals table
        print("\n📊 READ_DEALS table:")
        result = await session.execute(text("SELECT COUNT(*) FROM read_deals"))
        deals_count = result.scalar()
        print(f"   Total deals: {deals_count}")
        
        if deals_count > 0:
            # Show sample deal IDs and keys
            result = await session.execute(text("""
                SELECT deal_key, id, hash_key, client_name 
                FROM read_deals 
                ORDER BY deal_key 
                LIMIT 5
            """))
            deals_sample = result.fetchall()
            
            print("   Sample deals:")
            for deal in deals_sample:
                print(f"     ID: {deal[1]}")
                print(f"     Key: {deal[0]}")
                print(f"     Hash: {deal[2]}")
                print(f"     Client: {deal[3]}")
                print()
        
        # Check read_positions table
        print("📦 READ_POSITIONS table:")
        result = await session.execute(text("SELECT COUNT(*) FROM read_positions"))
        positions_count = result.scalar()
        print(f"   Total positions: {positions_count}")
        
        if positions_count > 0:
            # Show sample position IDs and keys
            result = await session.execute(text("""
                SELECT hash_key, id, deal_id, product_name, position_number
                FROM read_positions 
                ORDER BY hash_key 
                LIMIT 5
            """))
            positions_sample = result.fetchall()
            
            print("   Sample positions:")
            for pos in positions_sample:
                print(f"     ID: {pos[1]}")
                print(f"     Deal ID: {pos[2]}")
                print(f"     Hash: {pos[0]}")
                print(f"     Product: {pos[3]}")
                print(f"     Position #: {pos[4]}")
                print()
        
        # Check for duplicates
        print("🔍 Checking for potential issues:")
        
        # Check for duplicate deal_keys
        result = await session.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT deal_key, COUNT(*) 
                FROM read_deals 
                GROUP BY deal_key 
                HAVING COUNT(*) > 1
            ) duplicates
        """))
        duplicate_deals = result.scalar()
        
        if duplicate_deals > 0:
            print(f"   ❌ Found {duplicate_deals} duplicate deal_keys!")
        else:
            print("   ✅ No duplicate deal_keys")
        
        # Check for duplicate position hash_keys
        result = await session.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT hash_key, COUNT(*) 
                FROM read_positions 
                GROUP BY hash_key 
                HAVING COUNT(*) > 1
            ) duplicates
        """))
        duplicate_positions = result.scalar()
        
        if duplicate_positions > 0:
            print(f"   ❌ Found {duplicate_positions} duplicate position hash_keys!")
        else:
            print("   ✅ No duplicate position hash_keys")
        
        # Check event store
        print("\n📚 EVENT_STORE table:")
        result = await session.execute(text("SELECT COUNT(*) FROM event_store"))
        events_count = result.scalar()
        print(f"   Total events: {events_count}")
        
        if events_count > 0:
            result = await session.execute(text("""
                SELECT event_type, COUNT(*) as count
                FROM event_store 
                GROUP BY event_type 
                ORDER BY count DESC
            """))
            recent_events = result.fetchall()
            
            print("   Event types:")
            for event in recent_events:
                print(f"     {event[0]}: {event[1]}")


async def main():
    """Main function."""
    try:
        await check_database()
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

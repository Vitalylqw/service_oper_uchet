#!/usr/bin/env python3
"""Check data in database."""

import asyncio

from sqlalchemy import text

from infrastructure.database.connection import get_database_session


async def check_data():
    """Check data in database."""
    print("=== CHECKING DATABASE ===")
    
    async for session in get_database_session():
        # Check table structure first
        result_structure = await session.execute(text("PRAGMA table_info(read_deals)"))
        columns = result_structure.fetchall()
        print("read_deals table columns:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # Check read_deals (Event Sourcing read model)
        result = await session.execute(text("SELECT COUNT(*) FROM read_deals"))
        deals_count = result.scalar()
        print(f"\nTotal deals: {deals_count}")
        
        if deals_count > 0:
            # Use first few columns that exist
            result2 = await session.execute(
                text("SELECT id, deal_key, client_name FROM read_deals LIMIT 5")
            )
            deals = result2.fetchall()
            print("\nSample deals:")
            for deal in deals:
                print(f"  ID: {deal[0]}, Key: {deal[1]}, Client: {deal[2]}")
        
        # Check sync sessions
        result3 = await session.execute(text("SELECT COUNT(*) FROM sync_sessions"))
        sessions_count = result3.scalar()
        print(f"\nTotal sync sessions: {sessions_count}")
        
        if sessions_count > 0:
            result4 = await session.execute(
                text("SELECT id, status FROM sync_sessions LIMIT 3")
            )
            sessions = result4.fetchall()
            print("\nSample sessions:")
            for session_data in sessions:
                print(f"  ID: {session_data[0]}, Status: {session_data[1]}")
        
        # Check event store
        result5 = await session.execute(text("SELECT COUNT(*) FROM event_store"))
        events_count = result5.scalar()
        print(f"\nTotal events: {events_count}")
        
        break  # Exit after first session


if __name__ == "__main__":
    asyncio.run(check_data())

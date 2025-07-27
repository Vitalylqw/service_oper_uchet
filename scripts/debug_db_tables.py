#!/usr/bin/env python3
"""Debug database tables creation."""

import asyncio
from sqlalchemy import text
from src.infrastructure.database.connection import get_database_manager
from src.infrastructure.database.models import Base


async def debug_tables():
    """Debug database tables."""
    print("=== DEBUGGING DATABASE TABLES ===")
    
    # Get database manager
    manager = await get_database_manager()
    
    # Check if we can connect
    success = await manager.test_connection()
    if not success:
        print("❌ Cannot connect to database")
        return
    
    print("✅ Database connection OK")
    
    # Try to create tables using SQLAlchemy
    print("Creating tables using SQLAlchemy...")
    engine = manager.sync_engine
    
    try:
        Base.metadata.create_all(engine)
        print("✅ Tables created via SQLAlchemy")
    except Exception as e:
        print(f"❌ SQLAlchemy table creation failed: {e}")
    
    # Check what tables exist
    async with manager.get_async_session() as session:
        try:
            # For SQLite
            result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = result.fetchall()
            print(f"\n📋 Tables in database: {len(tables)}")
            for table in tables:
                print(f"  - {table[0]}")
                
                # Check table structure
                result2 = await session.execute(text(f"PRAGMA table_info({table[0]})"))
                columns = result2.fetchall()
                print(f"    Columns: {len(columns)}")
                for col in columns[:3]:  # Show first 3 columns
                    print(f"      {col[1]} ({col[2]})")
                    
        except Exception as e:
            print(f"❌ Error checking tables: {e}")


if __name__ == "__main__":
    asyncio.run(debug_tables()) 
#!/usr/bin/env python3
"""
Simple database connection test.

Tests SQLite connection without complex imports.
"""

import asyncio
from pathlib import Path

import aiosqlite
from loguru import logger


async def test_sqlite_connection():
    """Test basic SQLite connection and table creation."""

    # Ensure data directory exists
    db_path = Path("data/service_oper_uchet.sqlite")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Testing SQLite connection: {db_path}")

    try:
        # Test async connection
        async with aiosqlite.connect(str(db_path)) as db:
            # Test basic query
            async with db.execute("SELECT 1 as test") as cursor:
                result = await cursor.fetchone()

            if result and result[0] == 1:
                logger.info("✅ SQLite async connection successful")

                # Test table creation
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS test_table (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Test data insertion
                await db.execute("INSERT INTO test_table (name) VALUES (?)", ("test_record",))
                await db.commit()

                # Test data retrieval
                async with db.execute("SELECT * FROM test_table") as cursor:
                    rows = await cursor.fetchall()

                logger.info(f"✅ Test table created and populated with {len(rows)} records")

                # Clean up test table
                await db.execute("DROP TABLE test_table")
                await db.commit()

                logger.info("✅ All SQLite tests passed!")
                return True
            else:
                logger.error("❌ SQLite query test failed")
                return False

    except Exception as e:
        logger.error(f"❌ SQLite connection failed: {e}")
        return False


async def main():
    """Main test function."""
    logger.info("🚀 Starting simple SQLite connection test...")

    # Check if aiosqlite is available
    try:
        import aiosqlite
        logger.info("✅ aiosqlite module found")
    except ImportError:
        logger.error("❌ aiosqlite not installed. Run: pip install aiosqlite")
        return False

    # Test connection
    success = await test_sqlite_connection()

    if success:
        print("\n" + "="*50)
        print("🎉 SQLite CONNECTION TEST PASSED!")
        print("="*50)
        print("✅ SQLite async connection works")
        print("✅ Table creation works")
        print("✅ Data insertion/retrieval works")
        print("✅ Ready for full database integration!")
        print("="*50)
        return True
    else:
        print("\n" + "="*50)
        print("❌ SQLite CONNECTION TEST FAILED!")
        print("="*50)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)

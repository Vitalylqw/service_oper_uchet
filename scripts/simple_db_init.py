#!/usr/bin/env python3
"""
Simple database initialization script.
Creates SQLite database with tables for development.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Direct imports to avoid relative import issues
import aiosqlite
from loguru import logger
from sqlalchemy import create_engine, text


async def init_sqlite_database():
    """Initialize SQLite database with basic structure."""

    # Database path
    db_path = Path("data/service_oper_uchet.sqlite")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Initializing SQLite database: {db_path}")

    try:
        # Create sync engine for table creation
        engine = create_engine(f"sqlite:///{db_path}")

        # Create basic test tables
        with engine.connect() as conn:
            # Test if we can connect
            result = conn.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            logger.info(f"Database connection test: {test_value}")

            # Create a simple test table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS test_connection (
                    id INTEGER PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    test_data TEXT
                )
            """))

            # Insert test data
            conn.execute(text("""
                INSERT INTO test_connection (test_data)
                VALUES ('Database initialization successful')
            """))

            conn.commit()

        logger.info("✅ SQLite database initialized successfully!")

        # Test async connection
        logger.info("Testing async connection...")
        async with aiosqlite.connect(str(db_path)) as db:
            async with db.execute("SELECT test_data FROM test_connection LIMIT 1") as cursor:
                row = await cursor.fetchone()
                if row:
                    logger.info(f"✅ Async test successful: {row[0]}")
                else:
                    logger.warning("⚠️ No test data found")

        return True

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    logger.info("🚀 Starting simple database initialization...")
    success = asyncio.run(init_sqlite_database())

    if success:
        logger.info("🎉 Database initialization completed successfully!")
    else:
        logger.error("💥 Database initialization failed!")
        sys.exit(1)

#!/usr/bin/env python3
"""
Simple connection test for SQLite database.
Tests basic functionality without complex imports.
"""

import asyncio
import os
import sys
from pathlib import Path

import aiosqlite
from loguru import logger


async def test_simple_connection():
    """Test simple SQLite connection."""

    try:
        # Set database environment variables
        os.environ["DB_TYPE"] = "sqlite"
        os.environ["DB_SQLITE_DB_PATH"] = "data/service_oper_uchet.sqlite"

        # Database path
        db_path = Path("data/service_oper_uchet.sqlite")

        if not db_path.exists():
            logger.error(f"❌ Database file not found: {db_path}")
            return False

        logger.info(f"📂 Testing database: {db_path}")

        # Test async connection
        async with aiosqlite.connect(str(db_path)) as db:
            # Test basic query
            async with db.execute("SELECT 1 as test") as cursor:
                row = await cursor.fetchone()
                if row and row[0] == 1:
                    logger.info("✅ Async SQLite connection successful!")
                else:
                    logger.error("❌ Invalid query result")
                    return False

            # Test our test table
            async with db.execute("SELECT test_data FROM test_connection LIMIT 1") as cursor:
                row = await cursor.fetchone()
                if row:
                    logger.info(f"✅ Test data found: {row[0]}")
                else:
                    logger.warning("⚠️ No test data found (this is ok)")

        return True

    except Exception as e:
        logger.error(f"❌ Simple connection test failed: {e}")
        return False


async def test_with_our_config():
    """Test with our DatabaseConfig class."""

    try:
        # Add src to path
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

        # Set only DB_ environment variables
        os.environ.clear()  # Clear to avoid conflicts
        os.environ["DB_TYPE"] = "sqlite"
        os.environ["DB_SQLITE_DB_PATH"] = "data/service_oper_uchet.sqlite"

        logger.info("🔧 Testing with DatabaseConfig...")

        # Import database config
        from infrastructure.database.connection import DatabaseConfig

        config = DatabaseConfig()
        logger.info(f"✅ Config loaded: {config.db_type}, {config.sqlite_db_path}")

        # Test URLs
        logger.info(f"Sync URL: {config.sync_database_url}")
        logger.info(f"Async URL: {config.async_database_url}")

        return True

    except Exception as e:
        logger.error(f"❌ Config test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    """Main test function."""
    logger.info("🚀 Starting simple connection tests...")

    success = True

    # Test 1: Simple SQLite connection
    logger.info("\n" + "="*50)
    logger.info("TEST 1: Simple SQLite Connection")
    logger.info("="*50)

    simple_success = await test_simple_connection()
    if not simple_success:
        success = False

    # Test 2: DatabaseConfig
    logger.info("\n" + "="*50)
    logger.info("TEST 2: DatabaseConfig Test")
    logger.info("="*50)

    config_success = await test_with_our_config()
    if not config_success:
        success = False

    # Summary
    logger.info("\n" + "="*50)
    logger.info("TEST SUMMARY")
    logger.info("="*50)

    if success:
        logger.info("🎉 All connection tests passed!")
    else:
        logger.error("💥 Some tests failed!")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        sys.exit(1)

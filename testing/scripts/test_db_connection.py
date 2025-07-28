#!/usr/bin/env python3
"""
Test database connection and basic functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loguru import logger


async def test_database_connection():
    """Test database connection."""

    try:
        from infrastructure.database.connection import DatabaseConfig, DatabaseManager

        logger.info("🔍 Testing database connection...")

        # Create database config
        config = DatabaseConfig()
        db_manager = DatabaseManager(config)

        # Test connection
        async with db_manager.get_async_session() as session:
            from sqlalchemy import text

            # Test basic query
            result = await session.execute(text("SELECT 1"))
            test_value = result.scalar()

            if test_value == 1:
                logger.info("✅ Database connection successful")
            else:
                logger.error("❌ Database connection failed")
                return False

            # Check table structure
            result = await session.execute(text("PRAGMA table_info(read_deals)"))
            columns = result.fetchall()
            logger.info(f"📊 read_deals table has {len(columns)} columns")

            # Check data counts
            result = await session.execute(text("SELECT COUNT(*) FROM read_deals"))
            deals_count = result.scalar()
            logger.info(f"📊 Total deals: {deals_count}")

            result = await session.execute(text("SELECT COUNT(*) FROM sync_sessions"))
            sessions_count = result.scalar()
            logger.info(f"📊 Total sync sessions: {sessions_count}")

            result = await session.execute(text("SELECT COUNT(*) FROM event_store"))
            events_count = result.scalar()
            logger.info(f"📊 Total events: {events_count}")

            return True

    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def test_health_service():
    """Test health service."""

    try:
        from infrastructure.database.connection import DatabaseConfig, DatabaseManager
        from presentation.api.services.real_health_service import RealHealthService

        logger.info("🔍 Testing health service...")

        config = DatabaseConfig()
        db_manager = DatabaseManager(config)

        health_service = RealHealthService(db_manager)

        # Test health check
        health_status = await health_service.get_service_status()

        logger.info(f"📊 Overall status: {health_status.get('overall_status', 'unknown')}")
        logger.info(f"📊 Database: {health_status.get('components', {}).get('database', {}).get('status', 'unknown')}")
        logger.info(f"📊 Uptime: {health_status.get('uptime', 'unknown')}")

        if health_status.get('overall_status') == "healthy":
            logger.info("✅ Health service working correctly")
            return True
        else:
            logger.error("❌ Health service reports unhealthy status")
            return False

    except Exception as e:
        logger.error(f"❌ Health service test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    """Main test function."""
    logger.info("🚀 Starting database tests...")

    # Test 1: Database connection
    success1 = await test_database_connection()

    # Test 2: Health service
    success2 = await test_health_service()

    if success1 and success2:
        logger.info("🎉 All database tests passed successfully!")
        logger.info("📋 Database Summary:")
        logger.info("  ✅ Database connection working")
        logger.info("  ✅ Health service working")
        logger.info("  ✅ Tables accessible")
    else:
        logger.error("💥 Some database tests failed!")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

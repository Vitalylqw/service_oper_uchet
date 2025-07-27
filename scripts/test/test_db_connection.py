#!/usr/bin/env python3
"""
Test database connection and health checks.
Tests our real infrastructure components with SQLite.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger


async def test_database_connection():
    """Test database connection using our infrastructure."""

    try:
        # Import our database components
        from infrastructure.database.connection import DatabaseConfig, DatabaseManager

        logger.info("🔧 Testing DatabaseConfig...")

        # Test database configuration
        config = DatabaseConfig()
        logger.info(f"Database type: {config.db_type}")
        logger.info(f"Database path: {config.sqlite_db_path}")
        logger.info(f"Async URL: {config.async_database_url}")

        # Test database manager
        logger.info("🔧 Testing DatabaseManager...")
        db_manager = DatabaseManager(config)

        # Test connection
        logger.info("🔌 Testing database connection...")
        connection_ok = await db_manager.test_connection()

        if connection_ok:
            logger.info("✅ Database connection successful!")
        else:
            logger.error("❌ Database connection failed!")
            return False

        # Test session creation
        logger.info("🔧 Testing session creation...")
        session_factory = db_manager.async_session_factory

        async with session_factory() as session:
            # Test a simple query
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            logger.info(f"✅ Session test successful: {test_value}")

        return True

    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def test_health_service():
    """Test RealHealthService functionality."""

    try:
        logger.info("🏥 Testing RealHealthService...")

        # Import health service
        from infrastructure.database.connection import DatabaseConfig, DatabaseManager
        from presentation.api.services.real_health_service import RealHealthService

        # Create database manager
        config = DatabaseConfig()
        db_manager = DatabaseManager(config)

        # Create health service
        health_service = RealHealthService(db_manager)

        # Test database status
        logger.info("🔍 Testing database status check...")
        db_status = await health_service.get_database_status()
        logger.info(f"Database status: {db_status}")

        # Test system metrics
        logger.info("📊 Testing system metrics...")
        metrics = await health_service.get_system_metrics()
        logger.info(f"System metrics: {metrics}")

        # Test service status
        logger.info("🔍 Testing service status...")
        service_status = await health_service.get_service_status()
        logger.info(f"Service status: {service_status}")

        return True

    except Exception as e:
        logger.error(f"❌ Health service test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    """Main test function."""
    logger.info("🚀 Starting database connection and health checks tests...")

    success = True

    # Test 1: Database connection
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Database Connection")
    logger.info("="*60)

    db_success = await test_database_connection()
    if not db_success:
        success = False

    # Test 2: Health service
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Health Service")
    logger.info("="*60)

    health_success = await test_health_service()
    if not health_success:
        success = False

    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)

    if success:
        logger.info("🎉 All tests passed successfully!")
    else:
        logger.error("💥 Some tests failed!")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        sys.exit(1)

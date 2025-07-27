#!/usr/bin/env python3
"""
Database initialization script.

Creates database tables and tests connection for both SQLite and PostgreSQL.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from infrastructure.database.connection import DatabaseConfig, DatabaseManager
from infrastructure.database.models import Base
from loguru import logger


async def create_tables(db_manager: DatabaseManager) -> bool:
    """Create all database tables."""
    try:
        logger.info("Creating database tables...")

        # Create tables using sync engine (required for table creation)
        Base.metadata.create_all(db_manager.sync_engine)

        logger.info("✅ Database tables created successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        return False


async def test_connection(db_manager: DatabaseManager) -> bool:
    """Test database connection and basic operations."""
    try:
        logger.info("Testing database connection...")

        # Test basic connection
        connection_ok = await db_manager.test_connection()
        if not connection_ok:
            return False

        # Test table creation and queries
        async with db_manager.get_async_session() as session:
            # Test a simple query
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1 as test"))
            test_result = result.fetchone()

            if test_result and test_result[0] == 1:
                logger.info("✅ Database query test successful")
                return True
            else:
                logger.error("❌ Database query test failed")
                return False

    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
        return False


async def init_sample_data(db_manager: DatabaseManager) -> bool:
    """Initialize sample data for testing."""
    try:
        logger.info("Creating sample data...")

        # Import domain models
        import uuid

        from domain.models.sync_session import SyncSession, SyncType

        async with db_manager.get_async_session() as session:
            # Create a sample sync session using new field names
            sync_session = SyncSession(
                sync_type=SyncType.FULL,
                source_file_path="test_data.xlsx",
                source_file_hash="test_hash_123",
                source_file_size=1024,
            )
            sync_session.id = uuid.uuid4()

            # Add to session (would normally go through repository layer)
            from infrastructure.database.models import SyncSessionModel

            session_model = SyncSessionModel(
                id=sync_session.id,
                sync_type=sync_session.sync_type.value,
                status="completed",
                file_path=sync_session.source_file_path,
                file_hash=sync_session.source_file_hash,
                file_size=sync_session.source_file_size,
            )

            session.add(session_model)
            await session.commit()

        logger.info("✅ Sample data created successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to create sample data: {e}")
        return False


async def main():
    """Main initialization function."""
    logger.info("🚀 Starting database initialization...")

    # Get database configuration
    db_config = DatabaseConfig()

    logger.info(f"Database type: {db_config.db_type}")
    if db_config.db_type == "sqlite":
        logger.info(f"SQLite database path: {db_config.sqlite_db_path}")
        # Ensure data directory exists
        Path(db_config.sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)
    else:
        logger.info(f"PostgreSQL connection: {db_config.db_host}:{db_config.db_port}/{db_config.db_name}")

    # Initialize database manager
    db_manager = DatabaseManager(db_config)

    try:
        # Step 1: Test connection
        logger.info("Step 1: Testing database connection...")
        if not await test_connection(db_manager):
            logger.error("❌ Database connection failed - aborting initialization")
            return False

        # Step 2: Create tables
        logger.info("Step 2: Creating database tables...")
        if not await create_tables(db_manager):
            logger.error("❌ Table creation failed - aborting initialization")
            return False

        # Step 3: Test tables and queries
        logger.info("Step 3: Testing database tables...")
        if not await test_connection(db_manager):
            logger.error("❌ Table testing failed")
            return False

        # Step 4: Create sample data (optional)
        if os.getenv("CREATE_SAMPLE_DATA", "false").lower() in ("true", "1", "yes"):
            logger.info("Step 4: Creating sample data...")
            await init_sample_data(db_manager)

        logger.info("🎉 Database initialization completed successfully!")

        # Print connection info
        print("\n" + "="*60)
        print("📊 DATABASE INITIALIZATION SUMMARY")
        print("="*60)
        print(f"Database Type: {db_config.db_type.upper()}")
        if db_config.db_type == "sqlite":
            print(f"Database File: {db_config.sqlite_db_path}")
        else:
            print(f"Host: {db_config.db_host}:{db_config.db_port}")
            print(f"Database: {db_config.db_name}")
            print(f"User: {db_config.db_user}")
        print("Status: ✅ READY")
        print("="*60)

        return True

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

    finally:
        await db_manager.close()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

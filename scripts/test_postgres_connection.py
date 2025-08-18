#!/usr/bin/env python3
"""
Test PostgreSQL connection script.

This script tests the connection to PostgreSQL database using the configuration
from config.env file.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from infrastructure.database.connection import DatabaseConfig, DatabaseManager
from loguru import logger


async def test_postgres_connection():
    """Test PostgreSQL connection."""
    try:
        # Load configuration
        config = DatabaseConfig(_env_file="config.env")
        logger.info(f"Database type: {config.db_type}")
        logger.info(f"Host: {config.db_host}:{config.db_port}")
        logger.info(f"Database: {config.db_name}")
        logger.info(f"User: {config.db_user}")
        
        # Test connection
        db_manager = DatabaseManager(config)
        success = await db_manager.test_connection()
        
        if success:
            logger.success("PostgreSQL connection successful!")
            return True
        else:
            logger.error("PostgreSQL connection test failed!")
            return False
            
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        return False


async def test_sqlite_fallback():
    """Test SQLite fallback connection."""
    try:
        # Force SQLite configuration
        config = DatabaseConfig(
            db_type="sqlite",
            sqlite_db_path="data/test_connection.sqlite"
        )
        logger.info(f"Testing SQLite fallback...")
        
        db_manager = DatabaseManager(config)
        success = await db_manager.test_connection()
        
        if success:
            logger.success("SQLite connection successful!")
            return True
        else:
            logger.error("SQLite connection test failed!")
            return False
            
    except Exception as e:
        logger.error(f"SQLite connection failed: {e}")
        return False


async def main():
    """Main function."""
    logger.info("Testing database connections...")
    
    # Test PostgreSQL first
    postgres_ok = await test_postgres_connection()
    
    if not postgres_ok:
        logger.warning("PostgreSQL connection failed, testing SQLite fallback...")
        sqlite_ok = await test_sqlite_fallback()
        
        if sqlite_ok:
            logger.info("Using SQLite as fallback database")
        else:
            logger.error("Both database connections failed!")
            sys.exit(1)
    else:
        logger.success("PostgreSQL connection established successfully!")


if __name__ == "__main__":
    asyncio.run(main())

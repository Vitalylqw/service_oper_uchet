#!/usr/bin/env python3
"""
Database connection check script for Service Oper Uchet.

Tests database connectivity and reports status.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loguru import logger
from infrastructure.database.connection import DatabaseConfig, DatabaseManager
from infrastructure.database.models import Base


async def check_database_connection() -> bool:
    """Check database connection and return status."""
    try:
        logger.info("Checking database connection...")
        
        # Get database configuration
        config = DatabaseConfig()
        logger.info(f"Database type: {config.db_type}")
        logger.info(f"Database URL: {config.sync_database_url}")
        
        # Create database manager
        db_manager = DatabaseManager(config)
        
        # Test connection
        async with db_manager.get_async_session() as session:
            # Simple query to test connection
            result = await session.execute("SELECT 1 as test")
            test_value = result.scalar()
            
            if test_value == 1:
                logger.info("Database connection successful!")
                return True
            else:
                logger.error("Database connection test failed")
                return False
                
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def check_database_schema() -> bool:
    """Check if database schema exists."""
    try:
        logger.info("Checking database schema...")
        
        config = DatabaseConfig()
        db_manager = DatabaseManager(config)
        
        async with db_manager.get_session() as session:
            # Check if tables exist
            tables_query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """
            
            result = await session.execute(tables_query)
            tables = [row[0] for row in result.fetchall()]
            
            expected_tables = [
                'event_store',
                'read_deals', 
                'read_positions',
                'read_audit',
                'read_stats',
                'sync_sessions'
            ]
            
            missing_tables = set(expected_tables) - set(tables)
            
            if missing_tables:
                logger.warning(f"Missing tables: {missing_tables}")
                return False
            else:
                logger.info("All expected tables exist!")
                return True
                
    except Exception as e:
        logger.error(f"Schema check failed: {e}")
        return False


async def check_database_data() -> bool:
    """Check if database has any data."""
    try:
        logger.info("Checking database data...")
        
        config = DatabaseConfig()
        db_manager = DatabaseManager(config)
        
        async with db_manager.get_session() as session:
            # Check record counts
            tables = ['event_store', 'read_deals', 'read_positions', 'sync_sessions']
            
            for table in tables:
                count_query = f"SELECT COUNT(*) FROM {table}"
                result = await session.execute(count_query)
                count = result.scalar()
                logger.info(f"Table {table}: {count} records")
                
            return True
            
    except Exception as e:
        logger.error(f"Data check failed: {e}")
        return False


async def main() -> None:
    """Main function."""
    logger.info("Starting database health check...")
    
    # Check connection
    connection_ok = await check_database_connection()
    if not connection_ok:
        logger.error("Database connection failed!")
        sys.exit(1)
    
    # Check schema
    schema_ok = await check_database_schema()
    if not schema_ok:
        logger.warning("Database schema incomplete!")
    
    # Check data
    data_ok = await check_database_data()
    if not data_ok:
        logger.warning("Database data check failed!")
    
    # Summary
    if connection_ok and schema_ok and data_ok:
        logger.info("Database health check passed!")
        sys.exit(0)
    elif connection_ok:
        logger.warning("Database health check partially passed (connection OK, issues with schema/data)")
        sys.exit(0)
    else:
        logger.error("Database health check failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

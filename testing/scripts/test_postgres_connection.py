#!/usr/bin/env python3
"""
Simple PostgreSQL connection test.

This script tests basic PostgreSQL connectivity without running full synchronization.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loguru import logger


def setup_logging():
    """Setup logging configuration."""
    # Remove default logger
    logger.remove()
    
    # Add custom logger
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )


def setup_postgresql_environment():
    """Setup PostgreSQL environment variables from config.env."""
    config_file = Path(__file__).parent.parent.parent / "config.env"
    
    if config_file.exists():
        logger.info(f"📁 Loading PostgreSQL configuration from: {config_file}")
        
        # Read config.env and set environment variables
        with open(config_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Set both uppercase and lowercase versions for compatibility
                    os.environ[key] = value
                    os.environ[key.lower()] = value
        
        # Ensure PostgreSQL is selected
        os.environ["DB_TYPE"] = "postgresql"
        os.environ["db_type"] = "postgresql"
        
        # Set variables with DB_ prefix for pydantic-settings
        os.environ["DB_DB_TYPE"] = "postgresql"
        os.environ["DB_DB_HOST"] = os.environ.get("DB_HOST", "so_pg")
        os.environ["DB_DB_PORT"] = os.environ.get("DB_PORT", "5432")
        os.environ["DB_DB_NAME"] = os.environ.get("DB_NAME", "so_uchet")
        os.environ["DB_DB_USER"] = os.environ.get("DB_USER", "so_user")
        os.environ["DB_DB_PASSWORD"] = os.environ.get("DB_PASSWORD", "so_pass")
        
        logger.info("✅ PostgreSQL environment configured")
    else:
        logger.warning(f"⚠️ Config file not found: {config_file}")
        logger.info("🔧 Using default PostgreSQL settings")


async def test_postgres_connection():
    """Test basic PostgreSQL connection."""
    try:
        from infrastructure.database.connection import DatabaseConfig, DatabaseManager

        logger.info("🔍 Testing PostgreSQL connection...")

        # Setup database with PostgreSQL configuration
        config = DatabaseConfig()
        logger.info(f"🔧 Database config: type={config.db_type}, host={config.db_host}, port={config.db_port}, db={config.db_name}")
        
        db_manager = DatabaseManager(config)

        # Test connection
        async with db_manager.get_async_session() as session:
            from sqlalchemy import text

            # Test basic query
            result = await session.execute(text("SELECT 1 as test_value"))
            test_value = result.scalar()

            if test_value == 1:
                logger.info("✅ PostgreSQL connection successful")
            else:
                logger.error("❌ PostgreSQL connection failed")
                return False

            # Test PostgreSQL version
            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"📊 PostgreSQL version: {version}")

            # Test database name
            result = await session.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            logger.info(f"📊 Current database: {db_name}")

            # Test user
            result = await session.execute(text("SELECT current_user"))
            user = result.scalar()
            logger.info(f"📊 Current user: {user}")

            # Check if tables exist
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = result.fetchall()
            logger.info(f"📊 Available tables: {[table[0] for table in tables]}")

            return True

    except Exception as e:
        logger.error(f"❌ PostgreSQL connection test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    """Main test function."""
    # Setup logging
    setup_logging()
    
    # Setup PostgreSQL environment
    setup_postgresql_environment()
    
    logger.info("🚀 Starting PostgreSQL connection test...")

    # Test connection
    success = await test_postgres_connection()

    if success:
        logger.info("🎉 PostgreSQL connection test passed successfully!")
        return 0
    else:
        logger.error("💥 PostgreSQL connection test failed!")
        return 1


if __name__ == "__main__":
    import os
    exit_code = asyncio.run(main())
    sys.exit(exit_code)





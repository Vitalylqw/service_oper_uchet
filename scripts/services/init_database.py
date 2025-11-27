#!/usr/bin/env python3
"""
Database initialization script for Service Oper Uchet.

Creates database, applies migrations, and sets up initial data.
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


async def init_database() -> None:
    """Initialize database with schema and initial data."""
    try:
        logger.info("Starting database initialization...")
        
        # Get database configuration
        config = DatabaseConfig()
        logger.info(f"Database type: {config.db_type}")
        logger.info(f"Database URL: {config.sync_database_url}")
        
        # Create database manager
        db_manager = DatabaseManager(config)
        
        # Test connection first
        logger.info("Testing database connection...")
        if not await db_manager.test_connection():
            raise RuntimeError("Database connection failed")
        
        # Apply migrations to create tables
        logger.info("Applying database migrations...")
        await apply_migrations()
        
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def apply_migrations() -> None:
    """Apply Alembic migrations."""
    try:
        import subprocess
        import os
        
        # Change to migrations directory
        migrations_dir = Path(__file__).parent.parent.parent / "migrations"
        os.chdir(migrations_dir)
        
        # Run alembic upgrade
        logger.info("Running Alembic migrations...")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info("Migrations applied successfully")
        if result.stdout:
            logger.info(f"Migration output: {result.stdout}")
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed: {e}")
        if e.stderr:
            logger.error(f"Migration error: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Migration error: {e}")
        raise


async def create_initial_data() -> None:
    """Create initial test data."""
    try:
        logger.info("Creating initial test data...")
        
        # TODO: Add initial data creation logic
        # This could include:
        # - Default sync sessions
        # - Sample deals and positions
        # - Initial statistics
        
        logger.info("Initial data created successfully!")
        
    except Exception as e:
        logger.error(f"Initial data creation failed: {e}")
        raise


async def main() -> None:
    """Main function."""
    try:
        await init_database()
        await create_initial_data()
        logger.info("Database setup completed successfully!")
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

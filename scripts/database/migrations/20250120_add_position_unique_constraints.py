"""
Migration: Add unique constraints for read_positions table
Date: 2025-01-20
Purpose: 
1. Add unique constraint (hash_key, is_active) - prevents duplicates of active positions
2. Add unique constraint (hash_key, version) - ensures version uniqueness
3. Solves issue with position duplication when deal UUIDs regenerate during parsing
"""

import os
import sys
from sqlalchemy import text, create_engine
from sqlalchemy.engine import Engine
from loguru import logger


def _apply_sqlite(engine: Engine) -> None:
    """Apply migration for SQLite database."""
    with engine.begin() as conn:
        logger.info("Applying SQLite migration: add position unique constraints")
        
        # Check if indexes already exist
        existing_indexes = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='index' AND name IN ("
            "'ix_read_positions_hash_active', 'ix_read_positions_hash_version')"
        )).fetchall()
        
        existing_index_names = [idx[0] for idx in existing_indexes]
        
        # 1. Add unique constraint (hash_key, is_active)
        if "ix_read_positions_hash_active" not in existing_index_names:
            conn.execute(text(
                """
                CREATE UNIQUE INDEX ix_read_positions_hash_active 
                ON read_positions (hash_key, is_active)
                WHERE is_active = 1;
                """
            ))
            logger.info("✅ Created unique constraint ix_read_positions_hash_active")
        else:
            logger.info("⚠️ Constraint ix_read_positions_hash_active already exists")
        
        # 2. Add unique constraint (hash_key, version)
        if "ix_read_positions_hash_version" not in existing_index_names:
            conn.execute(text(
                """
                CREATE UNIQUE INDEX ix_read_positions_hash_version 
                ON read_positions (hash_key, version);
                """
            ))
            logger.info("✅ Created unique constraint ix_read_positions_hash_version")
        else:
            logger.info("⚠️ Constraint ix_read_positions_hash_version already exists")


def _apply_postgresql(engine: Engine) -> None:
    """Apply migration for PostgreSQL."""
    with engine.begin() as conn:
        logger.info("Applying PostgreSQL migration: add position unique constraints")
        
        # Check if indexes already exist
        existing_indexes = conn.execute(text(
            """
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'read_positions' 
            AND indexname IN ('ix_read_positions_hash_active', 'ix_read_positions_hash_version')
            """
        )).fetchall()
        
        existing_index_names = [idx[0] for idx in existing_indexes]
        
        # 1. Add unique constraint (hash_key, is_active) - only for active records
        if "ix_read_positions_hash_active" not in existing_index_names:
            conn.execute(text(
                """
                CREATE UNIQUE INDEX ix_read_positions_hash_active 
                ON read_positions (hash_key, is_active)
                WHERE is_active = true;
                """
            ))
            logger.info("✅ Created unique constraint ix_read_positions_hash_active")
        else:
            logger.info("⚠️ Constraint ix_read_positions_hash_active already exists")
        
        # 2. Add unique constraint (hash_key, version)
        if "ix_read_positions_hash_version" not in existing_index_names:
            conn.execute(text(
                """
                CREATE UNIQUE INDEX ix_read_positions_hash_version 
                ON read_positions (hash_key, version);
                """
            ))
            logger.info("✅ Created unique constraint ix_read_positions_hash_version")
        else:
            logger.info("⚠️ Constraint ix_read_positions_hash_version already exists")


def apply_migration(database_url: str) -> None:
    """Apply migration based on database type."""
    engine = create_engine(database_url)
    
    try:
        if "sqlite" in database_url:
            _apply_sqlite(engine)
        elif "postgresql" in database_url:
            _apply_postgresql(engine)
        else:
            raise ValueError(f"Unsupported database type in URL: {database_url}")
            
        logger.info("✅ Migration 20250120_add_position_unique_constraints completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    # Add parent directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    sys.path.insert(0, project_root)

    from src.infrastructure.database.connection import DatabaseConfig
    
    try:
        db_config = DatabaseConfig()
        database_url = db_config.sync_database_url
        logger.info(f"Applying migration to database: {database_url.split('@')[-1] if '@' in database_url else database_url}")
        apply_migration(database_url)
        
    except Exception as e:
        logger.error(f"Failed to apply migration: {e}")
        sys.exit(1)
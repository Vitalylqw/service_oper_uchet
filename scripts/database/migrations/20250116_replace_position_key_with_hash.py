"""Replace position_key unique constraint with hash_key.

Changes unique constraint from (deal_id, position_key) to (deal_id, hash_key)
for better uniqueness detection of deal positions.

This migration:
1. Drops old unique constraint on (deal_id, position_key)  
2. Creates new unique constraint on (deal_id, hash_key)
3. Keeps position_key column for backward compatibility

Usage:
    python scripts/database/migrations/20250116_replace_position_key_with_hash.py
"""
from __future__ import annotations

import os
import sys
from sqlalchemy import text, create_engine
from sqlalchemy.engine import Engine
from loguru import logger


def _apply_postgres(engine: Engine) -> None:
    """Apply migration for PostgreSQL."""
    with engine.begin() as conn:
        logger.info("Applying PostgreSQL migration: replace position_key constraint with hash_key")
        
        # 1. Drop old unique constraint
        try:
            conn.execute(text(
                "DROP INDEX IF EXISTS ix_read_positions_deal_position_key;"
            ))
            logger.info("✅ Dropped old constraint ix_read_positions_deal_position_key")
        except Exception as e:
            logger.warning(f"Failed to drop old constraint (may not exist): {e}")
        
        # 2. Create new unique constraint on (deal_id, hash_key)
        conn.execute(text(
            """
            CREATE UNIQUE INDEX ix_read_positions_deal_hash_key 
            ON read_positions (deal_id, hash_key);
            """
        ))
        logger.info("✅ Created new constraint ix_read_positions_deal_hash_key")


def _apply_sqlite(engine: Engine) -> None:
    """Apply migration for SQLite."""
    with engine.begin() as conn:
        logger.info("Applying SQLite migration: replace position_key constraint with hash_key")
        
        # 1. Drop old unique constraint
        try:
            conn.execute(text(
                "DROP INDEX IF EXISTS ix_read_positions_deal_position_key;"
            ))
            logger.info("✅ Dropped old constraint ix_read_positions_deal_position_key")
        except Exception as e:
            logger.warning(f"Failed to drop old constraint (may not exist): {e}")
        
        # 2. Create new unique constraint on (deal_id, hash_key)
        conn.execute(text(
            """
            CREATE UNIQUE INDEX ix_read_positions_deal_hash_key 
            ON read_positions (deal_id, hash_key);
            """
        ))
        logger.info("✅ Created new constraint ix_read_positions_deal_hash_key")


def apply_migration() -> None:
    """Apply the migration based on database type."""
    database_url = os.getenv("DATABASE_URL", "sqlite:///data/service_oper_uchet.sqlite")
    
    logger.info("🚀 Starting migration: Replace position_key constraint with hash_key")
    logger.info(f"Database URL: {database_url}")
    
    engine = create_engine(database_url)
    
    try:
        # Check if it's PostgreSQL or SQLite
        if database_url.startswith("postgresql"):
            _apply_postgres(engine)
        else:
            _apply_sqlite(engine)
        
        logger.success("✅ Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)


def rollback_migration() -> None:
    """Rollback the migration (restore position_key constraint)."""
    database_url = os.getenv("DATABASE_URL", "sqlite:///data/service_oper_uchet.sqlite")
    
    logger.info("🔄 Rolling back migration: Restore position_key constraint")
    logger.info(f"Database URL: {database_url}")
    
    engine = create_engine(database_url)
    
    try:
        with engine.begin() as conn:
            # 1. Drop new constraint
            try:
                conn.execute(text(
                    "DROP INDEX IF EXISTS ix_read_positions_deal_hash_key;"
                ))
                logger.info("✅ Dropped new constraint ix_read_positions_deal_hash_key")
            except Exception as e:
                logger.warning(f"Failed to drop new constraint: {e}")
            
            # 2. Restore old constraint
            conn.execute(text(
                """
                CREATE UNIQUE INDEX ix_read_positions_deal_position_key 
                ON read_positions (deal_id, position_key);
                """
            ))
            logger.info("✅ Restored old constraint ix_read_positions_deal_position_key")
        
        logger.success("✅ Rollback completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_migration()
    else:
        apply_migration()
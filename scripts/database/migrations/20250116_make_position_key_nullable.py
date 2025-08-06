"""
Migration: Make position_key nullable in read_positions table
Date: 2025-01-16
Purpose: Allow position_key to be NULL since we switched to hash_key for uniqueness
"""

import os
import sys
from sqlalchemy import text, create_engine
from sqlalchemy.engine import Engine
from loguru import logger


def _apply_sqlite(engine: Engine) -> None:
    """Apply migration for SQLite database."""
    with engine.begin() as conn:
        logger.info("Applying SQLite migration: make position_key nullable")
        
        # SQLite doesn't support ALTER COLUMN directly
        # We need to recreate the table without NOT NULL constraint
        
        # Step 0: Clean up any previous failed migrations
        conn.execute(text("DROP TABLE IF EXISTS read_positions_new;"))
        logger.info("✅ Cleaned up previous migration artifacts")
        
        # Step 1: Create new table structure (exact copy of original, but position_key is nullable)
        conn.execute(text("""
            CREATE TABLE read_positions_new (
                id CHAR(36) PRIMARY KEY,
                deal_id CHAR(36) NOT NULL,
                deal_key VARCHAR(255) NOT NULL,
                position_key VARCHAR(500),  -- Now nullable (was NOT NULL)
                hash_key VARCHAR(32) NOT NULL,
                product_name VARCHAR(1000) NOT NULL,
                supplier_name VARCHAR(500),
                pickup_date VARCHAR(50),
                quantity NUMERIC(15, 3),
                purchase_price_amount NUMERIC(15, 2),
                sale_price_amount NUMERIC(15, 2),
                revenue_amount NUMERIC(15, 2),
                margin_amount NUMERIC(15, 2),
                cost_amount NUMERIC(15, 2),
                client_name VARCHAR(500) NOT NULL,
                period_month VARCHAR(20) NOT NULL,
                period_year VARCHAR(4) NOT NULL,
                is_active BOOLEAN NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                version INTEGER NOT NULL
            );
        """))
        logger.info("✅ Created new table read_positions_new")
        
        # Step 2: Copy data from old table
        conn.execute(text("""
            INSERT INTO read_positions_new 
            SELECT * FROM read_positions;
        """))
        logger.info("✅ Copied data to new table")
        
        # Step 3: Drop old table
        conn.execute(text("DROP TABLE read_positions;"))
        logger.info("✅ Dropped old table")
        
        # Step 4: Rename new table
        conn.execute(text("ALTER TABLE read_positions_new RENAME TO read_positions;"))
        logger.info("✅ Renamed new table")
        
        # Step 5: Recreate indexes
        conn.execute(text("""
            CREATE UNIQUE INDEX ix_read_positions_deal_hash_key 
            ON read_positions (deal_id, hash_key);
        """))
        logger.info("✅ Created unique index on (deal_id, hash_key)")
        
        # Optional: Create index on position_key for backward compatibility
        conn.execute(text("""
            CREATE INDEX ix_read_positions_position_key 
            ON read_positions (position_key);
        """))
        logger.info("✅ Created index on position_key")


def _apply_postgresql(engine: Engine) -> None:
    """Apply migration for PostgreSQL database."""
    with engine.begin() as conn:
        logger.info("Applying PostgreSQL migration: make position_key nullable")
        
        # PostgreSQL supports ALTER COLUMN directly
        conn.execute(text("""
            ALTER TABLE read_positions 
            ALTER COLUMN position_key DROP NOT NULL;
        """))
        logger.info("✅ Made position_key nullable")


def apply_migration() -> None:
    """Apply the migration based on database type."""
    logger.info("🚀 Starting migration: Make position_key nullable")
    
    db_url = os.getenv("DATABASE_URL", "sqlite:///data/service_oper_uchet.sqlite")
    logger.info(f"Database URL: {db_url}")
    
    engine = create_engine(db_url)
    
    if engine.url.drivername == "sqlite":
        _apply_sqlite(engine)
    elif engine.url.drivername == "postgresql":
        _apply_postgresql(engine)
    else:
        logger.error(f"Unsupported database type: {engine.url.drivername}")
        sys.exit(1)
    
    logger.success("✅ Migration completed successfully!")


if __name__ == "__main__":
    apply_migration()
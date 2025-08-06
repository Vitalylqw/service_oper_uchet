"""
Migration: Restructure read_positions table
Date: 2025-01-20
Purpose: 
1. Remove position_key column 
2. Add position_number column
3. Update indexes accordingly
"""

import os
import sys
from sqlalchemy import text, create_engine
from sqlalchemy.engine import Engine
from loguru import logger


def _apply_sqlite(engine: Engine) -> None:
    """Apply migration for SQLite database."""
    with engine.begin() as conn:
        logger.info("Applying SQLite migration: restructure read_positions")
        
        # SQLite doesn't support ALTER COLUMN directly
        # We need to recreate the table
        
        # Step 0: Clean up any previous failed migrations
        conn.execute(text("DROP TABLE IF EXISTS read_positions_new;"))
        logger.info("✅ Cleaned up previous migration artifacts")
        
        # Step 1: Create new table structure with position_number and without position_key
        conn.execute(text("""
            CREATE TABLE read_positions_new (
                id CHAR(36) PRIMARY KEY,
                deal_id CHAR(36) NOT NULL,
                deal_key VARCHAR(255) NOT NULL,
                position_number INTEGER NOT NULL,
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
        
        # Step 2: Copy data from old table (set position_number = 1 as default)
        conn.execute(text("""
            INSERT INTO read_positions_new 
            SELECT 
                id, deal_id, deal_key, 
                1 as position_number,  -- Default position number
                hash_key, product_name, supplier_name, pickup_date,
                quantity, purchase_price_amount, sale_price_amount,
                revenue_amount, margin_amount, cost_amount,
                client_name, period_month, period_year,
                is_active, created_at, updated_at, version
            FROM read_positions;
        """))
        logger.info("✅ Copied data to new table")
        
        # Step 3: Drop old table
        conn.execute(text("DROP TABLE read_positions;"))
        logger.info("✅ Dropped old table")
        
        # Step 4: Rename new table
        conn.execute(text("ALTER TABLE read_positions_new RENAME TO read_positions;"))
        logger.info("✅ Renamed new table")
        
        # Step 5: Create indexes
        indexes = [
            "CREATE INDEX ix_read_positions_deal_id ON read_positions (deal_id);",
            "CREATE INDEX ix_read_positions_position_number ON read_positions (position_number);",
            "CREATE INDEX ix_read_positions_product_name ON read_positions (product_name);",
            "CREATE INDEX ix_read_positions_supplier ON read_positions (supplier_name);",
            "CREATE INDEX ix_read_positions_client ON read_positions (client_name);",
            "CREATE INDEX ix_read_positions_period ON read_positions (period_year, period_month);",
            "CREATE INDEX ix_read_positions_hash_key ON read_positions (hash_key);",
            "CREATE INDEX ix_read_positions_deal_product ON read_positions (deal_id, product_name);",
            "CREATE INDEX ix_read_positions_deal_position ON read_positions (deal_id, position_number);",
            "CREATE UNIQUE INDEX ix_read_positions_deal_hash_key ON read_positions (deal_id, hash_key);"
        ]
        
        for index_sql in indexes:
            conn.execute(text(index_sql))
        
        logger.info("✅ Created all indexes")


def _apply_postgresql(engine: Engine) -> None:
    """Apply migration for PostgreSQL database."""
    with engine.begin() as conn:
        logger.info("Applying PostgreSQL migration: restructure read_positions")
        
        # Step 1: Add position_number column
        conn.execute(text("""
            ALTER TABLE read_positions 
            ADD COLUMN position_number INTEGER DEFAULT 1 NOT NULL;
        """))
        logger.info("✅ Added position_number column")
        
        # Step 2: Drop position_key column
        conn.execute(text("""
            ALTER TABLE read_positions 
            DROP COLUMN IF EXISTS position_key;
        """))
        logger.info("✅ Dropped position_key column")
        
        # Step 3: Create new indexes
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_read_positions_position_number 
            ON read_positions (position_number);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_read_positions_deal_position 
            ON read_positions (deal_id, position_number);
        """))
        logger.info("✅ Created new indexes")


def apply_migration() -> None:
    """Apply the migration to the database."""
    # Import here to avoid import issues during migration
    from src.infrastructure.database.connection import get_connection_string
    
    logger.info("🚀 Starting migration: Restructure read_positions table")
    
    try:
        connection_string = get_connection_string()
        engine = create_engine(connection_string, echo=False)
        
        # Determine database type
        if connection_string.startswith("sqlite"):
            _apply_sqlite(engine)
        elif connection_string.startswith("postgresql"):
            _apply_postgresql(engine)
        else:
            raise ValueError(f"Unsupported database type: {connection_string}")
        
        logger.info("✅ Migration completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    # Add the project root to Python path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    apply_migration()
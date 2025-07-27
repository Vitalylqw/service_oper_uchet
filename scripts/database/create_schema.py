#!/usr/bin/env python3
"""
Create database schema for our models.
Uses direct SQLAlchemy approach to avoid import issues.
"""

import asyncio
import os
from pathlib import Path

from loguru import logger
from sqlalchemy import create_engine, text


async def create_database_schema():
    """Create database schema with our models."""

    try:
        # Set environment
        os.environ["DB_TYPE"] = "sqlite"
        os.environ["DB_SQLITE_DB_PATH"] = "data/service_oper_uchet.sqlite"

        # Database path
        db_path = Path("data/service_oper_uchet.sqlite")

        logger.info(f"📂 Creating schema in: {db_path}")

        # Create sync engine
        engine = create_engine(f"sqlite:///{db_path}")

        with engine.connect() as conn:
            # Create Event Store table
            logger.info("🗄️ Creating event_store table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS event_store (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id VARCHAR(36) UNIQUE NOT NULL,
                    aggregate_id VARCHAR(36) NOT NULL,
                    aggregate_type VARCHAR(100) NOT NULL,
                    event_type VARCHAR(200) NOT NULL,
                    event_version INTEGER DEFAULT 1 NOT NULL,
                    event_data TEXT NOT NULL,
                    event_metadata TEXT,
                    sequence_number INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            """))

            # Create indexes for event store
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_event_store_aggregate_id
                ON event_store(aggregate_id)
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_event_store_event_type
                ON event_store(event_type)
            """))

            # Create Read Model: Deals
            logger.info("📊 Creating read_deals table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS read_deals (
                    id VARCHAR(36) PRIMARY KEY,
                    deal_key VARCHAR(255) UNIQUE NOT NULL,
                    hash_key VARCHAR(32) NOT NULL,
                    client_name VARCHAR(500) NOT NULL,
                    invoice_info VARCHAR(500) NOT NULL,
                    invoice_number VARCHAR(100),
                    invoice_date VARCHAR(20),
                    period_month VARCHAR(20) NOT NULL,
                    period_year VARCHAR(4) NOT NULL,
                    period_full_name VARCHAR(100) NOT NULL,
                    is_shipped VARCHAR(20),
                    is_paid VARCHAR(20),
                    upd_number VARCHAR(100),
                    seller VARCHAR(300),
                    total_revenue_amount DECIMAL(15,2),
                    total_revenue_currency VARCHAR(3) DEFAULT 'RUB',
                    total_margin_amount DECIMAL(15,2),
                    total_margin_currency VARCHAR(3) DEFAULT 'RUB',
                    total_cost_amount DECIMAL(15,2),
                    total_cost_currency VARCHAR(3) DEFAULT 'RUB',
                    kickback_amount_value DECIMAL(15,2),
                    kickback_amount_currency VARCHAR(3) DEFAULT 'RUB',
                    items_count INTEGER DEFAULT 0,
                    total_quantity DECIMAL(15,3),
                    is_active BOOLEAN DEFAULT 1 NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version INTEGER DEFAULT 1 NOT NULL
                )
            """))

            # Create Sync Sessions table
            logger.info("🔄 Creating sync_sessions table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sync_sessions (
                    id VARCHAR(36) PRIMARY KEY,
                    sync_type VARCHAR(20) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    file_path VARCHAR(1000) NOT NULL,
                    file_hash VARCHAR(32) NOT NULL,
                    file_size INTEGER NOT NULL,
                    started_at TIMESTAMP,
                    finished_at TIMESTAMP,
                    stats_data TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            conn.commit()

        logger.info("✅ Database schema created successfully!")

        # Test the tables
        with engine.connect() as conn:
            # Check tables exist
            result = conn.execute(text("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name IN ('event_store', 'read_deals', 'sync_sessions')
            """))
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"📋 Created tables: {tables}")

        return True

    except Exception as e:
        logger.error(f"❌ Schema creation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    logger.info("🚀 Creating database schema...")
    success = asyncio.run(create_database_schema())

    if success:
        logger.info("🎉 Schema creation completed successfully!")
    else:
        logger.error("💥 Schema creation failed!")
        exit(1)

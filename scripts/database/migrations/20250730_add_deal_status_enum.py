"""Add enum-like constraint for is_paid and is_shipped columns.

Usage:
    http://localhost:3000/dealsrations/20250730_add_deal_status_enum.py

The script reads DATABASE_URL env var (default sqlite:///local.db). It autodetects
PostgreSQL or SQLite and applies correct DDL.
"""
from __future__ import annotations

import os
import sys
from sqlalchemy import text, create_engine
from sqlalchemy.engine import Engine
from loguru import logger

POSTGRES_VALUES = "'pending','partial','paid','shipped','completed'"
SQLITE_VALUES = ("pending","partial","paid","shipped","completed")

def _apply_postgres(engine: Engine) -> None:
    with engine.begin() as conn:
        # 1. Create enum type if not exists
        conn.execute(text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'deal_status') THEN
                    CREATE TYPE deal_status AS ENUM ({values});
                END IF;
            END$$;
            """.format(values=POSTGRES_VALUES)
        ))

        # 2. Ensure all existing values are within enum set (strip leading 'Status.' etc.)
        conn.execute(text(
            """
            UPDATE read_deals
               SET is_paid    = lower(regexp_replace(is_paid, '^status\\.', '')),
                   is_shipped = lower(regexp_replace(is_shipped, '^status\\.', ''));
            """
        ))

        # 3. Alter column type using enum
        for col in ("is_paid", "is_shipped"):
            logger.info(f"Altering column {col} to deal_status enum")
            conn.execute(text(
                f"""
                ALTER TABLE read_deals
                  ALTER COLUMN {col} TYPE deal_status USING {col}::deal_status;
                """
            ))

        # 4. Add NOT NULL default 'pending' (optional)
        conn.execute(text(
            """
            ALTER TABLE read_deals ALTER COLUMN is_paid SET DEFAULT 'pending';
            ALTER TABLE read_deals ALTER COLUMN is_shipped SET DEFAULT 'pending';
            """
        ))

    logger.success("PostgreSQL DDL applied successfully")


def _apply_sqlite(engine: Engine) -> None:
    # SQLite lacks ALTER CHECK easily; recreate table in place.
    # We'll add CHECK constraint on new columns.
    with engine.begin() as conn:
        # Disable FK
        conn.execute(text("PRAGMA foreign_keys=off"))
        # 1. Rename table
        conn.execute(text("ALTER TABLE read_deals RENAME TO read_deals_old"))
        # 2. Recreate table with constraint (only showing affected columns)
        #    We copy the original CREATE statement but add CHECK constraints.
        conn.execute(text(
            f"""
            CREATE TABLE read_deals (
                -- NOTE: only subset relevant fields shown here; we keep rest via *
                id TEXT PRIMARY KEY,
                deal_key TEXT NOT NULL,
                hash_key TEXT NOT NULL,
                client_name TEXT NOT NULL,
                invoice_info TEXT NOT NULL,
                invoice_number TEXT,
                invoice_date TEXT,
                period_month TEXT NOT NULL,
                period_year TEXT NOT NULL,
                period_full_name TEXT NOT NULL,
                is_shipped TEXT CHECK(is_shipped IN {SQLITE_VALUES}),
                is_paid TEXT CHECK(is_paid IN {SQLITE_VALUES}),
                -- keep remaining columns identical using *
                total_revenue_amount NUMERIC,
                total_revenue_currency TEXT,
                total_margin_amount NUMERIC,
                total_margin_currency TEXT,
                total_cost_amount NUMERIC,
                total_cost_currency TEXT,
                kickback_amount_value NUMERIC,
                kickback_amount_currency TEXT,
                items_count INTEGER,
                total_quantity NUMERIC,
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT,
                updated_at TEXT,
                version INTEGER DEFAULT 1
            );
            """
        ))
        # 3. Copy data
        conn.execute(text("""
            INSERT INTO read_deals SELECT * FROM read_deals_old;
        """))
        # 4. Drop old table
        conn.execute(text("DROP TABLE read_deals_old"))
        conn.execute(text("PRAGMA foreign_keys=on"))
    logger.success("SQLite DDL applied successfully")


def main() -> None:
    db_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv("DATABASE_URL", "sqlite:///local.db")
    engine = create_engine(db_url)
    dialect = engine.url.get_dialect().name
    logger.info(f"Connecting to {db_url} (dialect={dialect})")

    if dialect == "postgresql":
        _apply_postgres(engine)
    elif dialect == "sqlite":
        _apply_sqlite(engine)
    else:
        logger.error("Unsupported dialect for this migration")
        sys.exit(1)

    logger.success("Migration completed")

if __name__ == "__main__":
    main()

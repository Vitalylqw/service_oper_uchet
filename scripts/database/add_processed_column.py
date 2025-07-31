#!/usr/bin/env python
"""Add processed_at column to event_store if it is missing.

Run once when migrating to the new event-processing model.
This script is idempotent: if the column already exists, it will
print a friendly message and exit with code 0.
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys
from typing import Final

DB_PATH: Final = pathlib.Path("data") / "service_oper_uchet.sqlite"


def main() -> None:
    if not DB_PATH.exists():
        sys.exit(f"❌ DB file not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute("ALTER TABLE event_store ADD COLUMN processed_at TIMESTAMP")
        print("✅ Column processed_at added")
    except sqlite3.OperationalError as exc:
        msg = str(exc).lower()
        if "duplicate" in msg or "exists" in msg:
            print("ℹ️  Column processed_at already exists – skipping")
        else:
            raise
    finally:
        conn.commit()
        conn.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Reset any sync sessions stuck in 'running' status.

Marks them as 'failed' and sets finished_at to now.
Idempotent.
"""
from __future__ import annotations

import pathlib
import sqlite3
from datetime import datetime

DB_PATH = pathlib.Path("data") / "service_oper_uchet.sqlite"

if not DB_PATH.exists():
    raise SystemExit(f"DB not found: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
now_iso = datetime.utcnow().isoformat(sep=" ", timespec="seconds")
cur.execute(
    "UPDATE sync_sessions SET status='failed', finished_at=? WHERE status='running'",
    (now_iso,),
)
modified = cur.rowcount if cur.rowcount != -1 else 0
conn.commit()
conn.close()
print(f"Reset {modified} running session(s) to failed at {now_iso}")

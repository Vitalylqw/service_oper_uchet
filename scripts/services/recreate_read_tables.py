#!/usr/bin/env python3
"""
Service script: Drop and recreate read tables using Alembic migration 0003.

Usage:
  python scripts/services/recreate_read_tables.py

This script runs Alembic upgrade to head, ensuring read tables are recreated
according to the latest migration (0003).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    alembic_ini = repo_root / "migrations" / "alembic.ini"
    if not alembic_ini.exists():
        print("alembic.ini not found; ensure migrations are initialized")
        return 1

    try:
        # Run alembic upgrade to latest
        cmd = [sys.executable, "-m", "alembic", "-c", str(alembic_ini), "upgrade", "head"]
        print("Running:", " ".join(cmd))
        subprocess.check_call(cmd, cwd=str(repo_root))
        print("Alembic upgrade completed.")
        return 0
    except subprocess.CalledProcessError as e:
        print("Alembic upgrade failed:", e)
        return e.returncode


if __name__ == "__main__":
    raise SystemExit(main())



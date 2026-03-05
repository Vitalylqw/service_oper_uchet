"""
Create a database snapshot -- captures current state of read_deals and read_positions.

Usage:
    python dashboard/create_db_snapshot.py --label "before_sync"
    python dashboard/create_db_snapshot.py --label "after_sync"
    python dashboard/create_db_snapshot.py  # auto-generated label
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "dashboard"))

from sqlalchemy import create_engine
from infrastructure.database.connection import DatabaseConfig
from db_snapshot_service import collect_snapshot, save_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def get_sync_engine():
    """Create sync engine from project config."""
    config = DatabaseConfig()
    return create_engine(config.sync_database_url, echo=False, future=True)


def main() -> int:
    """Entry point: collect and save snapshot."""
    parser = argparse.ArgumentParser(description="Create DB state snapshot")
    parser.add_argument(
        "--label", type=str, default=None,
        help="Snapshot label (e.g. 'before_sync'). Auto-generated if omitted.",
    )
    parser.add_argument(
        "--source", type=str, default="manual",
        help="Snapshot source identifier (default: manual)",
    )
    args = parser.parse_args()

    label = args.label or f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    source = args.source

    logger.info("Creating snapshot: label=%s, source=%s", label, source)

    engine = get_sync_engine()
    try:
        with engine.connect() as conn:
            snap = collect_snapshot(conn, label=label, source=source)
            snapshot_id = save_snapshot(conn, snap)
    except Exception:
        logger.exception("Failed to create snapshot")
        return 1
    finally:
        engine.dispose()

    # Print summary
    print("\n" + "=" * 60)
    print(f"  SNAPSHOT CREATED: id={snapshot_id}, label={label}")
    print("=" * 60)
    print(f"  read_deals:     {snap.deals_total_rows} rows")
    print(f"  read_positions: {snap.pos_total_rows} rows")
    print(f"  Deal periods:   {len(snap.deal_periods)}")
    print(f"  Pos. periods:   {len(snap.position_periods)}")
    health_fails = sum(
        1 for v in snap.health_checks.values()
        if isinstance(v, dict) and v.get("status") in ("FAIL", "WARN")
    )
    if health_fails:
        print(f"  Health issues:  {health_fails} check(s) with WARN/FAIL")
    else:
        print("  Health:         ALL OK")
    print("=" * 60 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

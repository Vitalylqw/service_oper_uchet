"""
Pipeline: sync -> snapshot -> compare dashboard.

Runs sequentially:
1. scripts/test/test_sync_integration.py  (full sync)
2. dashboard/create_db_snapshot.py        (auto-label)
3. dashboard/generate_dashboard.py        (compare last two snapshots)

Usage:
    python dashboard/run_sync_snapshot_dashboard.py
    python dashboard/run_sync_snapshot_dashboard.py --sync-type full
    python dashboard/run_sync_snapshot_dashboard.py --snapshot-label "my_label"
    python dashboard/run_sync_snapshot_dashboard.py --skip-sync
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_step(step_name: str, cmd: list[str]) -> bool:
    """Run a subprocess step and return True on success."""
    logger.info("=" * 60)
    logger.info("STEP: %s", step_name)
    logger.info("CMD:  %s", " ".join(cmd))
    logger.info("=" * 60)

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

    if result.returncode != 0:
        logger.error("FAILED: %s (exit code %d)", step_name, result.returncode)
        return False

    logger.info("OK: %s", step_name)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pipeline: sync -> snapshot -> compare dashboard",
    )
    parser.add_argument(
        "--sync-type", type=str, default="full",
        choices=["full", "incremental"],
        help="Sync type for test_sync_integration (default: full)",
    )
    parser.add_argument(
        "--snapshot-label", type=str, default=None,
        help="Snapshot label. Auto-generated if omitted.",
    )
    parser.add_argument(
        "--skip-sync", action="store_true",
        help="Skip sync step (only snapshot + dashboard)",
    )
    args = parser.parse_args()

    python = sys.executable
    # Step 1: Sync
    if not args.skip_sync:
        sync_cmd = [
            python,
            str(PROJECT_ROOT / "scripts" / "test" / "test_sync_integration.py"),
            "--sync-type", args.sync_type,
        ]
        if not run_step("Synchronization", sync_cmd):
            logger.error("Sync failed -- aborting pipeline.")
            return 1

    # Step 2: Snapshot
    snapshot_cmd = [
        python,
        str(PROJECT_ROOT / "dashboard" / "create_db_snapshot.py"),
    ]
    if args.snapshot_label:
        snapshot_cmd.extend(["--label", args.snapshot_label])

    if not run_step("Create DB Snapshot", snapshot_cmd):
        logger.error("Snapshot creation failed -- aborting pipeline.")
        return 1

    # Step 3: Compare dashboard
    dashboard_cmd = [
        python,
        str(PROJECT_ROOT / "dashboard" / "generate_dashboard.py"),
        "--mode", "compare",
    ]
    if not run_step("Generate Compare Dashboard", dashboard_cmd):
        logger.error("Dashboard generation failed.")
        return 1

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

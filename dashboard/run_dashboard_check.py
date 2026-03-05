"""
One-command dashboard workflow: snapshot + HTML generation.

Usage:
    # Single snapshot + dashboard
    python dashboard/run_dashboard_check.py --label "test_v1"

    # Before/after workflow
    python dashboard/run_dashboard_check.py --before "sync_test"
    # ... run your test ...
    python dashboard/run_dashboard_check.py --after "sync_test"
    # ^ auto-finds 'before_sync_test', creates 'after_sync_test', generates compare dashboard
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "dashboard"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_script(script_name: str, args: list[str]) -> int:
    """Run a sibling Python script, return exit code."""
    cmd = [sys.executable, str(SCRIPTS_DIR / script_name)] + args
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Dashboard check workflow")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--label", type=str, default=None,
        help="Create snapshot with this label and generate latest dashboard.",
    )
    group.add_argument(
        "--before", type=str, default=None,
        help="Create 'before_<name>' snapshot.",
    )
    group.add_argument(
        "--after", type=str, default=None,
        help="Create 'after_<name>' snapshot and generate compare dashboard.",
    )
    args = parser.parse_args()

    if args.label:
        rc = run_script("create_db_snapshot.py", ["--label", args.label])
        if rc != 0:
            return rc
        return run_script("generate_dashboard.py", ["--mode", "latest"])

    if args.before:
        label = f"before_{args.before}"
        return run_script("create_db_snapshot.py", ["--label", label])

    if args.after:
        label_before = f"before_{args.after}"
        label_after = f"after_{args.after}"
        rc = run_script("create_db_snapshot.py", ["--label", label_after])
        if rc != 0:
            return rc
        return run_script(
            "generate_dashboard.py",
            ["--mode", "compare", "--label1", label_before, "--label2", label_after],
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Trigger LibreOffice headless conversion to refresh Excel formula cache."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from application.excel_parser.precalc import refresh_excel_cache_if_enabled  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recalculate Excel formulas via LibreOffice headless conversion",
    )
    parser.add_argument("excel_path", help="Absolute or relative path to the source .xlsx file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    excel_path = Path(args.excel_path).resolve()

    if not excel_path.exists():
        print(f"Input file not found: {excel_path}", file=sys.stderr)
        return 2

    refreshed = refresh_excel_cache_if_enabled(excel_path)
    print(str(refreshed))
    return 0


if __name__ == "__main__":
    sys.exit(main())



#!/usr/bin/env python3
"""
Export unique product names from read_positions to a CSV file.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from loguru import logger

try:
    from infrastructure.config.env_loader import load_runtime_env
    from infrastructure.database.connection import DatabaseConfig
except ImportError:  # pragma: no cover - fallback for repo-local imports
    from src.infrastructure.config.env_loader import load_runtime_env
    from src.infrastructure.database.connection import DatabaseConfig

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "exports" / "read_positions_product_names.csv"
)


def setup_logging() -> None:
    """Configure console logging for the script."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
        colorize=False,
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Export unique product_name values from read_positions to CSV."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the CSV file to create.",
    )
    return parser.parse_args()


def export_unique_product_names(output_path: Path) -> int:
    """Export normalized unique product names and return the number of rows written."""
    load_runtime_env()
    config = DatabaseConfig()
    count_query = (
        "SELECT COUNT(*) "
        "FROM ("
        "SELECT DISTINCT TRIM(product_name) AS product_name "
        "FROM read_positions "
        "WHERE product_name IS NOT NULL "
        "  AND TRIM(product_name) <> ''"
        ") AS unique_names"
    )
    query = (
        "COPY ("
        "SELECT DISTINCT TRIM(product_name) AS product_name "
        "FROM read_positions "
        "WHERE product_name IS NOT NULL "
        "  AND TRIM(product_name) <> '' "
        "ORDER BY product_name"
        ") TO STDOUT WITH CSV HEADER"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    count_result = subprocess.run(
        ["psql", "-X", "-q", "-t", "-A", "-c", count_query, config.sync_database_url],
        check=True,
        capture_output=True,
        text=True,
    )
    row_count = int(count_result.stdout.strip())

    with output_path.open("w", encoding="utf-8", newline="") as file_obj:
        subprocess.run(
            ["psql", "-X", "-q", "-c", query, config.sync_database_url],
            check=True,
            stdout=file_obj,
            stderr=subprocess.PIPE,
            text=True,
        )

    return row_count


def main() -> int:
    """Script entrypoint."""
    args = parse_args()
    setup_logging()

    try:
        row_count = export_unique_product_names(args.output)
    except Exception as exc:
        logger.exception("Failed to export product names")
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    logger.info("Exported {} unique product names to {}", row_count, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

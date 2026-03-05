"""Excel Health Dashboard — CLI entry point.

Orchestrates Excel parsing, health checks, DB comparison, and HTML report
generation. Report is saved to dashboard/reports/.

Usage:
    python dashboard/excel_health_dashboard.py
    python dashboard/excel_health_dashboard.py --periods "Январь 2025" "Февраль 2025"
    python dashboard/excel_health_dashboard.py --excel-path path/to/file.xlsx
"""

from __future__ import annotations

import argparse
import logging
import sys
import webbrowser
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# ---------------------------------------------------------------------------
# sys.path bootstrap — must happen before any project imports
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(_PROJECT_ROOT / "dashboard"))

# ---------------------------------------------------------------------------
# Project imports (after path bootstrap)
# ---------------------------------------------------------------------------
from excel_audit.comparator import compare_period  # noqa: E402
from excel_audit.config import AuditConfig  # noqa: E402
from excel_audit.db_reader import get_db_period_data  # noqa: E402
from excel_audit.excel_reader import (  # noqa: E402
    filter_periods,
    get_available_periods,
    parse_all_periods,
)
from excel_audit.health_checker import run_health_check  # noqa: E402
from excel_audit.html_generator import render_full_report  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

from infrastructure.database.connection import DatabaseConfig  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_DEFAULT_EXCEL = str(
    _PROJECT_ROOT / "data" / "real_data_for_testing" / "Data_source_excel.xlsx"
)
_DEFAULT_OUTPUT = str(_PROJECT_ROOT / "dashboard" / "reports")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Excel Health Dashboard — health check and Excel vs DB comparison",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--excel-path",
        default=_DEFAULT_EXCEL,
        help=f"Path to Excel file (default: {_DEFAULT_EXCEL})",
    )
    parser.add_argument(
        "--periods",
        nargs="+",
        default=None,
        metavar="PERIOD",
        help='Period names to analyse, e.g. "Январь 2025". Default: all sheets.',
    )
    parser.add_argument(
        "--output-dir",
        default=_DEFAULT_OUTPUT,
        help=f"Directory for HTML report (default: {_DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        metavar="RUBLES",
        help=(
            "Minimum absolute delta (rubles) to treat as a discrepancy. "
            f"Default: {AuditConfig().threshold} (from AuditConfig)."
        ),
    )
    parser.add_argument(
        "--show-warnings",
        action="store_true",
        default=False,
        help="Show WARN-level totals issues in the report (hidden by default).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the report in a browser after generation.",
    )
    return parser


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def _parse_period_name(period_name: str) -> tuple[str, str]:
    """Split 'Январь 2025' → ('Январь', '2025').

    Args:
        period_name: Space-separated month and year string.

    Returns:
        tuple[str, str]: (period_month, period_year).

    Raises:
        ValueError: If the period_name does not contain exactly one space.
    """
    parts = period_name.strip().rsplit(" ", 1)
    if len(parts) != 2:
        raise ValueError(
            f"Cannot split period_name '{period_name}' into month and year. "
            "Expected format: 'Январь 2025'."
        )
    return parts[0], parts[1]


def main() -> int:
    """Entry point: run the full audit pipeline and generate the HTML report."""
    parser = build_arg_parser()
    args = parser.parse_args()

    # ---- Build config ----
    config = AuditConfig(show_warnings=args.show_warnings)
    if args.threshold is not None:
        config = AuditConfig(
            threshold=Decimal(str(args.threshold)),
            show_warnings=args.show_warnings,
        )
    threshold = config.threshold
    show_warnings = config.show_warnings
    logger.info("Audit threshold: %s RUB, show_warnings: %s", threshold, show_warnings)

    excel_path = args.excel_path
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---- Verify Excel file exists ----
    if not Path(excel_path).exists():
        logger.error("Excel file not found: %s", excel_path)
        return 1

    # ---- Step 1: Parse Excel ----
    logger.info("=== Step 1: Parsing Excel file ===")
    available = get_available_periods(excel_path)
    logger.info("Sheets in file: %s", available)

    all_periods = parse_all_periods(excel_path)

    periods_map = filter_periods(all_periods, args.periods)
    if not periods_map:
        logger.error("No matching periods found. Available: %s", list(all_periods.keys()))
        return 1

    logger.info("Periods to analyse: %s", list(periods_map.keys()))

    # ---- Step 2: Health check ----
    logger.info("=== Step 2: Running health checks ===")
    health_reports = [
        run_health_check(deals, period_name, threshold)
        for period_name, deals in periods_map.items()
    ]

    # ---- Step 3 & 4: DB queries + comparison ----
    logger.info("=== Step 3: Querying database and comparing ===")
    db_config = DatabaseConfig()
    engine = create_engine(db_config.sync_database_url, echo=False, future=True)

    comparisons = []
    try:
        with engine.connect() as conn:
            for period_name, deals in periods_map.items():
                try:
                    month, year = _parse_period_name(period_name)
                    db_data = get_db_period_data(conn, month, year, period_name)
                    cmp = compare_period(deals, db_data, period_name, threshold)
                    comparisons.append(cmp)
                except Exception:
                    logger.exception(
                        "Failed to compare period '%s'; skipping DB comparison for it.",
                        period_name,
                    )
    except Exception:
        logger.exception(
            "Could not connect to database. "
            "Report will be generated without comparison section."
        )
    finally:
        engine.dispose()

    # ---- Step 5: Generate HTML ----
    logger.info("=== Step 5: Generating HTML report ===")
    html_content = render_full_report(
        excel_path=excel_path,
        health_reports=health_reports,
        comparisons=comparisons,
        generated_at=datetime.now(),
        threshold=threshold,
        show_warnings=show_warnings,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"excel_health_{timestamp}.html"
    output_file.write_text(html_content, encoding="utf-8")
    logger.info("Report saved: %s", output_file)

    # ---- Summary ----
    total_dups = sum(len(h.duplicates) for h in health_reports)
    total_fails = sum(h.fail_count for h in health_reports)
    total_warns = sum(h.warn_count for h in health_reports)
    total_only_excel = sum(len(c.only_in_excel) for c in comparisons)
    total_only_db = sum(len(c.only_in_db) for c in comparisons)
    total_diffs = sum(len(c.diffs) for c in comparisons)

    print("\n" + "=" * 60)
    print("  EXCEL AUDIT REPORT")
    print("=" * 60)
    print(f"  File:            {excel_path}")
    print(f"  Periods:         {len(health_reports)}")
    print(f"  Report:          {output_file}")
    print("-" * 60)
    print(f"  Duplicate keys:  {total_dups}")
    print(f"  Totals FAIL:     {total_fails}")
    print(f"  Totals WARN:     {total_warns}")
    print("-" * 60)
    print(f"  Only in Excel:   {total_only_excel}")
    print(f"  Only in DB:      {total_only_db}")
    print(f"  Deal diffs:      {total_diffs}")
    print("=" * 60 + "\n")

    if not args.no_browser:
        webbrowser.open(output_file.as_uri())

    return 0


if __name__ == "__main__":
    sys.exit(main())

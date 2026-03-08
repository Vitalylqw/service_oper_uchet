#!/usr/bin/env python3
"""
Test Excel parsing with real project data.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


async def test_excel_parsing() -> bool:
    """Parse the real Excel file and log a short summary."""
    try:
        from application.excel_parser import ExcelParserService
        from domain.models import SyncSession, SyncType

        logger.info("Testing Excel parsing with real data")

        parser = ExcelParserService()
        session = SyncSession(sync_type=SyncType.INCREMENTAL)
        excel_file = PROJECT_ROOT / "data" / "real_data_for_testing" / "Data_source_excel.xlsx"

        if not excel_file.exists():
            logger.error("Excel file not found: {}", excel_file)
            return False

        logger.info("Parsing file: {}", excel_file)
        result = await parser.parse_file(str(excel_file), session)

        logger.info("Parsing completed successfully")
        logger.info("Total deals: {}", result.total_deals)
        logger.info("Total items: {}", result.total_items)
        logger.info("Errors: {}", len(result.stats.errors))

        if result.stats.errors:
            logger.warning("Parsing errors found:")
            for error in result.stats.errors[:5]:
                logger.warning("  - {}", error)

        if result.deals:
            logger.info("Sample deals:")
            for index, deal in enumerate(result.deals[:3], start=1):
                logger.info("  {}. {} - {}", index, deal.client_name, deal.invoice_number)
                logger.info("     Revenue: {}", deal.total_revenue)
                logger.info("     Items: {}", len(deal.items))

        return True

    except Exception as exc:
        logger.exception("Excel parsing test failed: {}", exc)
        return False


async def test_change_detection() -> bool:
    """Parse the real file and run change detection against the current database."""
    try:
        from application.change_detector import ChangeDetectorService
        from application.excel_parser import ExcelParserService
        from domain.models import SyncSession, SyncType
        from infrastructure.database.connection import DatabaseConfig, DatabaseManager
        from infrastructure.database.repositories import DealRepositoryImplementation

        logger.info("Testing change detection")

        config = DatabaseConfig()
        db_manager = DatabaseManager(config)

        async with db_manager.get_async_session() as session:
            deal_repo = DealRepositoryImplementation(session)
            detector = ChangeDetectorService(deal_repo)
            parser = ExcelParserService()
            sync_session = SyncSession(sync_type=SyncType.INCREMENTAL)
            excel_file = PROJECT_ROOT / "data" / "real_data_for_testing" / "Data_source_excel.xlsx"

            parse_result = await parser.parse_file(str(excel_file), sync_session)
            changes = await detector.detect_changes(parse_result.deals, sync_period_months=12)

            logger.info("Change detection completed")
            logger.info("Insertions: {}", changes.insertion_count)
            logger.info("Updates: {}", changes.update_count)
            logger.info("Deletions: {}", changes.deletion_count)
            return True

    except Exception as exc:
        logger.exception("Change detection test failed: {}", exc)
        return False


async def main() -> int:
    """Script entrypoint."""
    logger.info("Starting Excel parsing checks")

    parsing_ok = await test_excel_parsing()
    detection_ok = await test_change_detection()

    if parsing_ok and detection_ok:
        logger.info("All Excel parsing checks passed")
        return 0

    logger.error("Some Excel parsing checks failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

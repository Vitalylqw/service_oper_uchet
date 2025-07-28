#!/usr/bin/env python3
"""
Test Excel parsing with real data.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loguru import logger


async def test_excel_parsing():
    """Test Excel parsing with real data."""

    try:
        from application.excel_parser import ExcelParserService
        from domain.models import SyncSession, SyncType

        logger.info("🔍 Testing Excel parsing with real data...")

        # Create parser service
        parser = ExcelParserService()

        # Create dummy sync session
        session = SyncSession(sync_type=SyncType.INCREMENTAL)

        # Path to real Excel file
        excel_file = Path("data/real_data_for_testing/Data_source_excel.xlsx")

        if not excel_file.exists():
            logger.error(f"❌ Excel file not found: {excel_file}")
            return False

        logger.info(f"📁 Parsing file: {excel_file}")

        # Parse Excel file
        result = await parser.parse_file(str(excel_file), session)

        logger.info("✅ Parsing completed successfully!")
        logger.info(f"📊 Total deals: {result.total_deals}")
        logger.info(f"📊 Total items: {result.total_items}")
        logger.info(f"📊 Errors: {len(result.stats.errors)}")

        if result.stats.errors:
            logger.warning("⚠️ Parsing errors found:")
            for error in result.stats.errors[:5]:  # Show first 5 errors
                logger.warning(f"  - {error}")

        # Show sample deals
        if result.deals:
            logger.info("📋 Sample deals:")
            for i, deal in enumerate(result.deals[:3]):
                logger.info(f"  {i+1}. {deal.client_name} - {deal.invoice_number}")
                logger.info(f"     Revenue: {deal.total_revenue}")
                logger.info(f"     Items: {len(deal.items)}")

        return True

    except Exception as e:
        logger.error(f"❌ Excel parsing test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def test_change_detection():
    """Test change detection with parsed data."""

    try:
        from application.change_detector import ChangeDetectorService
        from application.excel_parser import ExcelParserService
        from domain.models import SyncSession, SyncType
        from infrastructure.database.connection import DatabaseConfig, DatabaseManager
        from infrastructure.database.repositories import DealRepositoryImplementation

        logger.info("🔍 Testing change detection...")

        # Setup database
        config = DatabaseConfig()
        db_manager = DatabaseManager(config)

        async with db_manager.get_async_session() as session:
            deal_repo = DealRepositoryImplementation(session)
            detector = ChangeDetectorService(deal_repo)

            # Parse Excel file
            parser = ExcelParserService()
            sync_session = SyncSession(sync_type=SyncType.INCREMENTAL)
            excel_file = Path("data/real_data_for_testing/Data_source_excel.xlsx")

            parse_result = await parser.parse_file(str(excel_file), sync_session)

            # Detect changes
            changes = await detector.detect_changes(parse_result.deals, sync_period_months=12)

            logger.info("✅ Change detection completed!")
            logger.info(f"📊 Insertions: {changes.insertion_count}")
            logger.info(f"📊 Updates: {changes.update_count}")
            logger.info(f"📊 Deletions: {changes.deletion_count}")

            return True

    except Exception as e:
        logger.error(f"❌ Change detection test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    """Main test function."""
    logger.info("🚀 Starting Excel parsing tests...")

    # Test 1: Excel parsing
    success1 = await test_excel_parsing()

    # Test 2: Change detection
    success2 = await test_change_detection()

    if success1 and success2:
        logger.info("🎉 All tests passed successfully!")
    else:
        logger.error("💥 Some tests failed!")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

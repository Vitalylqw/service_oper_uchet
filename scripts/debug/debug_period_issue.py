#!/usr/bin/env python3
"""
Debug script for period validation issues.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loguru import logger
from application.excel_parser import ExcelParserService
from domain.models import SyncSession, SyncType


async def debug_period_issue():
    """Debug period validation issues."""
    logger.info("🔍 Debugging period validation issues...")
    
    # Create parser service
    parser = ExcelParserService()
    
    # Create dummy sync session
    session = SyncSession(sync_type=SyncType.FULL)
    
    # Path to real Excel file
    excel_file = Path("data/real_data_for_testing/Data_source_excel.xlsx")
    
    if not excel_file.exists():
        logger.error(f"❌ Excel file not found: {excel_file}")
        return
    
    logger.info(f"📁 Parsing file: {excel_file}")
    
    # Parse Excel file
    result = await parser.parse_file(str(excel_file), session)
    
    logger.info("✅ Parsing completed!")
    logger.info(f"📊 Total deals: {result.total_deals}")
    logger.info(f"📊 Total items: {result.total_items}")
    logger.info(f"📊 Errors: {len(result.stats.errors)}")
    logger.info(f"📊 Warnings: {len(result.stats.warnings)}")
    
    # Check for deals with invalid periods
    invalid_period_deals = []
    
    for i, deal in enumerate(result.deals):
        try:
            # Check if period is valid
            period = deal.period
            if not period or not period.month or not period.year:
                invalid_period_deals.append((i, deal, "Empty period"))
            elif period.month == "Unknown" or period.year == "0000":
                invalid_period_deals.append((i, deal, "Invalid period values"))
        except Exception as e:
            invalid_period_deals.append((i, deal, f"Period validation error: {e}"))
    
    if invalid_period_deals:
        logger.warning(f"⚠️ Found {len(invalid_period_deals)} deals with invalid periods:")
        for i, deal, reason in invalid_period_deals[:5]:  # Show first 5
            logger.warning(f"  Deal {i}: {deal.client_name} - {reason}")
            logger.warning(f"    Period: {getattr(deal, 'period', 'NO PERIOD')}")
    else:
        logger.info("✅ All deals have valid periods!")
    
    # Show sample deals with their periods
    logger.info("📋 Sample deals with periods:")
    for i, deal in enumerate(result.deals[:5]):
        period_info = f"{deal.period.month} {deal.period.year}" if deal.period else "NO PERIOD"
        logger.info(f"  {i+1}. {deal.client_name} - {deal.invoice_number} - {period_info}")


if __name__ == "__main__":
    asyncio.run(debug_period_issue())
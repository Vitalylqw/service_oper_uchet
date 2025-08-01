#!/usr/bin/env python3
"""
Test script for calc_* fields fix in read_deals table.

This script tests the recalculation of calculated totals after position changes.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loguru import logger
from infrastructure.database.connection import DatabaseConfig, DatabaseManager
from infrastructure.workers.read_model_builder import ReadModelBuilder
from infrastructure.database.event_store import EventStoreImplementation
from infrastructure.database.models import ReadModelDeal
from sqlalchemy import select, text
from decimal import Decimal


async def test_calc_fields_fix():
    """Test the fix for calc_* fields in read_deals."""
    logger.info("🧪 Testing calc_* fields fix...")
    
    # Setup database
    config = DatabaseConfig()
    db_manager = DatabaseManager(config)
    
    async with db_manager.get_async_session() as session:
        # Initialize read model builder
        event_store = EventStoreImplementation(session)
        builder = ReadModelBuilder(session, event_store)
        
        # 1. Check current state
        logger.info("📊 Checking current state of calc_* fields...")
        
        result = await session.execute(text("""
            SELECT 
                deal_key,
                calc_revenue_amount,
                calc_margin_amount,
                calc_cost_amount,
                items_count
            FROM read_deals 
            LIMIT 5
        """))
        
        deals_before = result.fetchall()
        logger.info("Before fix:")
        for deal in deals_before:
            logger.info(f"  Deal: {deal[0]}, calc_revenue: {deal[1]}, calc_margin: {deal[2]}, calc_cost: {deal[3]}, items: {deal[4]}")
        
        # 2. Check positions data
        logger.info("📋 Checking positions data...")
        
        result = await session.execute(text("""
            SELECT 
                deal_id,
                COUNT(*) as pos_count,
                SUM(revenue_amount) as total_revenue,
                SUM(margin_amount) as total_margin,
                SUM(cost_amount) as total_cost
            FROM read_positions 
            WHERE is_active = 1 
            GROUP BY deal_id 
            LIMIT 5
        """))
        
        positions = result.fetchall()
        logger.info("Positions summary:")
        for pos in positions:
            logger.info(f"  Deal: {pos[0]}, positions: {pos[1]}, revenue: {pos[2]}, margin: {pos[3]}, cost: {pos[4]}")
        
        # 3. Test recalculation for first deal
        if positions:
            test_deal_id = positions[0][0]
            logger.info(f"🔄 Testing recalculation for deal: {test_deal_id}")
            
            await builder._recalculate_totals(test_deal_id)
            
            # 4. Check result
            result = await session.execute(
                select(ReadModelDeal).where(ReadModelDeal.id == test_deal_id)
            )
            deal_after = result.scalar()
            
            if deal_after:
                logger.info("✅ After recalculation:")
                logger.info(f"  Deal: {deal_after.deal_key}")
                logger.info(f"  calc_revenue: {deal_after.calc_revenue_amount}")
                logger.info(f"  calc_margin: {deal_after.calc_margin_amount}")
                logger.info(f"  calc_cost: {deal_after.calc_cost_amount}")
                logger.info(f"  items_count: {deal_after.items_count}")
                logger.info(f"  revenue_mismatch: {deal_after.revenue_mismatch}")
                logger.info(f"  margin_mismatch: {deal_after.margin_mismatch}")
                logger.info(f"  cost_mismatch: {deal_after.cost_mismatch}")
                logger.info(f"  has_totals_error: {deal_after.has_totals_error}")
        
        # 5. Test batch recalculation
        logger.info("🔄 Testing batch recalculation for all deals...")
        
        result = await session.execute(text("SELECT id FROM read_deals LIMIT 10"))
        deal_ids = [row[0] for row in result.fetchall()]
        
        for deal_id in deal_ids:
            await builder._recalculate_totals(deal_id)
        
        # 6. Check final state
        logger.info("📊 Final state after batch recalculation:")
        
        result = await session.execute(text("""
            SELECT 
                deal_key,
                calc_revenue_amount,
                calc_margin_amount,
                calc_cost_amount,
                items_count,
                revenue_mismatch,
                margin_mismatch,
                cost_mismatch,
                has_totals_error
            FROM read_deals 
            LIMIT 5
        """))
        
        deals_after = result.fetchall()
        for deal in deals_after:
            logger.info(f"  Deal: {deal[0]}")
            logger.info(f"    calc_revenue: {deal[1]}, calc_margin: {deal[2]}, calc_cost: {deal[3]}")
            logger.info(f"    items: {deal[4]}, mismatches: {deal[5]}/{deal[6]}/{deal[7]}, error: {deal[8]}")
        
        await session.commit()
        logger.info("✅ Test completed successfully!")


async def main():
    """Main test function."""
    try:
        await test_calc_fields_fix()
        return 0
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 
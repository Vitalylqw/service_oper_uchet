#!/usr/bin/env python3
"""
Script to update all calc_* fields in read_deals table.

This script recalculates all calculated totals for all deals in the database.
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
from sqlalchemy import text


async def update_all_calc_fields():
    """Update all calc_* fields for all deals."""
    logger.info("🔄 Starting full update of calc_* fields...")
    
    # Setup database
    config = DatabaseConfig()
    db_manager = DatabaseManager(config)
    
    async with db_manager.get_async_session() as session:
        # Initialize read model builder
        event_store = EventStoreImplementation(session)
        builder = ReadModelBuilder(session, event_store)
        
        # 1. Get all deal IDs
        logger.info("📋 Getting all deal IDs...")
        result = await session.execute(text("SELECT id FROM read_deals"))
        deal_ids = [row[0] for row in result.fetchall()]
        
        logger.info(f"📊 Found {len(deal_ids)} deals to update")
        
        # 2. Check current state
        result = await session.execute(text("""
            SELECT 
                COUNT(*) as total_deals,
                COUNT(CASE WHEN calc_revenue_amount = 0 AND calc_margin_amount = 0 AND calc_cost_amount = 0 THEN 1 END) as zero_calc_deals,
                COUNT(CASE WHEN calc_revenue_amount > 0 OR calc_margin_amount > 0 OR calc_cost_amount > 0 THEN 1 END) as non_zero_calc_deals
            FROM read_deals
        """))
        
        stats = result.fetchone()
        logger.info(f"📈 Current state: total={stats[0]}, zero_calc={stats[1]}, non_zero_calc={stats[2]}")
        
        # 3. Update all deals
        logger.info("🔄 Updating calc_* fields for all deals...")
        
        updated_count = 0
        error_count = 0
        
        for i, deal_id in enumerate(deal_ids):
            try:
                await builder._recalculate_totals(deal_id)
                updated_count += 1
                
                if (i + 1) % 50 == 0:
                    logger.info(f"✅ Updated {i + 1}/{len(deal_ids)} deals...")
                    
            except Exception as e:
                logger.error(f"❌ Error updating deal {deal_id}: {e}")
                error_count += 1
        
        # 4. Check final state
        logger.info("📊 Checking final state...")
        
        result = await session.execute(text("""
            SELECT 
                COUNT(*) as total_deals,
                COUNT(CASE WHEN calc_revenue_amount = 0 AND calc_margin_amount = 0 AND calc_cost_amount = 0 THEN 1 END) as zero_calc_deals,
                COUNT(CASE WHEN calc_revenue_amount > 0 OR calc_margin_amount > 0 OR calc_cost_amount > 0 THEN 1 END) as non_zero_calc_deals,
                COUNT(CASE WHEN has_totals_error = true THEN 1 END) as error_deals
            FROM read_deals
        """))
        
        final_stats = result.fetchone()
        logger.info(f"📈 Final state: total={final_stats[0]}, zero_calc={final_stats[1]}, non_zero_calc={final_stats[2]}, errors={final_stats[3]}")
        
        # 5. Show some examples
        logger.info("📋 Examples of updated deals:")
        result = await session.execute(text("""
            SELECT 
                deal_key,
                calc_revenue_amount,
                calc_margin_amount,
                calc_cost_amount,
                items_count,
                has_totals_error
            FROM read_deals 
            WHERE calc_revenue_amount > 0 OR calc_margin_amount > 0 OR calc_cost_amount > 0
            LIMIT 5
        """))
        
        examples = result.fetchall()
        for example in examples:
            logger.info(f"  {example[0]}: revenue={example[1]}, margin={example[2]}, cost={example[3]}, items={example[4]}, error={example[5]}")
        
        # 6. Show deals with errors
        logger.info("⚠️ Deals with calculation errors:")
        result = await session.execute(text("""
            SELECT 
                deal_key,
                total_revenue_amount,
                total_margin_amount,
                total_cost_amount,
                calc_revenue_amount,
                calc_margin_amount,
                calc_cost_amount
            FROM read_deals 
            WHERE has_totals_error = true
            LIMIT 5
        """))
        
        error_examples = result.fetchall()
        for error_example in error_examples:
            logger.info(f"  {error_example[0]}: total_rev={error_example[1]}, total_mar={error_example[2]}, total_cost={error_example[3]}, calc_rev={error_example[4]}, calc_mar={error_example[5]}, calc_cost={error_example[6]}")
        
        await session.commit()
        
        logger.info(f"✅ Update completed! Updated: {updated_count}, Errors: {error_count}")


async def main():
    """Main function."""
    try:
        await update_all_calc_fields()
        return 0
    except Exception as e:
        logger.error(f"❌ Update failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 
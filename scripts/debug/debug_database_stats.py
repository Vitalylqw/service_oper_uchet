#!/usr/bin/env python3
"""
Debug database stats issue.
Check what's actually in the database and why stats are empty.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger
from sqlalchemy import text

from infrastructure.database.connection import DatabaseConfig, DatabaseManager


async def debug_database_stats():
    """Debug database stats issue."""
    
    logger.info("🔍 Debugging database stats...")
    
    # Get database configuration
    db_config = DatabaseConfig()
    db_manager = DatabaseManager(db_config)
    
    try:
        async with db_manager.get_async_session() as session:
            
            # 1. Check total deals count
            logger.info("1. Checking total deals count...")
            total_deals = await session.execute(text("SELECT COUNT(*) FROM read_deals"))
            total_count = total_deals.scalar()
            logger.info(f"Total deals in DB: {total_count}")
            
            # 2. Check is_active field values
            logger.info("2. Checking is_active field values...")
            active_check = await session.execute(text("""
                SELECT is_active, COUNT(*) as count
                FROM read_deals
                GROUP BY is_active
            """))
            for row in active_check.fetchall():
                logger.info(f"is_active = {row[0]} (type: {type(row[0])}): {row[1]} deals")
            
            # 3. Check with different boolean formats
            logger.info("3. Testing different boolean formats...")
            
            # Test is_active = 1
            count_1 = await session.execute(text("SELECT COUNT(*) FROM read_deals WHERE is_active = 1"))
            logger.info(f"is_active = 1: {count_1.scalar()} deals")
            
            # Test is_active = true
            count_true = await session.execute(text("SELECT COUNT(*) FROM read_deals WHERE is_active = true"))
            logger.info(f"is_active = true: {count_true.scalar()} deals")
            
            # Test is_active = 'true' (string)
            count_str_true = await session.execute(text("SELECT COUNT(*) FROM read_deals WHERE is_active = 'true'"))
            logger.info(f"is_active = 'true': {count_str_true.scalar()} deals")
            
            # Test is_active IS TRUE
            count_is_true = await session.execute(text("SELECT COUNT(*) FROM read_deals WHERE is_active IS TRUE"))
            logger.info(f"is_active IS TRUE: {count_is_true.scalar()} deals")
            
            # 4. Check financial data
            logger.info("4. Checking financial data...")
            financial_check = await session.execute(text("""
                SELECT
                    COUNT(*) as deals_count,
                    SUM(total_revenue_amount) as total_revenue,
                    SUM(total_margin_amount) as total_margin,
                    AVG(total_revenue_amount) as avg_revenue
                FROM read_deals
            """))
            row = financial_check.fetchone()
            if row:
                logger.info(f"All deals - count: {row[0]}, revenue: {row[1]}, margin: {row[2]}, avg: {row[3]}")
            
            # 5. Check sample deal data
            logger.info("5. Sample deal data...")
            sample_deals = await session.execute(text("""
                SELECT
                    client_name,
                    is_active,
                    total_revenue_amount,
                    is_shipped,
                    is_paid
                FROM read_deals
                LIMIT 3
            """))
            for i, row in enumerate(sample_deals.fetchall()):
                logger.info(f"Deal {i+1}: client='{row[0]}', is_active={row[1]}, revenue={row[2]}, shipped={row[3]}, paid={row[4]}")
                
            # 6. Check database type info
            logger.info("6. Database info...")
            logger.info(f"DB Type: {db_config.db_type}")
            if db_config.db_type == "sqlite":
                logger.info(f"SQLite path: {db_config.sqlite_db_path}")
                
    except Exception as e:
        logger.error(f"Error debugging database: {e}")
        return False
        
    return True


async def main():
    """Main function."""
    logger.info("🚀 Starting database stats debug...")
    
    success = await debug_database_stats()
    
    if success:
        logger.info("🎉 Database debug completed!")
    else:
        logger.error("💥 Database debug failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

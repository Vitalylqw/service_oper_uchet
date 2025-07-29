#!/usr/bin/env python3
"""
Ultra-fast migration script to fix events with empty periods using single SQL query.

This migration updates all DealCreated events with empty period data in one operation.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loguru import logger
from infrastructure.database.connection import DatabaseConfig, DatabaseManager
from sqlalchemy import text


async def fix_empty_periods_migration_ultra_fast():
    """Ultra-fast migration using single SQL query."""
    logger.info("⚡ Starting ULTRA-FAST migration: Fix empty periods in events")
    
    # Create database manager
    db_config = DatabaseConfig()
    db_manager = DatabaseManager(db_config)
    
    # Get database session
    async with db_manager.get_async_session() as session:
        
        # First, count how many events need fixing
        logger.info("🔍 Counting events with empty periods...")
        
        count_query = text("""
        SELECT COUNT(*) as count
        FROM event_store 
        WHERE event_type = 'DealCreated' 
        AND (
            event_data IS NULL 
            OR json_extract(event_data, '$.period') IS NULL 
            OR json_extract(event_data, '$.period.month') IS NULL 
            OR json_extract(event_data, '$.period.year') IS NULL 
            OR json_extract(event_data, '$.period.month') = '' 
            OR json_extract(event_data, '$.period.year') = '' 
            OR json_extract(event_data, '$.period.month') = 'Unknown' 
            OR json_extract(event_data, '$.period.year') = '0000'
        )
        """)
        
        result = await session.execute(count_query)
        count = result.scalar()
        
        logger.info(f"⚠️ Found {count} events with empty/invalid periods")
        
        if count == 0:
            logger.info("✅ No events with empty periods found. Migration not needed.")
            return
        
        # Show sample events
        logger.info("📋 Sample events to be fixed:")
        sample_query = text("""
        SELECT event_id, event_data, created_at
        FROM event_store 
        WHERE event_type = 'DealCreated' 
        AND (
            event_data IS NULL 
            OR json_extract(event_data, '$.period') IS NULL 
            OR json_extract(event_data, '$.period.month') IS NULL 
            OR json_extract(event_data, '$.period.year') IS NULL 
            OR json_extract(event_data, '$.period.month') = '' 
            OR json_extract(event_data, '$.period.year') = '' 
            OR json_extract(event_data, '$.period.month') = 'Unknown' 
            OR json_extract(event_data, '$.period.year') = '0000'
        )
        LIMIT 5
        """)
        
        result = await session.execute(sample_query)
        samples = result.fetchall()
        
        for i, (event_id, event_data, created_at) in enumerate(samples):
            client_name = "UNKNOWN"
            if event_data:
                try:
                    import json
                    data = json.loads(event_data) if isinstance(event_data, str) else event_data
                    client_name = data.get("client_name", "UNKNOWN")
                except:
                    pass
            logger.info(f"  {i+1}. {client_name} - Created: {created_at}")
        
        # Ultra-fast update using single SQL query with CASE statement
        logger.info("⚡ Fixing events with empty periods (ultra-fast method)...")
        
        # Create the update query that handles all cases in one operation
        update_query = text("""
        UPDATE event_store 
        SET event_data = CASE 
            WHEN created_at IS NOT NULL THEN
                json_set(
                    COALESCE(event_data, '{}'),
                    '$.period',
                    json_object(
                        'month', 
                        CASE strftime('%m', created_at)
                            WHEN '01' THEN 'Январь'
                            WHEN '02' THEN 'Февраль'
                            WHEN '03' THEN 'Март'
                            WHEN '04' THEN 'Апрель'
                            WHEN '05' THEN 'Май'
                            WHEN '06' THEN 'Июнь'
                            WHEN '07' THEN 'Июль'
                            WHEN '08' THEN 'Август'
                            WHEN '09' THEN 'Сентябрь'
                            WHEN '10' THEN 'Октябрь'
                            WHEN '11' THEN 'Ноябрь'
                            WHEN '12' THEN 'Декабрь'
                            ELSE 'Январь'
                        END,
                        'year', strftime('%Y', created_at),
                        'full_name', 
                        CASE strftime('%m', created_at)
                            WHEN '01' THEN 'Январь ' || strftime('%Y', created_at)
                            WHEN '02' THEN 'Февраль ' || strftime('%Y', created_at)
                            WHEN '03' THEN 'Март ' || strftime('%Y', created_at)
                            WHEN '04' THEN 'Апрель ' || strftime('%Y', created_at)
                            WHEN '05' THEN 'Май ' || strftime('%Y', created_at)
                            WHEN '06' THEN 'Июнь ' || strftime('%Y', created_at)
                            WHEN '07' THEN 'Июль ' || strftime('%Y', created_at)
                            WHEN '08' THEN 'Август ' || strftime('%Y', created_at)
                            WHEN '09' THEN 'Сентябрь ' || strftime('%Y', created_at)
                            WHEN '10' THEN 'Октябрь ' || strftime('%Y', created_at)
                            WHEN '11' THEN 'Ноябрь ' || strftime('%Y', created_at)
                            WHEN '12' THEN 'Декабрь ' || strftime('%Y', created_at)
                            ELSE 'Январь ' || strftime('%Y', created_at)
                        END
                    )
                )
            ELSE
                json_set(
                    COALESCE(event_data, '{}'),
                    '$.period',
                    json_object(
                        'month', 'Январь',
                        'year', '2025',
                        'full_name', 'Январь 2025'
                    )
                )
        END
        WHERE event_type = 'DealCreated' 
        AND (
            event_data IS NULL 
            OR json_extract(event_data, '$.period') IS NULL 
            OR json_extract(event_data, '$.period.month') IS NULL 
            OR json_extract(event_data, '$.period.year') IS NULL 
            OR json_extract(event_data, '$.period.month') = '' 
            OR json_extract(event_data, '$.period.year') = '' 
            OR json_extract(event_data, '$.period.month') = 'Unknown' 
            OR json_extract(event_data, '$.period.year') = '0000'
        )
        """)
        
        # Execute the update
        start_time = datetime.now()
        result = await session.execute(update_query)
        await session.commit()
        end_time = datetime.now()
        
        # Get the number of affected rows
        affected_rows = result.rowcount
        
        duration = (end_time - start_time).total_seconds()
        
        logger.info("✅ ULTRA-FAST Migration completed!")
        logger.info(f"📊 Results:")
        logger.info(f"  ✅ Fixed events: {affected_rows}")
        logger.info(f"  ⏱️ Duration: {duration:.2f} seconds")
        logger.info(f"  🚀 Speed: {affected_rows/duration:.1f} events/second")


if __name__ == "__main__":
    asyncio.run(fix_empty_periods_migration_ultra_fast()) 
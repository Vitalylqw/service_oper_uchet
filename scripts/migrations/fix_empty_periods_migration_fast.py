#!/usr/bin/env python3
"""
Fast migration script to fix events with empty periods using batching.

This migration finds DealCreated events with empty period data and updates them
in batches for better performance.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loguru import logger
from infrastructure.database.connection import DatabaseConfig, DatabaseManager
from infrastructure.database.event_store import EventStoreImplementation
from infrastructure.database.models import EventStoreModel
from sqlalchemy import select, update, text


async def fix_empty_periods_migration_fast():
    """Fast migration to fix events with empty periods using batching."""
    logger.info("🚀 Starting FAST migration: Fix empty periods in events")
    
    # Create database manager
    db_config = DatabaseConfig()
    db_manager = DatabaseManager(db_config)
    
    # Get database session
    async with db_manager.get_async_session() as session:
        event_store = EventStoreImplementation(session)
        
        # Find events with empty periods using direct SQL for speed
        logger.info("🔍 Finding events with empty periods (fast method)...")
        
        # Use direct SQL query to find events with empty periods
        sql_query = """
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
        """
        
        result = await session.execute(text(sql_query))
        events_to_fix = result.fetchall()
        
        logger.info(f"⚠️ Found {len(events_to_fix)} events with empty/invalid periods")
        
        if not events_to_fix:
            logger.info("✅ No events with empty periods found. Migration not needed.")
            return
        
        # Show sample events that will be fixed
        logger.info("📋 Sample events to be fixed:")
        for i, (event_id, event_data, created_at) in enumerate(events_to_fix[:5]):
            client_name = "UNKNOWN"
            if event_data:
                try:
                    import json
                    data = json.loads(event_data) if isinstance(event_data, str) else event_data
                    client_name = data.get("client_name", "UNKNOWN")
                except:
                    pass
            logger.info(f"  {i+1}. {client_name} - Created: {created_at}")
        
        # Fix events in batches
        logger.info("🔧 Fixing events with empty periods (batch processing)...")
        
        batch_size = 1000
        total_fixed = 0
        total_errors = 0
        
        # Process in batches
        for i in range(0, len(events_to_fix), batch_size):
            batch = events_to_fix[i:i + batch_size]
            batch_start = i + 1
            batch_end = min(i + batch_size, len(events_to_fix))
            
            logger.info(f"📦 Processing batch {batch_start}-{batch_end} of {len(events_to_fix)}...")
            
            # Create batch update statements
            update_statements = []
            
            for event_id, event_data, created_at in batch:
                try:
                    # Parse existing event data
                    if isinstance(event_data, str):
                        import json
                        data = json.loads(event_data)
                    else:
                        data = event_data or {}
                    
                    # Determine fallback period based on event creation time
                    if created_at:
                        # Use the month and year from creation time
                        month_name = created_at.strftime("%B")  # Full month name in English
                        year = str(created_at.year)
                        
                        # Convert English month to Russian
                        month_mapping = {
                            "January": "Январь", "February": "Февраль", "March": "Март",
                            "April": "Апрель", "May": "Май", "June": "Июнь",
                            "July": "Июль", "August": "Август", "September": "Сентябрь",
                            "October": "Октябрь", "November": "Ноябрь", "December": "Декабрь"
                        }
                        
                        russian_month = month_mapping.get(month_name, "Январь")
                        
                        # Create new period data
                        new_period_data = {
                            "month": russian_month,
                            "year": year,
                            "full_name": f"{russian_month} {year}"
                        }
                    else:
                        # Fallback to default period
                        new_period_data = {
                            "month": "Январь",
                            "year": "2025",
                            "full_name": "Январь 2025"
                        }
                    
                    # Update event data
                    data["period"] = new_period_data
                    
                    # Create update statement
                    import json
                    new_event_data = json.dumps(data, ensure_ascii=False)
                    
                    update_stmt = text("""
                        UPDATE event_store 
                        SET event_data = :event_data 
                        WHERE event_id = :event_id
                    """)
                    
                    update_statements.append({
                        "event_data": new_event_data,
                        "event_id": event_id
                    })
                    
                except Exception as e:
                    logger.error(f"❌ Error preparing update for event {event_id}: {e}")
                    total_errors += 1
            
            # Execute batch update
            try:
                for params in update_statements:
                    await session.execute(
                        text("UPDATE event_store SET event_data = :event_data WHERE event_id = :event_id"),
                        params
                    )
                
                # Commit batch
                await session.commit()
                total_fixed += len(update_statements)
                
                logger.info(f"✅ Batch {batch_start}-{batch_end} completed. Total fixed: {total_fixed}")
                
            except Exception as e:
                logger.error(f"❌ Error updating batch {batch_start}-{batch_end}: {e}")
                await session.rollback()
                total_errors += len(batch)
        
        logger.info("✅ FAST Migration completed!")
        logger.info(f"📊 Results:")
        logger.info(f"  ✅ Fixed events: {total_fixed}")
        logger.info(f"  ❌ Errors: {total_errors}")
        logger.info(f"  📋 Total processed: {len(events_to_fix)}")


if __name__ == "__main__":
    asyncio.run(fix_empty_periods_migration_fast()) 
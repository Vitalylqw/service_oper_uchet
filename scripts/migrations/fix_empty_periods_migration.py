#!/usr/bin/env python3
"""
Migration script to fix events with empty periods.

This migration finds DealCreated events with empty period data and updates them
with valid fallback periods based on the event creation time or other available data.
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
from sqlalchemy import select, update


async def fix_empty_periods_migration():
    """Migration to fix events with empty periods."""
    logger.info("🔧 Starting migration: Fix empty periods in events")
    
    # Create database manager
    db_config = DatabaseConfig()
    db_manager = DatabaseManager(db_config)
    
    # Get database session
    async with db_manager.get_async_session() as session:
        event_store = EventStoreImplementation(session)
        
        # Find events with empty periods
        logger.info("🔍 Finding events with empty periods...")
        
        # Query for DealCreated events with empty period data
        query = select(EventStoreModel).where(
            EventStoreModel.event_type == "DealCreated"
        )
        
        result = await session.execute(query)
        events = result.scalars().all()
        
        logger.info(f"📊 Found {len(events)} DealCreated events total")
        
        # Filter events with empty periods
        events_with_empty_periods = []
        
        for event in events:
            try:
                event_data = event.event_data
                if isinstance(event_data, dict):
                    period_data = event_data.get("period", {})
                    
                    # Check if period is empty or invalid
                    if (not period_data or 
                        not period_data.get("month") or 
                        not period_data.get("year") or
                        period_data.get("month") == "" or
                        period_data.get("year") == "" or
                        period_data.get("month") == "Unknown" or
                        period_data.get("year") == "0000"):
                        
                        events_with_empty_periods.append(event)
            except Exception as e:
                logger.warning(f"⚠️ Error processing event {event.event_id}: {e}")
                events_with_empty_periods.append(event)
        
        logger.info(f"⚠️ Found {len(events_with_empty_periods)} events with empty/invalid periods")
        
        if not events_with_empty_periods:
            logger.info("✅ No events with empty periods found. Migration not needed.")
            return
        
        # Show sample events that will be fixed
        logger.info("📋 Sample events to be fixed:")
        for i, event in enumerate(events_with_empty_periods[:5]):
            event_data = event.event_data or {}
            client_name = event_data.get("client_name", "UNKNOWN")
            period_data = event_data.get("period", {})
            created_at = event.created_at
            
            logger.info(f"  {i+1}. {client_name} - Period: {period_data} - Created: {created_at}")
        
        # Fix events with empty periods
        logger.info("🔧 Fixing events with empty periods...")
        
        fixed_count = 0
        error_count = 0
        
        for event in events_with_empty_periods:
            try:
                # Determine fallback period based on event creation time
                created_at = event.created_at
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
                event_data = event.event_data or {}
                event_data["period"] = new_period_data
                
                # Update the event in database
                update_stmt = (
                    update(EventStoreModel)
                    .where(EventStoreModel.event_id == event.event_id)
                    .values(event_data=event_data)
                )
                
                await session.execute(update_stmt)
                fixed_count += 1
                
                if fixed_count % 100 == 0:
                    logger.info(f"✅ Fixed {fixed_count} events...")
                
            except Exception as e:
                logger.error(f"❌ Error fixing event {event.event_id}: {e}")
                error_count += 1
        
        # Commit changes
        await session.commit()
        
        logger.info("✅ Migration completed!")
        logger.info(f"📊 Results:")
        logger.info(f"  ✅ Fixed events: {fixed_count}")
        logger.info(f"  ❌ Errors: {error_count}")
        logger.info(f"  📋 Total processed: {len(events_with_empty_periods)}")


if __name__ == "__main__":
    asyncio.run(fix_empty_periods_migration())
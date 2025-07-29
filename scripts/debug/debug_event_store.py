#!/usr/bin/env python3
"""
Debug script for Event Store issues.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loguru import logger
from infrastructure.database.connection import DatabaseConfig, DatabaseManager
from infrastructure.database.event_store import EventStoreImplementation


async def debug_event_store():
    """Debug Event Store issues."""
    logger.info("🔍 Debugging Event Store issues...")
    
    # Create database manager
    db_config = DatabaseConfig()
    db_manager = DatabaseManager(db_config)
    
    # Get database session
    async with db_manager.get_async_session() as session:
        event_store = EventStoreImplementation(session)
        
        # Get latest events
        events = await event_store.get_latest_events(limit=100)
        
        logger.info(f"📊 Found {len(events)} events in Event Store")
        
        # Check for events with invalid periods
        invalid_period_events = []
        
        for i, event in enumerate(events):
            if event.get("event_type") == "DealCreated":
                event_data = event.get("event_data", {})
                period_data = event_data.get("period", {})
                
                if not period_data or not period_data.get("month") or not period_data.get("year"):
                    invalid_period_events.append((i, event, "Empty period data"))
                elif period_data.get("month") == "Unknown" or period_data.get("year") == "0000":
                    invalid_period_events.append((i, event, "Invalid period values"))
                elif period_data.get("month") == "" or period_data.get("year") == "":
                    invalid_period_events.append((i, event, "Empty period values"))
        
        if invalid_period_events:
            logger.warning(f"⚠️ Found {len(invalid_period_events)} events with invalid periods:")
            for i, event, reason in invalid_period_events[:5]:  # Show first 5
                event_data = event.get("event_data", {})
                client_name = event_data.get("client_name", "UNKNOWN")
                period_data = event_data.get("period", {})
                created_at = event.get("created_at", "UNKNOWN")
                logger.warning(f"  Event {i}: {client_name} - {reason}")
                logger.warning(f"    Period: {period_data}")
                logger.warning(f"    Event ID: {event.get('event_id')}")
                logger.warning(f"    Aggregate ID: {event.get('aggregate_id')}")
                logger.warning(f"    Created at: {created_at}")
        else:
            logger.info("✅ All events have valid periods!")
        
        # Show sample events
        logger.info("📋 Sample events:")
        for i, event in enumerate(events[:5]):
            event_type = event.get("event_type", "UNKNOWN")
            event_data = event.get("event_data", {})
            created_at = event.get("created_at", "UNKNOWN")
            
            if event_type == "DealCreated":
                client_name = event_data.get("client_name", "UNKNOWN")
                period_data = event_data.get("period", {})
                period_info = f"{period_data.get('month', '')} {period_data.get('year', '')}" if period_data else "NO PERIOD"
                logger.info(f"  {i+1}. {event_type}: {client_name} - {period_info} ({created_at})")
            else:
                logger.info(f"  {i+1}. {event_type} ({created_at})")


if __name__ == "__main__":
    asyncio.run(debug_event_store())
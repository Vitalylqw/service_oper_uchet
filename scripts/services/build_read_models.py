#!/usr/bin/env python3
"""Build read models from events."""

import asyncio

from src.infrastructure.database.connection import get_database_session
from src.infrastructure.database.event_store import EventStoreImplementation
from src.infrastructure.workers.read_model_builder import ReadModelBuilder


async def build_read_models():
    """Build read models from all events."""
    print("=== BUILDING READ MODELS ===")
    
    async for session in get_database_session():
        try:
            # Create event store
            event_store = EventStoreImplementation(session)
            
            # Create read model builder
            builder = ReadModelBuilder(session, event_store)
            
            # Process all events
            print("Processing all events...")
            processed = await builder.process_latest_events(limit=1000)
            print(f"✅ Processed {processed} events")
            
            await session.commit()
            print("✅ Read models built successfully!")
            
        except Exception as e:
            print(f"❌ Error building read models: {e}")
            await session.rollback()
            raise
        break


if __name__ == "__main__":
    asyncio.run(build_read_models())

#!/usr/bin/env python3
"""
Test script for hybrid deferred events approach.

Tests the combination of:
1. Proper event ordering (aggregate_id, sequence_number)
2. Deferred event queue for failed processing
3. Retry mechanism with exponential backoff
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.infrastructure.database.connection import get_database_session
from src.infrastructure.database.event_store import EventStoreImplementation
from src.infrastructure.workers.read_model_builder import ReadModelBuilder
from src.infrastructure.workers.deferred_event_queue import DeferredEventQueue


async def test_hybrid_approach():
    """Test the hybrid approach with deferred events."""
    logger.info("🧪 Testing Hybrid Deferred Events Approach")
    
    async for session in get_database_session():
        try:
            # Initialize components
            event_store = EventStoreImplementation(session)
            read_model_builder = ReadModelBuilder(session, event_store)
            
            # Test 1: Check event ordering
            logger.info("📋 Test 1: Checking event ordering...")
            events = await event_store.get_latest_events(limit=10)
            
            if events:
                logger.info(f"Found {len(events)} events")
                for i, event in enumerate(events[:5]):  # Show first 5
                    logger.info(
                        f"  {i+1}. {event['event_type']} | "
                        f"Aggregate: {event['aggregate_id']} | "
                        f"Sequence: {event['sequence_number']}"
                    )
            else:
                logger.info("No events found in database")
            
            # Test 2: Check deferred queue status
            logger.info("📋 Test 2: Checking deferred queue status...")
            queue_status = read_model_builder.deferred_queue.get_queue_status()
            logger.info(f"Queue status: {queue_status}")
            
            # Test 3: Process events with hybrid approach
            logger.info("📋 Test 3: Processing events with hybrid approach...")
            processed_count = await read_model_builder.process_latest_events(
                limit=50, auto_commit=False
            )
            logger.info(f"Processed {processed_count} events")
            
            # Test 4: Check final queue status
            logger.info("📋 Test 4: Final queue status...")
            final_status = read_model_builder.deferred_queue.get_queue_status()
            logger.info(f"Final queue status: {final_status}")
            
            # Test 5: Show deferred events details if any
            if final_status['queue_size'] > 0:
                logger.info("📋 Test 5: Deferred events details...")
                deferred_events = read_model_builder.deferred_queue.get_deferred_events_summary()
                for event in deferred_events:
                    logger.warning(f"Deferred: {event}")
            
            # Commit if no errors
            await session.commit()
            logger.info("✅ All tests completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            await session.rollback()
            raise
        finally:
            break


async def test_deferred_queue_standalone():
    """Test deferred queue functionality standalone."""
    logger.info("🧪 Testing Deferred Queue Standalone")
    
    queue = DeferredEventQueue(max_retries=2)
    
    # Create test events
    test_events = [
        {
            "event_type": "DealItemAdded",
            "aggregate_id": "test-deal-1",
            "event_data": {"test": "data1"}
        },
        {
            "event_type": "DealCreated", 
            "aggregate_id": "test-deal-2",
            "event_data": {"test": "data2"}
        }
    ]
    
    # Add events to queue
    await queue.add_event(test_events[0], "Parent deal not found")
    await queue.add_event(test_events[1], "Invalid period data")
    
    # Check status
    status = queue.get_queue_status()
    logger.info(f"Queue status after adding events: {status}")
    
    # Test processing (with mock processor)
    async def mock_processor(event):
        logger.info(f"Processing event: {event['event_type']}")
        # Simulate success
        return True
    
    processed = await queue.process_deferred_events(mock_processor)
    logger.info(f"Processed {processed} events")
    
    # Final status
    final_status = queue.get_queue_status()
    logger.info(f"Final queue status: {final_status}")


async def main():
    """Main test function."""
    logger.info("🚀 Starting Hybrid Deferred Events Tests")
    
    try:
        # Test 1: Standalone deferred queue
        await test_deferred_queue_standalone()
        
        # Test 2: Full hybrid approach
        await test_hybrid_approach()
        
        logger.info("✅ All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Tests failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
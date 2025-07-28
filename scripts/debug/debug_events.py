#!/usr/bin/env python3
"""Debug events in event store."""

import asyncio
import json

from sqlalchemy import text

from src.infrastructure.database.connection import get_database_session


async def debug_events():
    """Debug events in event store."""
    print("=== DEBUGGING EVENTS ===")
    
    async for session in get_database_session():
        try:
            # Get sample events
            result = await session.execute(
                text("SELECT event_id, aggregate_id, event_type, event_data FROM event_store LIMIT 5")
            )
            events = result.fetchall()
            
            print(f"Found {len(events)} sample events:")
            
            for i, event in enumerate(events):
                print(f"\n📋 Event #{i+1}:")
                print(f"  Event ID: {event[0]}")
                print(f"  Aggregate ID: {event[1]}")
                print(f"  Event Type: {event[2]}")
                print(f"  Event Data: {event[3]}")
                
                # Try to parse event data
                try:
                    if event[3]:
                        data = json.loads(event[3])
                        print(f"  Parsed Data Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        
                        if isinstance(data, dict) and 'deal' in data:
                            deal_data = data['deal']
                            print(f"    Deal Keys: {list(deal_data.keys()) if isinstance(deal_data, dict) else 'Not a dict'}")
                            if isinstance(deal_data, dict):
                                print(f"    Client Name: {deal_data.get('client_name', 'MISSING')}")
                                print(f"    Invoice Info: {deal_data.get('invoice_info', 'MISSING')}")
                    else:
                        print("  ❌ Event data is empty/null")
                        
                except Exception as e:
                    print(f"  ❌ Failed to parse event data: {e}")
                
        except Exception as e:
            print(f"❌ Error debugging events: {e}")
        break


if __name__ == "__main__":
    asyncio.run(debug_events())

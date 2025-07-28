#!/usr/bin/env python3
"""Fix read model builder for correct event format."""

import asyncio

from sqlalchemy.dialects.sqlite import insert

from src.infrastructure.database.connection import get_database_session
from src.infrastructure.database.event_store import EventStoreImplementation
from src.infrastructure.database.models import ReadModelDeal
from src.infrastructure.workers.read_model_builder import ReadModelBuilder


async def process_deal_created_event_fixed(session, event_data, full_event):
    """Fixed version of deal created event processing."""
    try:
        # Parse data directly from event (not wrapped in "deal" object)
        deal_id = event_data.get("deal_id")
        deal_key = event_data.get("deal_key", "")
        client_name = event_data.get("client_name", "")
        invoice_info = event_data.get("invoice_info", "")
        invoice_number = event_data.get("invoice_number", "")
        invoice_date = event_data.get("invoice_date", "")
        
        # Parse period
        period = event_data.get("period", {})
        period_month = period.get("month", "") if isinstance(period, dict) else ""
        period_year = period.get("year", "") if isinstance(period, dict) else ""
        period_full_name = period.get("full_name", "") if isinstance(period, dict) else ""
        
        # Parse status fields
        is_shipped = event_data.get("is_shipped", "")
        is_paid = event_data.get("is_paid", "")
        upd_number = event_data.get("upd_number", "")
        seller = event_data.get("seller", "")
        
        # Parse totals
        totals = event_data.get("totals", {})
        revenue = totals.get("revenue", {}) if isinstance(totals, dict) else {}
        margin = totals.get("margin", {}) if isinstance(totals, dict) else {}
        cost = totals.get("cost", {}) if isinstance(totals, dict) else {}
        kickback = totals.get("kickback") if isinstance(totals, dict) else None
        
        # Create read model entry
        read_deal_data = {
            "id": deal_id,
            "deal_key": deal_key,
            "hash_key": str(hash(deal_key))[:32],  # Simple hash
            "client_name": client_name,
            "invoice_info": invoice_info,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "period_month": period_month,
            "period_year": period_year,
            "period_full_name": period_full_name,
            "is_shipped": is_shipped,
            "is_paid": is_paid,
            "upd_number": upd_number,
            "seller": seller,
            "total_revenue_amount": float(revenue.get("amount", 0)) if isinstance(revenue, dict) and revenue.get("amount") else None,
            "total_revenue_currency": revenue.get("currency", "RUB") if isinstance(revenue, dict) else "RUB",
            "total_margin_amount": float(margin.get("amount", 0)) if isinstance(margin, dict) and margin.get("amount") else None,
            "total_margin_currency": margin.get("currency", "RUB") if isinstance(margin, dict) else "RUB",
            "total_cost_amount": float(cost.get("amount", 0)) if isinstance(cost, dict) and cost.get("amount") else None,
            "total_cost_currency": cost.get("currency", "RUB") if isinstance(cost, dict) else "RUB",
            "kickback_amount_value": float(kickback.get("amount", 0)) if kickback and isinstance(kickback, dict) and kickback.get("amount") else None,
            "kickback_amount_currency": kickback.get("currency", "RUB") if kickback and isinstance(kickback, dict) else "RUB",
            "items_count": 0,  # Will be updated by items
            "total_quantity": 0,  # Will be updated by items
            "is_active": True,
        }
        
        # Use upsert to handle conflicts
        stmt = insert(ReadModelDeal).values(**read_deal_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={key: stmt.excluded[key] for key in read_deal_data.keys()}
        )
        
        await session.execute(stmt)
        print(f"✅ Created read model for deal {deal_key}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create deal read model: {e}")
        return False


async def build_read_models_fixed():
    """Build read models with fixed event parsing."""
    print("=== BUILDING READ MODELS (FIXED) ===")
    
    async for session in get_database_session():
        try:
            # Get events directly
            from sqlalchemy import text
            result = await session.execute(
                text("SELECT event_id, aggregate_id, event_type, event_data FROM event_store WHERE event_type = 'DealCreated' ORDER BY created_at")
            )
            events = result.fetchall()
            
            print(f"Processing {len(events)} DealCreated events...")
            
            processed = 0
            for event in events:
                event_id, aggregate_id, event_type, event_data_json = event
                
                import json
                event_data = json.loads(event_data_json)
                
                success = await process_deal_created_event_fixed(
                    session,
                    event_data,
                    {"event_id": event_id, "aggregate_id": aggregate_id}
                )
                
                if success:
                    processed += 1
            
            await session.commit()
            print(f"✅ Successfully processed {processed} deal events")
            
        except Exception as e:
            print(f"❌ Error building read models: {e}")
            await session.rollback()
            raise
        break


if __name__ == "__main__":
    asyncio.run(build_read_models_fixed())

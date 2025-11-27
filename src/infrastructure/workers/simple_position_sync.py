"""
Simplified Position Synchronization Logic (No Versioning).

Implements new simplified sync logic:
1. Current state only in read_positions
2. Simple UPSERT/DELETE operations  
3. No soft deletes, no versioning
4. Full history preserved in event_store

Author: System Architect
Date: 2025-01-21
"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models import Deal, DealItem
from ..database.models import ReadModelPosition


class SimplePositionSync:
    """
    Simplified position synchronization logic without versioning.
    
    Key principles:
    1. Use hash_key for position identification 
    2. Simple UPSERT for existing positions
    3. DELETE for removed positions (hard delete)
    4. Current state only in DB, history in event_store
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def sync_deal_positions(
        self, 
        deal: Deal, 
        deal_context: dict[str, Any],
        sync_session_id: uuid.UUID | None = None
    ) -> dict[str, int]:
        """
        Synchronize all positions for a deal using simplified logic.
        
        NEW LOGIC:
        1. For each position from parser: UPSERT by hash_key
        2. DELETE positions not present in parser data
        
        Args:
            deal: Deal object from parser with all positions
            deal_context: Deal context for denormalization
            sync_session_id: Sync session ID for audit
            
        Returns:
            Dict with sync statistics: {'created': 0, 'updated': 0, 'deleted': 0}
        """
        stats = {'created': 0, 'updated': 0, 'deleted': 0}
        
        deal_key = deal_context.get("deal_key", "")
        logger.info(f"🔄 Starting simplified position sync for deal {deal_key} with {len(deal.items)} positions")
        
        # Step 1: UPSERT each position from parser
        parser_hash_keys = set()
        for item in deal.items:
            hash_key = str(item.get_full_hash_key(deal_key))
            parser_hash_keys.add(hash_key)
            
            result = await self._upsert_position(item, deal_context, sync_session_id)
            stats[result] += 1
        
        # Step 2: DELETE positions that are no longer in parser data
        deleted_count = await self._delete_removed_positions(
            deal.id, parser_hash_keys, sync_session_id
        )
        stats['deleted'] += deleted_count
        
        logger.info(f"✅ Simplified position sync completed for deal {deal_key}: {stats}")
        return stats

    async def _upsert_position(
        self, 
        item: DealItem, 
        deal_context: dict[str, Any],
        sync_session_id: uuid.UUID | None = None
    ) -> str:
        """
        UPSERT single position using hash_key.
        
        SIMPLIFIED LOGIC:
        1. Prepare position data
        2. Use PostgreSQL UPSERT (INSERT ... ON CONFLICT DO UPDATE)
        3. Return 'created' or 'updated' based on conflict
        
        Returns:
            'created' or 'updated'
        """
        deal_key = deal_context.get("deal_key", "")
        hash_key = str(item.get_full_hash_key(deal_key))
        
        # Prepare position data
        position_data = self._prepare_position_data(item, deal_context)
        
        # Check if position already exists
        existing = await self.session.execute(
            select(ReadModelPosition).where(ReadModelPosition.hash_key == hash_key)
        )
        exists = existing.scalar_one_or_none() is not None
        
        # UPSERT logic using PostgreSQL ON CONFLICT
        stmt = insert(ReadModelPosition).values(**position_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['hash_key'],
            set_={
                # Update all fields except id, hash_key
                'deal_id': stmt.excluded.deal_id,
                'deal_key': stmt.excluded.deal_key,
                'position_number': stmt.excluded.position_number,
                'product_name': stmt.excluded.product_name,
                'supplier_name': stmt.excluded.supplier_name,
                'pickup_date': stmt.excluded.pickup_date,
                'quantity': stmt.excluded.quantity,
                'purchase_price_amount': stmt.excluded.purchase_price_amount,
                'sale_price_amount': stmt.excluded.sale_price_amount,
                'revenue_amount': stmt.excluded.revenue_amount,
                'margin_amount': stmt.excluded.margin_amount,
                'cost_amount': stmt.excluded.cost_amount,
                'client_name': stmt.excluded.client_name,
                'period_month': stmt.excluded.period_month,
                'period_year': stmt.excluded.period_year,
                'updated_at': stmt.excluded.updated_at,
            }
        )
        
        await self.session.execute(stmt)
        await self.session.commit()
        
        if exists:
            logger.debug(f"🔄 Updated position {hash_key}")
            return 'updated'
        else:
            logger.debug(f"➕ Created position {hash_key}")
            return 'created'

    async def _delete_removed_positions(
        self, 
        deal_id: uuid.UUID,
        parser_hash_keys: set[str],
        sync_session_id: uuid.UUID | None = None
    ) -> int:
        """
        DELETE positions that exist in DB but not in parser data.
        
        SIMPLIFIED LOGIC (hard delete):
        1. Find all positions for this deal_id
        2. Delete those whose hash_key is not in parser data
        
        Args:
            deal_id: Deal UUID 
            parser_hash_keys: Set of hash_keys from parser
            sync_session_id: Sync session ID for audit
            
        Returns:
            Number of deleted positions
        """
        # Find all positions for this deal
        existing_positions = await self.session.execute(
            select(ReadModelPosition).where(ReadModelPosition.deal_id == deal_id)
        )
        
        positions_to_delete = []
        for position in existing_positions.scalars():
            if position.hash_key not in parser_hash_keys:
                positions_to_delete.append(position.hash_key)
        
        # Hard delete positions that are no longer in parser data
        if positions_to_delete:
            await self.session.execute(
                delete(ReadModelPosition).where(
                    ReadModelPosition.hash_key.in_(positions_to_delete)
                )
            )
            
            logger.info(f"🗑️ Deleted {len(positions_to_delete)} removed positions for deal {deal_id}")
            for hash_key in positions_to_delete:
                logger.debug(f"🗑️ Deleted position {hash_key}")
        
        return len(positions_to_delete)

    def _prepare_position_data(self, item: DealItem, deal_context: dict[str, Any]) -> dict[str, Any]:
        """Prepare position data for database insertion."""
        deal_key = deal_context.get("deal_key", "")
        
        return {
            "id": item.id,
            "deal_id": item.deal_id,
            "deal_key": deal_key,
            # Item info with position number and full hash key
            "position_number": item.position_number if item.position_number is not None else 1,
            "hash_key": str(item.get_full_hash_key(deal_key)),
            "product_name": item.product_name,
            "supplier_name": item.supplier_name,
            "pickup_date": item.pickup_date,
            # Quantities and pricing
            "quantity": item.quantity,
            "purchase_price_amount": item.purchase_price.amount if item.purchase_price else None,
            "sale_price_amount": item.sale_price.amount if item.sale_price else None,
            "revenue_amount": item.revenue.amount if item.revenue else None,
            "margin_amount": item.margin.amount if item.margin else None,
            "cost_amount": item.cost.amount if item.cost else None,
            # Deal context (denormalized)
            "client_name": deal_context.get("client_name", ""),
            "period_month": deal_context.get("period_month", ""),
            "period_year": deal_context.get("period_year", ""),
        }

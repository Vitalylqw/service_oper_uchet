"""
Position Synchronization Logic for ReadModelBuilder.

Implements correct position synchronization logic:
1. Version-based position updates using hash_key comparison
2. Deal-level position cleanup for removed positions
3. Soft-delete approach with is_active flag

Author: System Architect
Date: 2025-01-20
"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models import Deal, DealItem
from ..database.models import ReadModelPosition


class PositionSyncLogic:
    """
    Encapsulates correct position synchronization logic.
    
    Key principles:
    1. Use hash_key for position identification (not UUID)
    2. Version-based updates with soft delete
    3. Deal-level cleanup of removed positions
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
        Synchronize all positions for a deal using correct versioning logic.
        
        Steps:
        1. For each position from parser: version control by hash_key
        2. For deal: deactivate positions not present in parser data
        
        Args:
            deal: Deal object from parser with all positions
            deal_context: Deal context for denormalization
            sync_session_id: Sync session ID for audit
            
        Returns:
            Dict with sync statistics: {'created': 0, 'updated': 0, 'deactivated': 0}
        """
        stats = {'created': 0, 'updated': 0, 'deactivated': 0}
        
        deal_key = deal_context.get("deal_key", "")
        logger.info(f"🔄 Starting position sync for deal {deal_key} with {len(deal.items)} positions")
        
        # Step 1: Process each position from parser
        parser_hash_keys = set()
        for item in deal.items:
            hash_key = str(item.get_full_hash_key(deal_key))
            parser_hash_keys.add(hash_key)
            
            result = await self._sync_single_position(item, deal_context, sync_session_id)
            stats[result] += 1
        
        # Step 2: Deactivate positions that are no longer in parser data
        # Find all active positions for this deal_hash_key (not deal UUID!)
        deactivated_count = await self._deactivate_removed_positions(
            deal_key, parser_hash_keys, sync_session_id
        )
        stats['deactivated'] += deactivated_count
        
        logger.info(f"✅ Position sync completed for deal {deal_key}: {stats}")
        return stats

    async def _sync_single_position(
        self, 
        item: DealItem, 
        deal_context: dict[str, Any],
        sync_session_id: uuid.UUID | None = None
    ) -> str:
        """
        Sync single position using hash_key comparison.
        
        Logic:
        1. Check if position with this hash_key exists and is active
        2. If exists: create new version, deactivate old
        3. If not exists: create new position
        
        Returns:
            'created' or 'updated'
        """
        deal_key = deal_context.get("deal_key", "")
        hash_key = str(item.get_full_hash_key(deal_key))
        
        # Check for existing active position with same hash_key
        existing_active = await self.session.execute(
            select(ReadModelPosition)
            .where(
                ReadModelPosition.hash_key == hash_key,
                ReadModelPosition.is_active == True
            )
        )
        existing_position = existing_active.scalar_one_or_none()
        
        # Prepare position data
        position_data = self._prepare_position_data(item, deal_context)
        
        if existing_position:
            # UPDATE LOGIC: Create new version, deactivate old
            logger.debug(f"🔄 Updating position {hash_key}: version {existing_position.version} -> {existing_position.version + 1}")
            
            # Step 1: Deactivate old version
            await self.session.execute(
                update(ReadModelPosition)
                .where(ReadModelPosition.id == existing_position.id)
                .values(
                    is_active=False,
                    version=existing_position.version + 1
                )
            )
            
            # Step 2: Create new active version
            position_data.update({
                "version": existing_position.version + 2,
                "is_active": True,
            })
            
            stmt = insert(ReadModelPosition).values(**position_data)
            await self.session.execute(stmt)
            
            return 'updated'
        else:
            # CREATE LOGIC: New position
            logger.debug(f"➕ Creating new position {hash_key}")
            
            position_data.update({
                "version": 1,
                "is_active": True,
            })
            
            stmt = insert(ReadModelPosition).values(**position_data)
            await self.session.execute(stmt)
            
            return 'created'

    async def _deactivate_removed_positions(
        self, 
        deal_key: str, 
        parser_hash_keys: set[str],
        sync_session_id: uuid.UUID | None = None
    ) -> int:
        """
        Deactivate positions that exist in DB but not in parser data.
        
        This handles the case when positions are removed from Excel.
        
        Args:
            deal_key: Deal hash key (not UUID!)
            parser_hash_keys: Set of hash_keys from parser
            sync_session_id: Sync session ID for audit
            
        Returns:
            Number of deactivated positions
        """
        # Find all active positions for this deal_key
        active_positions = await self.session.execute(
            select(ReadModelPosition)
            .where(
                ReadModelPosition.deal_key == deal_key,
                ReadModelPosition.is_active == True
            )
        )
        
        positions_to_deactivate = []
        for position in active_positions.scalars():
            if position.hash_key not in parser_hash_keys:
                positions_to_deactivate.append(position)
        
        # Deactivate positions that are no longer in parser data
        deactivated_count = 0
        for position in positions_to_deactivate:
            logger.debug(f"🗑️ Deactivating removed position {position.hash_key}")
            
            await self.session.execute(
                update(ReadModelPosition)
                .where(ReadModelPosition.id == position.id)
                .values(
                    is_active=False,
                    version=position.version + 1
                )
            )
            deactivated_count += 1
        
        if deactivated_count > 0:
            logger.info(f"🗑️ Deactivated {deactivated_count} removed positions for deal {deal_key}")
        
        return deactivated_count

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
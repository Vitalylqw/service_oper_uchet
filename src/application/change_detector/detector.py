"""
Change Detection Service.

Implements algorithms for comparing Excel data with database state
and identifying changes for incremental synchronization.
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

from ...domain.interfaces import DealRepository
from ...domain.models import Deal, DealItem
from ...domain.value_objects import HashKey
from .models import (
    ChangeDetectionResult,
    ChangeType,
    EntityChange,
    EntityType,
    HashComparisonCache,
)


class ChangeDetectorService:
    """
    Service for detecting changes between Excel and database data.

    Uses hash-based comparison for performance with fallback to detailed comparison.
    Implements incremental change detection algorithms.
    """

    def __init__(self, deal_repository: DealRepository) -> None:
        """Initialize change detector with repository."""
        self.deal_repository = deal_repository
        self.hash_cache = HashComparisonCache()

    async def detect_changes(
        self, excel_deals: list[Deal], sync_period_months: int = 3
    ) -> ChangeDetectionResult:
        """
        Detect changes between Excel data and database.

        Args:
            excel_deals: List of deals from Excel parsing
            sync_period_months: Number of months to include in incremental sync

        Returns:
            ChangeDetectionResult with all detected changes
        """
        start_time = time.time()
        logger.info(f"Starting change detection for {len(excel_deals)} Excel deals")

        result = ChangeDetectionResult()
        result.total_excel_deals = len(excel_deals)
        result.total_excel_items = sum(len(deal.items) for deal in excel_deals)

        try:
            # Get database deals for comparison
            db_deals = await self._get_database_deals(excel_deals, sync_period_months)
            result.total_db_deals = len(db_deals)
            result.total_db_items = sum(len(deal.items) for deal in db_deals)

            logger.info(f"Comparing with {len(db_deals)} database deals")

            # Build hash caches for fast comparison
            excel_hashes = self._build_entity_hash_cache(excel_deals)
            db_hashes = self._build_entity_hash_cache(db_deals)

            # Detect deal changes
            deal_changes = await self._detect_deal_changes(
                excel_deals, db_deals, excel_hashes, db_hashes
            )

            # Detect item changes
            item_changes = await self._detect_item_changes(
                excel_deals, db_deals, excel_hashes, db_hashes
            )

            # Categorize changes
            all_changes = deal_changes + item_changes
            result.insertions = [c for c in all_changes if c.change_type == ChangeType.INSERT]
            result.updates = [c for c in all_changes if c.change_type == ChangeType.UPDATE]
            result.deletions = [c for c in all_changes if c.change_type == ChangeType.DELETE]

            # Performance metrics
            result.comparison_duration_seconds = time.time() - start_time
            result.hash_comparison_count = len(excel_hashes.entity_hashes) + len(
                db_hashes.entity_hashes
            )
            result.detailed_comparison_count = len([c for c in all_changes if c.has_field_changes])

            logger.info(f"Change detection completed in {result.comparison_duration_seconds:.2f}s")
            logger.info(
                f"Found {result.total_changes} changes: "
                f"{result.insertion_count} insertions, "
                f"{result.update_count} updates, "
                f"{result.deletion_count} deletions"
            )

            return result

        except Exception as e:
            logger.error(f"Change detection failed: {e}")
            raise

    async def _get_database_deals(
        self, excel_deals: list[Deal], sync_period_months: int
    ) -> list[Deal]:
        """
        Get relevant database deals for comparison.

        For incremental sync, only loads deals from recent periods.
        """
        try:
            # Extract unique periods from Excel deals
            excel_periods = set()
            for deal in excel_deals:
                period_key = f"{deal.period.year}-{deal.period.month}"
                excel_periods.add(period_key)

            logger.debug(f"Excel periods: {excel_periods}")

            # Load database deals for these periods
            db_deals = []
            for period_key in excel_periods:
                year, month = period_key.split("-")
                period_deals = await self.deal_repository.find_by_period(month, year)
                db_deals.extend(period_deals)

            logger.debug(f"Loaded {len(db_deals)} database deals for comparison")
            return db_deals

        except Exception as e:
            logger.error(f"Failed to get database deals: {e}")
            return []

    def _build_entity_hash_cache(self, deals: list[Deal]) -> HashComparisonCache:
        """
        Build hash cache for fast entity comparison.

        Creates hashes for both deals and their items.
        """
        cache = HashComparisonCache()

        for deal in deals:
            # Hash deal
            deal_hash = self._calculate_deal_hash(deal)
            cache.set_hash(deal.deal_key, deal_hash)

            # Hash items
            for item in deal.items:
                item_key = self._get_item_key(deal, item)
                item_hash = self._calculate_item_hash(item)
                cache.set_hash(item_key, item_hash)

        logger.debug(f"Built hash cache with {cache.entity_count} entities")
        return cache

    async def _detect_deal_changes(
        self,
        excel_deals: list[Deal],
        db_deals: list[Deal],
        excel_hashes: HashComparisonCache,
        db_hashes: HashComparisonCache,
    ) -> list[EntityChange]:
        """Detect changes to deals."""
        changes = []

        # Build lookup maps
        db_deals_map = {deal.deal_key: deal for deal in db_deals}
        excel_deals_map = {deal.deal_key: deal for deal in excel_deals}

        # Find insertions and updates
        for excel_deal in excel_deals:
            deal_key = excel_deal.deal_key
            excel_hash = excel_hashes.get_hash(deal_key)

            if deal_key not in db_deals_map:
                # New deal - INSERT
                change = EntityChange(
                    change_type=ChangeType.INSERT,
                    entity_type=EntityType.DEAL,
                    entity_key=deal_key,
                    new_entity=excel_deal,
                    new_hash=excel_hash,
                )
                changes.append(change)
                logger.debug(f"Deal INSERT: {deal_key}")

            else:
                # Existing deal - check for changes
                db_deal = db_deals_map[deal_key]
                db_hash = db_hashes.get_hash(deal_key)

                if excel_hash != db_hash:
                    # Deal updated - detailed comparison
                    field_changes = self._compare_deal_fields(db_deal, excel_deal)

                    change = EntityChange(
                        change_type=ChangeType.UPDATE,
                        entity_type=EntityType.DEAL,
                        entity_key=deal_key,
                        field_changes=field_changes,
                        old_entity=db_deal,
                        new_entity=excel_deal,
                        old_hash=db_hash,
                        new_hash=excel_hash,
                    )
                    changes.append(change)
                    logger.debug(f"Deal UPDATE: {deal_key} ({len(field_changes)} fields)")

        # Find deletions
        for db_deal in db_deals:
            deal_key = db_deal.deal_key
            if deal_key not in excel_deals_map:
                # Deal deleted - DELETE (soft delete)
                db_hash = db_hashes.get_hash(deal_key)

                change = EntityChange(
                    change_type=ChangeType.DELETE,
                    entity_type=EntityType.DEAL,
                    entity_key=deal_key,
                    old_entity=db_deal,
                    old_hash=db_hash,
                )
                changes.append(change)
                logger.debug(f"Deal DELETE: {deal_key}")

        return changes

    async def _detect_item_changes(
        self,
        excel_deals: list[Deal],
        db_deals: list[Deal],
        excel_hashes: HashComparisonCache,
        db_hashes: HashComparisonCache,
    ) -> list[EntityChange]:
        """Detect changes to deal items."""
        changes = []

        # Build item lookup maps
        db_items_map = {}
        excel_items_map = {}

        for deal in db_deals:
            for item in deal.items:
                item_key = self._get_item_key(deal, item)
                db_items_map[item_key] = (deal, item)

        for deal in excel_deals:
            for item in deal.items:
                item_key = self._get_item_key(deal, item)
                excel_items_map[item_key] = (deal, item)

        # Find insertions and updates
        for item_key, (_excel_deal, excel_item) in excel_items_map.items():
            excel_hash = excel_hashes.get_hash(item_key)

            if item_key not in db_items_map:
                # New item - INSERT
                change = EntityChange(
                    change_type=ChangeType.INSERT,
                    entity_type=EntityType.DEAL_ITEM,
                    entity_key=item_key,
                    new_entity=excel_item,
                    new_hash=excel_hash,
                )
                changes.append(change)
                logger.debug(f"Item INSERT: {item_key}")

            else:
                # Existing item - check for changes
                db_deal, db_item = db_items_map[item_key]
                db_hash = db_hashes.get_hash(item_key)

                if excel_hash != db_hash:
                    # Item updated - detailed comparison
                    field_changes = self._compare_item_fields(db_item, excel_item)

                    change = EntityChange(
                        change_type=ChangeType.UPDATE,
                        entity_type=EntityType.DEAL_ITEM,
                        entity_key=item_key,
                        field_changes=field_changes,
                        old_entity=db_item,
                        new_entity=excel_item,
                        old_hash=db_hash,
                        new_hash=excel_hash,
                    )
                    changes.append(change)
                    logger.debug(f"Item UPDATE: {item_key} ({len(field_changes)} fields)")

        # Find deletions
        for item_key, (_db_deal, db_item) in db_items_map.items():
            if item_key not in excel_items_map:
                # Item deleted - DELETE (soft delete)
                db_hash = db_hashes.get_hash(item_key)

                change = EntityChange(
                    change_type=ChangeType.DELETE,
                    entity_type=EntityType.DEAL_ITEM,
                    entity_key=item_key,
                    old_entity=db_item,
                    old_hash=db_hash,
                )
                changes.append(change)
                logger.debug(f"Item DELETE: {item_key}")

        return changes

    def _calculate_deal_hash(self, deal: Deal) -> str:
        """Calculate hash for deal entity."""
        # Build normalized dictionary for hashing
        deal_dict = {
            "client_name": deal.client_name,
            "invoice_info": deal.invoice_info,
            "invoice_number": deal.invoice_number,
            "invoice_date": deal.invoice_date,
            "period": f"{deal.period.year}-{deal.period.month}",
            "is_shipped": deal.is_shipped.value if deal.is_shipped else None,
            "is_paid": deal.is_paid.value if deal.is_paid else None,
            "upd_number": deal.upd_number,
            "seller": deal.seller,
            "total_revenue": str(deal.total_revenue.amount) if deal.total_revenue else None,
            "total_margin": str(deal.total_margin.amount) if deal.total_margin else None,
            "total_cost": str(deal.total_cost.amount) if deal.total_cost else None,
            "kickback_amount": str(deal.kickback_amount.amount) if deal.kickback_amount else None,
        }

        hash_key = HashKey.from_dict(deal_dict)
        return hash_key.value

    def _calculate_item_hash(self, item: DealItem) -> str:
        """Calculate hash for deal item entity."""
        # Build normalized dictionary for hashing
        item_dict = {
            "product_name": item.product_name,
            "supplier_name": item.supplier_name,
            "pickup_date": item.pickup_date,
            "quantity": str(item.quantity) if item.quantity else None,
            "purchase_price": str(item.purchase_price.amount) if item.purchase_price else None,
            "sale_price": str(item.sale_price.amount) if item.sale_price else None,
            "revenue": str(item.revenue.amount) if item.revenue else None,
            "margin": str(item.margin.amount) if item.margin else None,
            "cost": str(item.cost.amount) if item.cost else None,
        }

        hash_key = HashKey.from_dict(item_dict)
        return hash_key.value

    def _get_item_key(self, deal: Deal, item: DealItem) -> str:
        """Generate unique key for deal item."""
        return f"{deal.deal_key}|{item.product_name}|{item.supplier_name or ''}"

    def _compare_deal_fields(self, old_deal: Deal, new_deal: Deal) -> dict[str, dict[str, Any]]:
        """Compare deal fields and return changes."""
        changes = {}

        # Define fields to compare
        fields_to_compare = [
            "client_name",
            "invoice_info",
            "invoice_number",
            "invoice_date",
            "is_shipped",
            "is_paid",
            "upd_number",
            "seller",
        ]

        for field in fields_to_compare:
            old_value = getattr(old_deal, field, None)
            new_value = getattr(new_deal, field, None)

            # Convert Status enums to string for comparison
            if hasattr(old_value, "value"):
                old_value = old_value.value
            if hasattr(new_value, "value"):
                new_value = new_value.value

            if old_value != new_value:
                changes[field] = {"old_value": old_value, "new_value": new_value}

        # Compare money fields
        money_fields = ["total_revenue", "total_margin", "total_cost", "kickback_amount"]
        for field in money_fields:
            old_money = getattr(old_deal, field, None)
            new_money = getattr(new_deal, field, None)

            old_amount = str(old_money.amount) if old_money else None
            new_amount = str(new_money.amount) if new_money else None

            if old_amount != new_amount:
                changes[field] = {"old_value": old_amount, "new_value": new_amount}

        return changes

    def _compare_item_fields(
        self, old_item: DealItem, new_item: DealItem
    ) -> dict[str, dict[str, Any]]:
        """Compare item fields and return changes."""
        changes = {}

        # Define fields to compare
        fields_to_compare = ["product_name", "supplier_name", "pickup_date"]

        for field in fields_to_compare:
            old_value = getattr(old_item, field, None)
            new_value = getattr(new_item, field, None)

            if old_value != new_value:
                changes[field] = {"old_value": old_value, "new_value": new_value}

        # Compare quantity
        old_qty = str(old_item.quantity) if old_item.quantity else None
        new_qty = str(new_item.quantity) if new_item.quantity else None

        if old_qty != new_qty:
            changes["quantity"] = {"old_value": old_qty, "new_value": new_qty}

        # Compare money fields
        money_fields = ["purchase_price", "sale_price", "revenue", "margin", "cost"]
        for field in money_fields:
            old_money = getattr(old_item, field, None)
            new_money = getattr(new_item, field, None)

            old_amount = str(old_money.amount) if old_money else None
            new_amount = str(new_money.amount) if new_money else None

            if old_amount != new_amount:
                changes[field] = {"old_value": old_amount, "new_value": new_amount}

        return changes

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for monitoring."""
        return {
            "hash_cache_entities": self.hash_cache.entity_count,
        }

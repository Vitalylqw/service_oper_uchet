"""
Real Deal Service for FastAPI endpoints.

Wrapper around DealRepositoryImplementation providing API-compatible interface
for deal operations with real database integration.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from loguru import logger

from src.infrastructure.database.repositories import DealRepositoryImplementation


class RealDealService:
    """
    Real deal service for API endpoints.

    Provides same interface as MockDealService but with real database operations
    through DealRepositoryImplementation.
    """

    def __init__(self, deal_repository: DealRepositoryImplementation) -> None:
        """Initialize real deal service with repository."""
        self.deal_repository = deal_repository
        logger.debug("RealDealService initialized")



    async def get_deals_paginated(self, page: int, limit: int, filters: dict) -> dict:
        """
        Get paginated deals with filters from real database.

        Args:
            page: Page number (1-based)
            limit: Number of items per page
            filters: Filter parameters (client_name, period, etc.)

        Returns:
            dict: Paginated deals response compatible with API models
        """
        try:
            logger.info(f"Getting paginated deals: page={page}, limit={limit}, filters={filters}")

            # Get deals from database through repository
            result = await self.deal_repository.find_all_paginated(page, limit, filters)

            # Convert read model deals to API format
            api_deals = []
            for deal_model in result["items"]:
                api_deal = self._read_model_to_api_format(deal_model)
                api_deals.append(api_deal)

            return {
                "items": api_deals,
                "total": result["total"],
                "page": result["page"],
                "limit": result["limit"],
                "pages": result["pages"],
            }

        except Exception as e:
            logger.error(f"Failed to get paginated deals: {e}")
            # Return empty result to prevent API failures during development
            return {
                "items": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "pages": 0,
            }

    async def get_deal_by_id(self, deal_id: str) -> dict | None:
        """
        Get deal by ID from real database.

        Args:
            deal_id: Deal UUID as string

        Returns:
            dict: Deal data in API format or None if not found
        """
        try:
            logger.info(f"Getting deal by ID: {deal_id}")

            # Convert string ID to UUID
            try:
                deal_uuid = uuid.UUID(deal_id)
                logger.debug(f"Converted to UUID: {deal_uuid}")
            except ValueError:
                logger.warning(f"Invalid UUID format: {deal_id}")
                return None

            # Get deal from repository
            logger.debug(f"Calling repository.get_by_id({deal_uuid})")
            deal = await self.deal_repository.get_by_id(deal_uuid)

            if not deal:
                logger.debug(f"Deal not found: {deal_id}")
                return None

            logger.debug(f"Deal found: {deal.id}, client: {deal.client_name}")
            logger.debug(f"Deal period type: {type(deal.period)}, value: {deal.period}")

            # Convert to API format
            logger.debug("Converting to API format...")
            api_deal = await self._domain_deal_to_api_format(deal, include_items=True)
            logger.debug(f"API conversion successful, deal_key: {deal.deal_key}")
            return api_deal

        except Exception as e:
            logger.error(f"Failed to get deal by ID {deal_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    async def get_deals_by_client(self, client_name: str) -> list[dict]:
        """
        Get deals by client name from real database.

        Args:
            client_name: Client name to search for

        Returns:
            list[dict]: List of deals in API format
        """
        try:
            logger.info(f"Getting deals by client: {client_name}")

            deals = await self.deal_repository.find_by_client(client_name)

            # Convert to API format
            api_deals = []
            for deal in deals:
                api_deal = await self._domain_deal_to_api_format(deal)
                api_deals.append(api_deal)

            logger.debug(f"Found {len(api_deals)} deals for client '{client_name}'")
            return api_deals

        except Exception as e:
            logger.error(f"Failed to get deals by client {client_name}: {e}")
            return []

    async def get_deals_by_period(self, period_month: str, period_year: str) -> list[dict]:
        """
        Get deals by period from real database.

        Args:
            period_month: Month name or number
            period_year: Year as string

        Returns:
            list[dict]: List of deals in API format
        """
        try:
            logger.info(f"Getting deals by period: {period_month} {period_year}")

            deals = await self.deal_repository.find_by_period(period_month, period_year)

            # Convert to API format
            api_deals = []
            for deal in deals:
                api_deal = await self._domain_deal_to_api_format(deal)
                api_deals.append(api_deal)

            logger.debug(f"Found {len(api_deals)} deals for period {period_month} {period_year}")
            return api_deals

        except Exception as e:
            logger.error(f"Failed to get deals by period {period_month} {period_year}: {e}")
            return []

    async def _domain_deal_to_api_format(self, deal, include_items: bool = False) -> dict:
        """
        Convert domain Deal model to API format.

        Args:
            deal: Domain Deal model
            include_items: Whether to include deal items

        Returns:
            dict: Deal data in API-compatible format
        """
        try:
            logger.debug(f"Converting deal {deal.id} to API format")
            logger.debug(f"Deal period: {deal.period}, type: {type(deal.period)}")

            # Basic deal information
            api_deal = {
                "id": str(deal.id),
                "deal_key": deal.deal_key or "",
                "client_name": deal.client_name or "",
                "seller": deal.seller or "",
                "invoice_info": deal.invoice_info or "",
                "invoice_number": deal.invoice_number or "",
                "invoice_date": deal.invoice_date or None,
                "upd_number": deal.upd_number or "",
                "upd_date": getattr(deal, 'upd_date', None),
                "is_shipped": self._status_to_bool(deal.is_shipped),
                "is_paid": self._status_to_bool(deal.is_paid),
                "created_at": getattr(deal, 'created_at', datetime.now(timezone.utc)),
                "updated_at": getattr(deal, 'updated_at', datetime.now(timezone.utc)) or datetime.now(timezone.utc),
            }

            # Financial information
            if deal.total_revenue:
                api_deal["revenue"] = deal.total_revenue.amount
            else:
                api_deal["revenue"] = Decimal("0.00")

            if deal.total_margin:
                api_deal["margin"] = deal.total_margin.amount
            else:
                api_deal["margin"] = Decimal("0.00")

            if deal.total_cost:
                api_deal["cost"] = deal.total_cost.amount
            else:
                api_deal["cost"] = Decimal("0.00")

            # Item count
            api_deal["items_count"] = len(deal.items)

            # Include items if requested
            if include_items:
                items = []
                for item in deal.items:
                    api_item = {
                        "id": str(item.id),
                        "product_name": item.product_name or "",
                        "quantity": item.quantity or Decimal("0"),
                        "purchase_price": item.purchase_price.amount if item.purchase_price else Decimal("0"),
                        "sale_price": item.sale_price.amount if item.sale_price else Decimal("0"),
                        "supplier_name": item.supplier_name or "",
                        "pickup_date": item.pickup_date or "",
                    }
                    items.append(api_item)
                api_deal["items"] = items

            return api_deal

        except Exception as e:
            logger.error(f"Error converting deal to API format: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _status_to_bool(self, status) -> bool:
        """Convert domain Status to boolean for API compatibility."""

        if status is None:
            return False

        if hasattr(status, 'value'):
            # Status enum
            return status.value in ['completed', 'paid', 'shipped', 'да', 'yes', True]

        # String status
        if isinstance(status, str):
            return status.lower() in ['completed', 'paid', 'shipped', 'да', 'yes', 'true']

        # Boolean status
        return bool(status)

    def _read_model_to_api_format(self, read_model) -> dict:
        """
        Convert ReadModel to API format.

        Args:
            read_model: ReadModelDeal object from database

        Returns:
            dict: Deal data in API-compatible format
        """
        # Convert string status values to boolean for API
        is_shipped = read_model.is_shipped in ["shipped", "completed"]
        is_paid = read_model.is_paid in ["paid", "completed"]

        return {
            "id": str(read_model.id),
            "deal_key": read_model.deal_key or "",
            "client_name": read_model.client_name or "",
                            "seller": read_model.seller or "",
            "invoice_number": read_model.invoice_number or "",
            "invoice_date": read_model.invoice_date or "",
            "revenue": str(read_model.total_revenue_amount or "0.00"),
            "margin": str(read_model.total_margin_amount or "0.00"),
            "is_shipped": is_shipped,
            "is_paid": is_paid,
            "items_count": read_model.items_count or 0,
            "updated_at": read_model.updated_at or read_model.created_at,
        }

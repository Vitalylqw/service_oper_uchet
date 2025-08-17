"""
Deal API models.

Contains Pydantic models for deal-related API requests and responses.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .common import FilterParams


class DealItemResponse(BaseModel):
    """Deal item response model."""
    
    id: str
    product_name: str
    supplier_name: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal
    cost_price: Decimal | None = None
    supplier_pickup_date: date | None = None


class DealResponse(BaseModel):
    """Deal response model."""
    
    id: str
    deal_key: str
    
    # Client information
    client_name: str
    seller: str
    
    # Document information
    invoice_number: str
    invoice_date: date | None = None
    upd_number: str | None = None
    upd_date: date | None = None
    
    # Financial information
    revenue: Decimal
    margin: Decimal
    cost: Decimal | None = None
    
    # Status information
    is_shipped: bool
    is_paid: bool
    
    # Period information
    period_month: str
    period_year: str
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    
    # Related items
    items: list[DealItemResponse] = Field(default_factory=list)


class DealSummary(BaseModel):
    """Deal summary for list views."""
    
    id: str
    deal_key: str
    client_name: str
    seller: str
    invoice_number: str
    invoice_date: date | None = None
    revenue: Decimal
    margin: Decimal
    is_shipped: bool
    is_paid: bool

    items_count: int
    updated_at: datetime

    @field_validator('invoice_date', mode='before')
    @classmethod
    def validate_invoice_date(cls, v):
        """Convert empty string to None for invoice_date."""
        if v == '' or v is None:
            return None
        
        # Handle string date format like '16.06.2025'
        if isinstance(v, str) and '.' in v:
            try:
                from datetime import datetime
                # Parse DD.MM.YYYY format
                return datetime.strptime(v, '%d.%m.%Y').date()
            except ValueError:
                # If parsing fails, return None
                return None
        
        return v

    @field_validator('revenue', 'margin', mode='before')
    @classmethod
    def validate_decimal_fields(cls, v):
        """Convert string decimals to Decimal objects."""
        if isinstance(v, str):
            return Decimal(v)
        return v


class DealFilters(FilterParams):
    """Deal-specific filter parameters."""
    
    client_name: str | None = Field(default=None, description="Filter by client name")
    seller: str | None = Field(default=None, description="Filter by seller")
    period_month: str | None = Field(default=None, description="Filter by month")
    period_year: str | None = Field(default=None, description="Filter by year")
    is_shipped: bool | None = Field(default=None, description="Filter by shipping status")
    is_paid: bool | None = Field(default=None, description="Filter by payment status")
    date_from: date | None = Field(default=None, description="Filter by date from")
    date_to: date | None = Field(default=None, description="Filter by date to")
    min_revenue: Decimal | None = Field(default=None, description="Minimum revenue")
    max_revenue: Decimal | None = Field(default=None, description="Maximum revenue")


class DealStatsResponse(BaseModel):
    """Deal statistics response."""
    
    total_deals: int
    total_revenue: Decimal
    total_margin: Decimal
    shipped_deals: int
    paid_deals: int
    avg_revenue: Decimal
    avg_profitability: Decimal
    unpaid_deals: int
    unshipped_deals: int
    top_clients: list[dict[str, str | Decimal]]
    revenue_by_month: list[dict[str, str | Decimal]] 
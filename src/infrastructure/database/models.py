"""
SQLAlchemy models for Event Store and Read Models.

Contains models for Event Sourcing pattern and CQRS read models.
Works with both PostgreSQL and SQLite databases.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.

    Uses PostgreSQL's UUID type when available,
    otherwise uses CHAR(32) for SQLite.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


class JSONType(TypeDecorator):
    """
    Platform-independent JSON type.

    Uses PostgreSQL's JSONB when available,
    otherwise uses standard JSON for SQLite.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())


Base = declarative_base()


class EventStoreModel(Base):
    """
    Event store table for Event Sourcing.

    Stores all domain events with JSON data and metadata.
    Compatible with both PostgreSQL and SQLite.
    """

    __tablename__ = "event_store"

    # Primary fields
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[uuid.UUID] = mapped_column(GUID(), default=uuid.uuid4, unique=True)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Event details
    event_type: Mapped[str] = mapped_column(String(200), nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    event_data: Mapped[dict] = mapped_column(JSONType(), nullable=False)
    event_metadata: Mapped[dict] = mapped_column(JSONType(), nullable=True)

    # Timing and sequencing
    sequence_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )

    # Indexes for performance (PostgreSQL-specific indexes will be created conditionally)
    __table_args__ = (
        Index("ix_event_store_aggregate_id", "aggregate_id"),
        Index("ix_event_store_event_type", "event_type"),
        Index("ix_event_store_created_at", "created_at"),
        Index("ix_event_store_sequence", "sequence_number"),
        # Composite indexes for common queries
        Index("ix_event_store_aggregate_sequence", "aggregate_id", "sequence_number"),
        Index("ix_event_store_type_created", "event_type", "created_at"),
    )


class ReadModelDeal(Base):
    """
    Read model for deals - optimized for queries.

    Denormalized view of deal data for fast reading.
    Compatible with both PostgreSQL and SQLite.
    """

    __tablename__ = "read_deals"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True)

    # Business key
    deal_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hash_key: Mapped[str] = mapped_column(String(32), nullable=False)

    # Basic deal info
    client_name: Mapped[str] = mapped_column(String(500), nullable=False)
    invoice_info: Mapped[str] = mapped_column(String(500), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=True)
    invoice_date: Mapped[str] = mapped_column(String(20), nullable=True)

    # Period
    period_month: Mapped[str] = mapped_column(String(20), nullable=False)
    period_year: Mapped[str] = mapped_column(String(4), nullable=False)
    period_full_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Status fields
    is_shipped: Mapped[str] = mapped_column(String(20), nullable=True)
    is_paid: Mapped[str] = mapped_column(String(20), nullable=True)

    # Document fields
    upd_number: Mapped[str] = mapped_column(String(100), nullable=True)
    seller: Mapped[str] = mapped_column(String(300), nullable=True)

    # Financial fields (stored as NUMERIC for precision)
    total_revenue_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=True)
    total_revenue_currency: Mapped[str] = mapped_column(String(3), default="RUB")

    total_margin_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=True)
    total_margin_currency: Mapped[str] = mapped_column(String(3), default="RUB")

    total_cost_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=True)
    total_cost_currency: Mapped[str] = mapped_column(String(3), default="RUB")

    kickback_amount_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=True)
    kickback_amount_currency: Mapped[str] = mapped_column(String(3), default="RUB")

    # Aggregated fields
    items_count: Mapped[int] = mapped_column(Integer, default=0)
    total_quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=True)

    # System fields
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Indexes for common queries
    __table_args__ = (
        Index("ix_read_deals_client_name", "client_name"),
        Index("ix_read_deals_period", "period_year", "period_month"),
        Index("ix_read_deals_status", "is_shipped", "is_paid"),
        Index("ix_read_deals_seller", "seller"),
        Index("ix_read_deals_created_at", "created_at"),
        Index("ix_read_deals_hash_key", "hash_key"),
        # Full-text search support
        Index("ix_read_deals_search", "client_name", "invoice_info", "seller"),
    )


class ReadModelPosition(Base):
    """
    Read model for deal positions - optimized for queries.

    Denormalized view of deal items for fast reading.
    Compatible with both PostgreSQL and SQLite.
    """

    __tablename__ = "read_positions"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True)

    # Foreign key to deal
    deal_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    deal_key: Mapped[str] = mapped_column(String(255), nullable=False)

    # Item info
    position_key: Mapped[str] = mapped_column(String(500), nullable=False)
    hash_key: Mapped[str] = mapped_column(String(32), nullable=False)

    product_name: Mapped[str] = mapped_column(String(1000), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(500), nullable=True)
    pickup_date: Mapped[str] = mapped_column(String(50), nullable=True)

    # Quantities and pricing
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=True)

    purchase_price_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=True)
    purchase_price_currency: Mapped[str] = mapped_column(String(3), default="RUB")

    sale_price_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=True)
    sale_price_currency: Mapped[str] = mapped_column(String(3), default="RUB")

    revenue_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=True)
    revenue_currency: Mapped[str] = mapped_column(String(3), default="RUB")

    margin_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=True)
    margin_currency: Mapped[str] = mapped_column(String(3), default="RUB")

    cost_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=True)
    cost_currency: Mapped[str] = mapped_column(String(3), default="RUB")

    # Deal context (denormalized for fast queries)
    client_name: Mapped[str] = mapped_column(String(500), nullable=False)
    period_month: Mapped[str] = mapped_column(String(20), nullable=False)
    period_year: Mapped[str] = mapped_column(String(4), nullable=False)

    # System fields
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Indexes for common queries
    __table_args__ = (
        Index("ix_read_positions_deal_id", "deal_id"),
        Index("ix_read_positions_product_name", "product_name"),
        Index("ix_read_positions_supplier", "supplier_name"),
        Index("ix_read_positions_client", "client_name"),
        Index("ix_read_positions_period", "period_year", "period_month"),
        Index("ix_read_positions_hash_key", "hash_key"),
        # Composite indexes
        Index("ix_read_positions_deal_product", "deal_id", "product_name"),
        # Unique constraint for position key within deal
        Index("ix_read_positions_deal_position_key", "deal_id", "position_key", unique=True),
    )


class ReadModelAudit(Base):
    """
    Read model for audit trail - change history.

    Tracks all changes to deals and positions.
    Compatible with both PostgreSQL and SQLite.
    """

    __tablename__ = "read_audit"

    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # What changed
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # deal, position
    entity_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(500), nullable=False)

    # Change details
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)  # INSERT, UPDATE, DELETE
    field_name: Mapped[str] = mapped_column(String(100), nullable=True)
    old_value: Mapped[str] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=True)

    # Context
    sync_session_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)

    # Timing
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    # Indexes
    __table_args__ = (
        Index("ix_read_audit_entity", "entity_type", "entity_id"),
        Index("ix_read_audit_session", "sync_session_id"),
        Index("ix_read_audit_changed_at", "changed_at"),
        Index("ix_read_audit_change_type", "change_type"),
    )


class ReadModelStats(Base):
    """
    Read model for statistics and metrics.

    Pre-aggregated statistics for dashboard and reporting.
    Compatible with both PostgreSQL and SQLite.
    """

    __tablename__ = "read_stats"

    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Stat identity
    stat_type: Mapped[str] = mapped_column(String(50), nullable=False)  # daily, monthly, yearly
    stat_date: Mapped[str] = mapped_column(String(20), nullable=False)  # 2024-01, 2024-01-15

    # Aggregation dimensions
    dimension_type: Mapped[str] = mapped_column(
        String(50), nullable=True
    )  # client, seller, supplier
    dimension_value: Mapped[str] = mapped_column(String(500), nullable=True)

    # Metrics
    deals_count: Mapped[int] = mapped_column(Integer, default=0)
    positions_count: Mapped[int] = mapped_column(Integer, default=0)

    total_revenue: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_margin: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=0)

    # Quality metrics
    shipped_deals_count: Mapped[int] = mapped_column(Integer, default=0)
    paid_deals_count: Mapped[int] = mapped_column(Integer, default=0)

    # System fields
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    # Indexes
    __table_args__ = (
        Index("ix_read_stats_type_date", "stat_type", "stat_date"),
        Index("ix_read_stats_dimension", "dimension_type", "dimension_value"),
        Index("ix_read_stats_calculated_at", "calculated_at"),
        # Unique constraint for preventing duplicates
        Index(
            "ix_read_stats_unique",
            "stat_type",
            "stat_date",
            "dimension_type",
            "dimension_value",
            unique=True,
        ),
    )


class SyncSessionModel(Base):
    """
    Model for sync session tracking.

    Tracks synchronization sessions and their results.
    Compatible with both PostgreSQL and SQLite.
    """

    __tablename__ = "sync_sessions"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True)

    # Session details
    sync_type: Mapped[str] = mapped_column(String(20), nullable=False)  # full, incremental
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # pending, completed, failed

    # File information
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Statistics
    stats_data: Mapped[dict] = mapped_column(JSONType(), nullable=True)

    # Results
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    # System fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    # Indexes
    __table_args__ = (
        Index("ix_sync_sessions_status", "status"),
        Index("ix_sync_sessions_type", "sync_type"),
        Index("ix_sync_sessions_started_at", "started_at"),
        Index("ix_sync_sessions_file_hash", "file_hash"),
    )

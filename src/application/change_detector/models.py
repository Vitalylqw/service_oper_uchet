"""
Models for change detection results.

Contains Pydantic models for representing detected changes between Excel and database.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ...domain.models import Deal, DealItem


class ChangeType(str, Enum):
    """Type of change detected."""

    INSERT = "INSERT"  # New entity in Excel, not in database
    UPDATE = "UPDATE"  # Existing entity modified in Excel
    DELETE = "DELETE"  # Entity exists in database but not in Excel


class EntityType(str, Enum):
    """Type of entity that changed."""

    DEAL = "deal"
    DEAL_ITEM = "deal_item"


class EntityChange(BaseModel):
    """
    Represents a single change to an entity.

    Contains information about what changed, old and new values.
    """

    # Change identification
    change_type: ChangeType = Field(..., description="Type of change")
    entity_type: EntityType = Field(..., description="Type of entity")
    entity_key: str = Field(..., description="Business key of the entity")

    # Change details
    field_changes: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Map of field_name -> {old_value, new_value}"
    )

    # Entity data
    old_entity: Deal | DealItem | None = Field(default=None, description="Previous entity state")
    new_entity: Deal | DealItem | None = Field(default=None, description="New entity state")

    # Hash comparison
    old_hash: str | None = Field(default=None, description="Previous entity hash")
    new_hash: str | None = Field(default=None, description="New entity hash")

    @property
    def has_field_changes(self) -> bool:
        """Check if entity has field-level changes."""
        return len(self.field_changes) > 0

    @property
    def changed_fields(self) -> list[str]:
        """Get list of changed field names."""
        return list(self.field_changes.keys())

    def get_field_change(self, field_name: str) -> dict[str, Any] | None:
        """Get change details for specific field."""
        return self.field_changes.get(field_name)


class ChangeDetectionResult(BaseModel):
    """
    Result of change detection process.

    Contains all detected changes grouped by type and entity.
    """

    # Summary statistics
    total_excel_deals: int = Field(default=0, description="Total deals in Excel")
    total_db_deals: int = Field(default=0, description="Total deals in database")
    total_excel_items: int = Field(default=0, description="Total items in Excel")
    total_db_items: int = Field(default=0, description="Total items in database")

    # Changes by type
    insertions: list[EntityChange] = Field(
        default_factory=list, description="New entities to insert"
    )
    updates: list[EntityChange] = Field(
        default_factory=list, description="Existing entities to update"
    )
    deletions: list[EntityChange] = Field(
        default_factory=list, description="Entities to delete (soft delete)"
    )

    # Performance metrics
    comparison_duration_seconds: float = Field(default=0.0, description="Time taken for comparison")
    hash_comparison_count: int = Field(
        default=0, description="Number of hash comparisons performed"
    )
    detailed_comparison_count: int = Field(
        default=0, description="Number of detailed comparisons performed"
    )

    @property
    def total_changes(self) -> int:
        """Total number of changes detected."""
        return len(self.insertions) + len(self.updates) + len(self.deletions)

    @property
    def insertion_count(self) -> int:
        """Number of insertions."""
        return len(self.insertions)

    @property
    def update_count(self) -> int:
        """Number of updates."""
        return len(self.updates)

    @property
    def deletion_count(self) -> int:
        """Number of deletions."""
        return len(self.deletions)

    @property
    def has_changes(self) -> bool:
        """Check if any changes were detected."""
        return self.total_changes > 0

    def get_changes_by_type(self, change_type: ChangeType) -> list[EntityChange]:
        """Get changes filtered by type."""
        if change_type == ChangeType.INSERT:
            return self.insertions
        elif change_type == ChangeType.UPDATE:
            return self.updates
        elif change_type == ChangeType.DELETE:
            return self.deletions
        else:
            return []

    def get_changes_by_entity(self, entity_type: EntityType) -> list[EntityChange]:
        """Get changes filtered by entity type."""
        all_changes = self.insertions + self.updates + self.deletions
        return [change for change in all_changes if change.entity_type == entity_type]

    def get_deal_changes(self) -> list[EntityChange]:
        """Get all deal-related changes."""
        return self.get_changes_by_entity(EntityType.DEAL)

    def get_item_changes(self) -> list[EntityChange]:
        """Get all item-related changes."""
        return self.get_changes_by_entity(EntityType.DEAL_ITEM)

    def to_summary_dict(self) -> dict[str, Any]:
        """Convert to summary dictionary for logging/reporting."""
        return {
            "excel_data": {
                "deals": self.total_excel_deals,
                "items": self.total_excel_items,
            },
            "database_data": {
                "deals": self.total_db_deals,
                "items": self.total_db_items,
            },
            "changes": {
                "insertions": self.insertion_count,
                "updates": self.update_count,
                "deletions": self.deletion_count,
                "total": self.total_changes,
            },
            "performance": {
                "duration_seconds": self.comparison_duration_seconds,
                "hash_comparisons": self.hash_comparison_count,
                "detailed_comparisons": self.detailed_comparison_count,
            },
        }


class HashComparisonCache(BaseModel):
    """
    Cache for hash-based comparisons.

    Stores entity hashes for fast change detection.
    """

    entity_hashes: dict[str, str] = Field(
        default_factory=dict, description="Map of entity_key -> hash_value"
    )

    def get_hash(self, entity_key: str) -> str | None:
        """Get hash for entity key."""
        return self.entity_hashes.get(entity_key)

    def set_hash(self, entity_key: str, hash_value: str) -> None:
        """Set hash for entity key."""
        self.entity_hashes[entity_key] = hash_value

    def has_entity(self, entity_key: str) -> bool:
        """Check if entity exists in cache."""
        return entity_key in self.entity_hashes

    def remove_entity(self, entity_key: str) -> None:
        """Remove entity from cache."""
        self.entity_hashes.pop(entity_key, None)

    def clear(self) -> None:
        """Clear all cached hashes."""
        self.entity_hashes.clear()

    @property
    def entity_count(self) -> int:
        """Number of cached entities."""
        return len(self.entity_hashes)

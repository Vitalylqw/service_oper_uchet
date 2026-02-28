"""
Pydantic models for QA Suite test framework.

Contains data models for test scenarios, expected results, validation,
and aggregate metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ScenarioCategory(str, Enum):
    """Category of test scenario."""

    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    MIXED = "MIXED"
    EDGE = "EDGE"


class ScenarioStatus(str, Enum):
    """Status of scenario execution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class ActionType(str, Enum):
    """Type of action to perform on Excel file."""

    ADD_SHEET = "add_sheet"
    REMOVE_SHEET = "remove_sheet"
    ADD_DEAL = "add_deal"
    REMOVE_DEAL = "remove_deal"
    UPDATE_DEAL_FIELD = "update_deal_field"
    ADD_POSITION = "add_position"
    REMOVE_POSITION = "remove_position"
    UPDATE_POSITION_FIELD = "update_position_field"


class ItemData(BaseModel):
    """Data for a deal item/position."""

    product_name: str = Field(..., description="Product name")
    supplier_name: Optional[str] = Field(None, description="Supplier name")
    quantity: Optional[Decimal] = Field(None, description="Quantity")
    purchase_price: Optional[Decimal] = Field(None, description="Purchase price")
    sale_price: Optional[Decimal] = Field(None, description="Sale price")
    pickup_date: Optional[str] = Field(None, description="Pickup date")
    position_number: Optional[int] = Field(None, description="Position number")

    # Calculated fields (optional, for expected values)
    revenue: Optional[Decimal] = Field(None, description="Expected revenue")
    margin: Optional[Decimal] = Field(None, description="Expected margin")
    cost: Optional[Decimal] = Field(None, description="Expected cost")


class DealData(BaseModel):
    """Data for a deal."""

    client_name: str = Field(..., description="Client name")
    invoice_info: str = Field(..., description="Invoice info (number + date)")
    invoice_number: Optional[str] = Field(None, description="Invoice number")
    invoice_date: Optional[str] = Field(None, description="Invoice date")
    seller: str = Field(..., description="Seller name")
    is_shipped: Optional[str] = Field(None, description="Shipped status (yes/no)")
    is_paid: Optional[str] = Field(None, description="Paid status (yes/no)")
    upd_number: Optional[str] = Field(None, description="UPD number")
    total_revenue: Optional[Decimal] = Field(None, description="Total revenue")
    total_margin: Optional[Decimal] = Field(None, description="Total margin")
    total_cost: Optional[Decimal] = Field(None, description="Total cost")
    kickback_amount: Optional[Decimal] = Field(None, description="Kickback amount")
    items: list[ItemData] = Field(default_factory=list, description="Deal items")

    @property
    def deal_key(self) -> str:
        """Generate deal key from invoice info and seller."""
        num = (self.invoice_number or "").strip().lower()
        date = (self.invoice_date or "").strip().lower()
        seller = (self.seller or "").strip().lower()
        return f"{num}|{date}|{seller}"


class ScenarioAction(BaseModel):
    """Action to perform in a test scenario."""

    type: ActionType = Field(..., description="Type of action")
    sheet_name: Optional[str] = Field(None, description="Target sheet name")
    deal_key: Optional[str] = Field(None, description="Target deal key")
    field_name: Optional[str] = Field(None, description="Field to update")
    field_value: Optional[Any] = Field(None, description="New field value")
    position_number: Optional[int] = Field(None, description="Position number")
    deals: list[DealData] = Field(default_factory=list, description="Deals to add")
    items: list[ItemData] = Field(default_factory=list, description="Items to add")


class ExpectedChanges(BaseModel):
    """Expected changes from sync operation."""

    insertions: int = Field(default=0, description="Expected insertions count")
    updates: int = Field(default=0, description="Expected updates count")
    deletions: int = Field(default=0, description="Expected deletions count")


class ExpectedDBState(BaseModel):
    """Expected database state after sync."""

    deals_count: Optional[str] = Field(
        None, description="Expected deals count (absolute or relative: '+1', '-2')"
    )
    positions_count: Optional[str] = Field(
        None, description="Expected positions count"
    )
    deals_in_period: Optional[dict[str, int]] = Field(
        None, description="Expected deals count by period"
    )
    positions_in_period: Optional[dict[str, int]] = Field(
        None, description="Expected positions count by period"
    )
    deal_exists: Optional[list[str]] = Field(
        None, description="Deal keys that should exist"
    )
    deal_not_exists: Optional[list[str]] = Field(
        None, description="Deal keys that should not exist"
    )


class ExpectedEvents(BaseModel):
    """Expected events from sync operation."""

    events: list[dict[str, Any]] = Field(
        default_factory=list, description="Expected events with type and count"
    )


class ExpectedResult(BaseModel):
    """Complete expected result for a scenario."""

    changes: ExpectedChanges = Field(
        default_factory=ExpectedChanges, description="Expected change counts"
    )
    db_state: ExpectedDBState = Field(
        default_factory=ExpectedDBState, description="Expected DB state"
    )
    events: ExpectedEvents = Field(
        default_factory=ExpectedEvents, description="Expected events"
    )
    sync_success: bool = Field(default=True, description="Expected sync success")


class TestScenario(BaseModel):
    """Complete test scenario definition."""

    id: str = Field(..., description="Unique scenario ID")
    name: str = Field(..., description="Human-readable scenario name")
    description: Optional[str] = Field(None, description="Detailed description")
    category: ScenarioCategory = Field(..., description="Scenario category")
    enabled: bool = Field(default=True, description="Whether scenario is enabled")

    # Setup
    base_state: Optional[str] = Field(
        None, description="Base Excel file to start from"
    )
    clear_db_before: bool = Field(
        default=False, description="Clear database before running"
    )
    sync_base_first: bool = Field(
        default=True, description="Sync base state before applying actions"
    )

    # Actions
    actions: list[ScenarioAction] = Field(
        default_factory=list, description="Actions to perform"
    )

    # Expected results
    expected: ExpectedResult = Field(
        default_factory=ExpectedResult, description="Expected results"
    )


class ValidationCheck(BaseModel):
    """Single validation check result."""

    check_name: str = Field(..., description="Name of the check")
    expected: Any = Field(..., description="Expected value")
    actual: Any = Field(..., description="Actual value")
    passed: bool = Field(..., description="Whether check passed")
    message: Optional[str] = Field(None, description="Additional message")


class ValidationResult(BaseModel):
    """Result of validation for a scenario."""

    passed: bool = Field(..., description="Overall validation passed")
    checks: list[ValidationCheck] = Field(
        default_factory=list, description="Individual check results"
    )
    errors: list[str] = Field(default_factory=list, description="Error messages")

    def add_check(
        self,
        check_name: str,
        expected: Any,
        actual: Any,
        message: Optional[str] = None,
    ) -> None:
        """Add a validation check."""
        passed = expected == actual
        self.checks.append(
            ValidationCheck(
                check_name=check_name,
                expected=expected,
                actual=actual,
                passed=passed,
                message=message,
            )
        )
        if not passed:
            self.passed = False

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.passed = False


class ScenarioResult(BaseModel):
    """Complete result of scenario execution."""

    scenario_id: str = Field(..., description="Scenario ID")
    scenario_name: str = Field(..., description="Scenario name")
    status: ScenarioStatus = Field(..., description="Execution status")
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime] = Field(None)
    duration_ms: Optional[int] = Field(None)
    validation: Optional[ValidationResult] = Field(None)
    error_message: Optional[str] = Field(None)
    sync_result_summary: Optional[dict[str, Any]] = Field(None)

    def complete(
        self,
        status: ScenarioStatus,
        validation: Optional[ValidationResult] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Complete scenario execution."""
        self.finished_at = datetime.now()
        self.status = status
        self.validation = validation
        self.error_message = error_message
        if self.started_at and self.finished_at:
            delta = self.finished_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)


@dataclass
class AggregateMetrics:
    """Aggregate database metrics for integrity checking."""

    total_deals: int = 0
    total_positions: int = 0
    total_revenue_sum: Decimal = field(default_factory=lambda: Decimal("0"))
    total_margin_sum: Decimal = field(default_factory=lambda: Decimal("0"))
    total_cost_sum: Decimal = field(default_factory=lambda: Decimal("0"))
    deals_by_period: dict[str, int] = field(default_factory=dict)
    positions_by_period: dict[str, int] = field(default_factory=dict)
    deals_with_errors: int = 0
    unique_clients: int = 0
    unique_sellers: int = 0
    total_events: int = 0
    events_by_type: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_deals": self.total_deals,
            "total_positions": self.total_positions,
            "total_revenue_sum": str(self.total_revenue_sum),
            "total_margin_sum": str(self.total_margin_sum),
            "total_cost_sum": str(self.total_cost_sum),
            "deals_by_period": self.deals_by_period,
            "positions_by_period": self.positions_by_period,
            "deals_with_errors": self.deals_with_errors,
            "unique_clients": self.unique_clients,
            "unique_sellers": self.unique_sellers,
            "total_events": self.total_events,
            "events_by_type": self.events_by_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AggregateMetrics":
        """Create from dictionary."""
        return cls(
            total_deals=data.get("total_deals", 0),
            total_positions=data.get("total_positions", 0),
            total_revenue_sum=Decimal(data.get("total_revenue_sum", "0")),
            total_margin_sum=Decimal(data.get("total_margin_sum", "0")),
            total_cost_sum=Decimal(data.get("total_cost_sum", "0")),
            deals_by_period=data.get("deals_by_period", {}),
            positions_by_period=data.get("positions_by_period", {}),
            deals_with_errors=data.get("deals_with_errors", 0),
            unique_clients=data.get("unique_clients", 0),
            unique_sellers=data.get("unique_sellers", 0),
            total_events=data.get("total_events", 0),
            events_by_type=data.get("events_by_type", {}),
        )


@dataclass
class DBSnapshot:
    """Snapshot of database state for restoration."""

    timestamp: datetime = field(default_factory=datetime.now)
    deals: list[dict[str, Any]] = field(default_factory=list)
    positions: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    metrics: Optional[AggregateMetrics] = None


class TestRunReport(BaseModel):
    """Complete test run report."""

    run_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    total_scenarios: int = Field(default=0)
    passed: int = Field(default=0)
    failed: int = Field(default=0)
    skipped: int = Field(default=0)
    errors: int = Field(default=0)
    duration_ms: int = Field(default=0)
    scenarios: list[ScenarioResult] = Field(default_factory=list)
    aggregates_before: Optional[dict[str, Any]] = Field(None)
    aggregates_after: Optional[dict[str, Any]] = Field(None)
    aggregate_diff: Optional[dict[str, Any]] = Field(None)

    def add_result(self, result: ScenarioResult) -> None:
        """Add a scenario result."""
        self.scenarios.append(result)
        self.total_scenarios += 1
        if result.status == ScenarioStatus.PASSED:
            self.passed += 1
        elif result.status == ScenarioStatus.FAILED:
            self.failed += 1
        elif result.status == ScenarioStatus.SKIPPED:
            self.skipped += 1
        elif result.status == ScenarioStatus.ERROR:
            self.errors += 1
        if result.duration_ms:
            self.duration_ms += result.duration_ms

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_scenarios == 0:
            return 0.0
        return (self.passed / self.total_scenarios) * 100

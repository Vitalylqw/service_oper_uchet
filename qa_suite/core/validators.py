"""
Result Validators for QA Suite.

Validates sync results against expected outcomes including
change counts, database state, events, and aggregate metrics.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Optional

from loguru import logger

from .db_manager import DBManager
from .models import (
    AggregateMetrics,
    ExpectedChanges,
    ExpectedDBState,
    ExpectedEvents,
    ExpectedResult,
    ValidationCheck,
    ValidationResult,
)


class ResultValidator:
    """
    Validator for sync operation results.

    Compares actual results against expected outcomes.
    """

    def __init__(self, db_manager: DBManager) -> None:
        """
        Initialize validator.

        Args:
            db_manager: Database manager for state queries.
        """
        self._db_manager = db_manager

    async def validate_all(
        self,
        expected: ExpectedResult,
        sync_result: Any,
        metrics_before: AggregateMetrics,
        metrics_after: AggregateMetrics,
    ) -> ValidationResult:
        """
        Validate all aspects of sync result.

        Args:
            expected: Expected results.
            sync_result: Actual sync result from orchestrator.
            metrics_before: Aggregate metrics before sync.
            metrics_after: Aggregate metrics after sync.

        Returns:
            ValidationResult with all checks.
        """
        validation = ValidationResult(passed=True, checks=[], errors=[])

        # Validate change counts
        changes_validation = self.validate_change_counts(
            sync_result, expected.changes
        )
        validation.checks.extend(changes_validation.checks)
        if not changes_validation.passed:
            validation.passed = False
            validation.errors.extend(changes_validation.errors)

        # Validate database state
        db_validation = await self.validate_db_state(
            expected.db_state, metrics_before, metrics_after
        )
        validation.checks.extend(db_validation.checks)
        if not db_validation.passed:
            validation.passed = False
            validation.errors.extend(db_validation.errors)

        # Validate events
        events_validation = self.validate_events(
            sync_result, expected.events
        )
        validation.checks.extend(events_validation.checks)
        if not events_validation.passed:
            validation.passed = False
            validation.errors.extend(events_validation.errors)

        # Validate sync success
        if expected.sync_success is not None:
            actual_success = sync_result.summary.success
            validation.add_check(
                "sync_success",
                expected.sync_success,
                actual_success,
                "Sync operation success status",
            )

        return validation

    def validate_change_counts(
        self, sync_result: Any, expected: ExpectedChanges
    ) -> ValidationResult:
        """
        Validate change counts from sync result.

        Args:
            sync_result: Actual sync result.
            expected: Expected change counts.

        Returns:
            ValidationResult for change counts.
        """
        validation = ValidationResult(passed=True, checks=[], errors=[])

        actual_insertions = sync_result.summary.insertions_count
        actual_updates = sync_result.summary.updates_count
        actual_deletions = sync_result.summary.deletions_count

        validation.add_check(
            "insertions_count",
            expected.insertions,
            actual_insertions,
            f"Expected {expected.insertions} insertions, got {actual_insertions}",
        )

        validation.add_check(
            "updates_count",
            expected.updates,
            actual_updates,
            f"Expected {expected.updates} updates, got {actual_updates}",
        )

        validation.add_check(
            "deletions_count",
            expected.deletions,
            actual_deletions,
            f"Expected {expected.deletions} deletions, got {actual_deletions}",
        )

        return validation

    async def validate_db_state(
        self,
        expected: ExpectedDBState,
        metrics_before: AggregateMetrics,
        metrics_after: AggregateMetrics,
    ) -> ValidationResult:
        """
        Validate database state after sync.

        Args:
            expected: Expected database state.
            metrics_before: Metrics before sync.
            metrics_after: Metrics after sync.

        Returns:
            ValidationResult for database state.
        """
        validation = ValidationResult(passed=True, checks=[], errors=[])

        # Validate deals count (relative or absolute)
        if expected.deals_count is not None:
            expected_deals = self._parse_count_expectation(
                expected.deals_count, metrics_before.total_deals
            )
            validation.add_check(
                "deals_count",
                expected_deals,
                metrics_after.total_deals,
                f"Expected {expected_deals} deals, got {metrics_after.total_deals}",
            )

        # Validate positions count
        if expected.positions_count is not None:
            expected_positions = self._parse_count_expectation(
                expected.positions_count, metrics_before.total_positions
            )
            validation.add_check(
                "positions_count",
                expected_positions,
                metrics_after.total_positions,
                f"Expected {expected_positions} positions, got {metrics_after.total_positions}",
            )

        # Validate deals in specific periods
        if expected.deals_in_period:
            for period, expected_count in expected.deals_in_period.items():
                actual_count = metrics_after.deals_by_period.get(period, 0)
                validation.add_check(
                    f"deals_in_period_{period}",
                    expected_count,
                    actual_count,
                    f"Expected {expected_count} deals in {period}, got {actual_count}",
                )

        # Validate positions in specific periods
        if expected.positions_in_period:
            for period, expected_count in expected.positions_in_period.items():
                actual_count = metrics_after.positions_by_period.get(period, 0)
                validation.add_check(
                    f"positions_in_period_{period}",
                    expected_count,
                    actual_count,
                    f"Expected {expected_count} positions in {period}, got {actual_count}",
                )

        # Validate deal existence
        if expected.deal_exists:
            for deal_key in expected.deal_exists:
                exists = await self._db_manager.deal_exists(deal_key)
                validation.add_check(
                    f"deal_exists_{deal_key}",
                    True,
                    exists,
                    f"Deal {deal_key} should exist",
                )

        # Validate deal non-existence
        if expected.deal_not_exists:
            for deal_key in expected.deal_not_exists:
                exists = await self._db_manager.deal_exists(deal_key)
                validation.add_check(
                    f"deal_not_exists_{deal_key}",
                    False,
                    exists,
                    f"Deal {deal_key} should not exist",
                )

        return validation

    def validate_events(
        self, sync_result: Any, expected: ExpectedEvents
    ) -> ValidationResult:
        """
        Validate events created during sync.

        Args:
            sync_result: Actual sync result.
            expected: Expected events.

        Returns:
            ValidationResult for events.
        """
        validation = ValidationResult(passed=True, checks=[], errors=[])

        if not expected.events:
            return validation

        # Get actual events from sync result
        actual_events = getattr(sync_result, "events_created", []) or []

        # Count events by type
        actual_by_type: dict[str, int] = {}
        for event in actual_events:
            event_type = event.get("event_type", "unknown")
            actual_by_type[event_type] = actual_by_type.get(event_type, 0) + 1

        # Validate expected event counts
        for expected_event in expected.events:
            if isinstance(expected_event, dict):
                event_type = expected_event.get("type")
                expected_count = expected_event.get("count", 0)

                actual_count = actual_by_type.get(event_type, 0)
                validation.add_check(
                    f"event_count_{event_type}",
                    expected_count,
                    actual_count,
                    f"Expected {expected_count} {event_type} events, got {actual_count}",
                )

        return validation

    def validate_aggregates(
        self,
        before: AggregateMetrics,
        after: AggregateMetrics,
        expected_diff: Optional[dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Validate aggregate metrics changes.

        Args:
            before: Metrics before operation.
            after: Metrics after operation.
            expected_diff: Expected differences.

        Returns:
            ValidationResult for aggregates.
        """
        validation = ValidationResult(passed=True, checks=[], errors=[])

        if not expected_diff:
            return validation

        # Validate deals diff
        if "deals_diff" in expected_diff:
            actual_diff = after.total_deals - before.total_deals
            validation.add_check(
                "deals_diff",
                expected_diff["deals_diff"],
                actual_diff,
                f"Expected deals diff {expected_diff['deals_diff']}, got {actual_diff}",
            )

        # Validate positions diff
        if "positions_diff" in expected_diff:
            actual_diff = after.total_positions - before.total_positions
            validation.add_check(
                "positions_diff",
                expected_diff["positions_diff"],
                actual_diff,
                f"Expected positions diff {expected_diff['positions_diff']}, got {actual_diff}",
            )

        # Validate revenue diff
        if "revenue_diff" in expected_diff:
            actual_diff = after.total_revenue_sum - before.total_revenue_sum
            expected_rev_diff = Decimal(str(expected_diff["revenue_diff"]))
            validation.add_check(
                "revenue_diff",
                expected_rev_diff,
                actual_diff,
                f"Expected revenue diff {expected_rev_diff}, got {actual_diff}",
            )

        return validation

    def _parse_count_expectation(
        self, expectation: str, before_value: int
    ) -> int:
        """
        Parse count expectation which can be absolute or relative.

        Args:
            expectation: String like "5", "+1", "-2".
            before_value: Value before operation for relative calculations.

        Returns:
            Expected absolute count.
        """
        expectation = str(expectation).strip()

        # Check for relative values
        if expectation.startswith("+"):
            return before_value + int(expectation[1:])
        elif expectation.startswith("-"):
            return before_value - int(expectation[1:])
        else:
            return int(expectation)


class AggregateValidator:
    """
    Validator for aggregate integrity checks.

    Ensures no unexpected global changes occurred.
    """

    def __init__(self, tolerance: Decimal = Decimal("0.01")) -> None:
        """
        Initialize validator.

        Args:
            tolerance: Tolerance for decimal comparisons.
        """
        self._tolerance = tolerance

    def validate_no_unexpected_changes(
        self,
        before: AggregateMetrics,
        after: AggregateMetrics,
        expected_changes: dict[str, Any],
    ) -> ValidationResult:
        """
        Validate that no unexpected aggregate changes occurred.

        Args:
            before: Metrics before operation.
            after: Metrics after operation.
            expected_changes: Expected aggregate changes.

        Returns:
            ValidationResult for unexpected changes.
        """
        validation = ValidationResult(passed=True, checks=[], errors=[])

        # Check for unexpected period additions
        new_periods = set(after.deals_by_period.keys()) - set(
            before.deals_by_period.keys()
        )
        expected_new_periods = set(expected_changes.get("new_periods", []))
        unexpected_new = new_periods - expected_new_periods
        if unexpected_new:
            validation.add_error(
                f"Unexpected new periods appeared: {unexpected_new}"
            )

        # Check for unexpected period removals
        removed_periods = set(before.deals_by_period.keys()) - set(
            after.deals_by_period.keys()
        )
        expected_removed = set(expected_changes.get("removed_periods", []))
        unexpected_removed = removed_periods - expected_removed
        if unexpected_removed:
            validation.add_error(
                f"Unexpected periods removed: {unexpected_removed}"
            )

        # Check for data integrity (no deals with errors increased unexpectedly)
        if (
            after.deals_with_errors > before.deals_with_errors
            and not expected_changes.get("allow_new_errors", False)
        ):
            validation.add_check(
                "deals_with_errors",
                before.deals_with_errors,
                after.deals_with_errors,
                "Unexpected increase in deals with totals errors",
            )

        return validation

    def validate_financial_consistency(
        self, metrics: AggregateMetrics
    ) -> ValidationResult:
        """
        Validate financial consistency of aggregate metrics.

        Args:
            metrics: Current aggregate metrics.

        Returns:
            ValidationResult for financial consistency.
        """
        validation = ValidationResult(passed=True, checks=[], errors=[])

        # Basic check: margin should be revenue - cost (approximately)
        expected_margin = metrics.total_revenue_sum - metrics.total_cost_sum
        margin_diff = abs(metrics.total_margin_sum - expected_margin)

        # Allow some tolerance due to rounding
        if margin_diff > self._tolerance * metrics.total_deals:
            validation.add_check(
                "financial_consistency",
                str(expected_margin),
                str(metrics.total_margin_sum),
                f"Margin sum {metrics.total_margin_sum} differs from "
                f"revenue-cost {expected_margin} by {margin_diff}",
            )

        return validation

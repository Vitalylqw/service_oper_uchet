"""
Scenario Loader for QA Suite.

Loads and parses test scenarios from YAML configuration files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml
from loguru import logger

from .models import (
    ActionType,
    DealData,
    ExpectedChanges,
    ExpectedDBState,
    ExpectedEvents,
    ExpectedResult,
    ItemData,
    ScenarioAction,
    ScenarioCategory,
    TestScenario,
)


class ScenarioLoader:
    """Loader for test scenarios from YAML files."""

    def __init__(self, scenarios_dir: Path) -> None:
        """
        Initialize scenario loader.

        Args:
            scenarios_dir: Directory containing scenario YAML files.
        """
        self._scenarios_dir = scenarios_dir

    def load_all_scenarios(self) -> list[TestScenario]:
        """
        Load all scenarios from the scenarios directory.

        Returns:
            List of parsed TestScenario objects.
        """
        scenarios = []

        if not self._scenarios_dir.exists():
            logger.warning(f"Scenarios directory not found: {self._scenarios_dir}")
            return scenarios

        # Load from all YAML files in directory
        for yaml_file in self._scenarios_dir.glob("*.yaml"):
            try:
                file_scenarios = self.load_from_file(yaml_file)
                scenarios.extend(file_scenarios)
                logger.debug(f"Loaded {len(file_scenarios)} scenarios from {yaml_file}")
            except Exception as e:
                logger.error(f"Failed to load scenarios from {yaml_file}: {e}")

        # Also check for .yml extension
        for yaml_file in self._scenarios_dir.glob("*.yml"):
            try:
                file_scenarios = self.load_from_file(yaml_file)
                scenarios.extend(file_scenarios)
                logger.debug(f"Loaded {len(file_scenarios)} scenarios from {yaml_file}")
            except Exception as e:
                logger.error(f"Failed to load scenarios from {yaml_file}: {e}")

        logger.info(f"Loaded {len(scenarios)} total scenarios")
        return scenarios

    def load_from_file(self, file_path: Path) -> list[TestScenario]:
        """
        Load scenarios from a single YAML file.

        Args:
            file_path: Path to YAML file.

        Returns:
            List of parsed TestScenario objects.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Scenario file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return []

        scenarios_data = data.get("scenarios", [])
        if not scenarios_data:
            # Single scenario file
            if "id" in data:
                scenarios_data = [data]
            else:
                return []

        return [self._parse_scenario(s) for s in scenarios_data]

    def load_scenario_by_id(self, scenario_id: str) -> Optional[TestScenario]:
        """
        Load a specific scenario by ID.

        Args:
            scenario_id: Unique scenario identifier.

        Returns:
            TestScenario if found, None otherwise.
        """
        all_scenarios = self.load_all_scenarios()
        for scenario in all_scenarios:
            if scenario.id == scenario_id:
                return scenario
        return None

    def load_scenarios_by_category(
        self, category: ScenarioCategory
    ) -> list[TestScenario]:
        """
        Load all scenarios of a specific category.

        Args:
            category: Scenario category to filter by.

        Returns:
            List of matching scenarios.
        """
        all_scenarios = self.load_all_scenarios()
        return [s for s in all_scenarios if s.category == category]

    def _parse_scenario(self, data: dict[str, Any]) -> TestScenario:
        """Parse a single scenario from dictionary data."""
        # Parse actions
        actions = []
        for action_data in data.get("actions", []):
            actions.append(self._parse_action(action_data))

        # Parse expected result
        expected_data = data.get("expected", {})
        expected = self._parse_expected(expected_data)

        return TestScenario(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            category=ScenarioCategory(data.get("category", "MIXED")),
            enabled=data.get("enabled", True),
            base_state=data.get("setup", {}).get("base_state"),
            clear_db_before=data.get("setup", {}).get("clear_db_before", False),
            sync_base_first=data.get("setup", {}).get("sync_base_first", True),
            actions=actions,
            expected=expected,
        )

    def _parse_action(self, data: dict[str, Any]) -> ScenarioAction:
        """Parse a single action from dictionary data."""
        # Parse deals if present
        deals = []
        for deal_data in data.get("deals", []):
            deals.append(self._parse_deal(deal_data))

        # Parse items if present
        items = []
        for item_data in data.get("items", []):
            items.append(self._parse_item(item_data))

        return ScenarioAction(
            type=ActionType(data["type"]),
            sheet_name=data.get("sheet_name"),
            deal_key=data.get("deal_key"),
            field_name=data.get("field_name"),
            field_value=data.get("field_value"),
            position_number=data.get("position_number"),
            deals=deals,
            items=items,
        )

    def _parse_deal(self, data: dict[str, Any]) -> DealData:
        """Parse deal data from dictionary."""
        # Parse items if present
        items = []
        for item_data in data.get("items", []):
            items.append(self._parse_item(item_data))

        return DealData(
            client_name=data["client_name"],
            invoice_info=data["invoice_info"],
            invoice_number=data.get("invoice_number"),
            invoice_date=data.get("invoice_date"),
            seller=data["seller"],
            is_shipped=data.get("is_shipped"),
            is_paid=data.get("is_paid"),
            upd_number=data.get("upd_number"),
            total_revenue=data.get("total_revenue"),
            total_margin=data.get("total_margin"),
            total_cost=data.get("total_cost"),
            kickback_amount=data.get("kickback_amount"),
            items=items,
        )

    def _parse_item(self, data: dict[str, Any]) -> ItemData:
        """Parse item data from dictionary."""
        return ItemData(
            product_name=data["product_name"],
            supplier_name=data.get("supplier_name"),
            quantity=data.get("quantity"),
            purchase_price=data.get("purchase_price"),
            sale_price=data.get("sale_price"),
            pickup_date=data.get("pickup_date"),
            position_number=data.get("position_number"),
            revenue=data.get("revenue"),
            margin=data.get("margin"),
            cost=data.get("cost"),
        )

    def _parse_expected(self, data: dict[str, Any]) -> ExpectedResult:
        """Parse expected result from dictionary data."""
        # Parse changes
        changes_data = data.get("changes", {})
        changes = ExpectedChanges(
            insertions=changes_data.get("insertions", 0),
            updates=changes_data.get("updates", 0),
            deletions=changes_data.get("deletions", 0),
        )

        # Parse db_state
        db_state_data = data.get("db_state", {})
        db_state = ExpectedDBState(
            deals_count=db_state_data.get("deals_count"),
            positions_count=db_state_data.get("positions_count"),
            deals_in_period=db_state_data.get("deals_in_period"),
            positions_in_period=db_state_data.get("positions_in_period"),
            deal_exists=db_state_data.get("deal_exists"),
            deal_not_exists=db_state_data.get("deal_not_exists"),
        )

        # Parse events
        events_data = data.get("events", {})
        events = ExpectedEvents(
            events=events_data.get("events", []) if isinstance(events_data, dict) else events_data
        )

        return ExpectedResult(
            changes=changes,
            db_state=db_state,
            events=events,
            sync_success=data.get("sync_success", True),
        )


def create_scenario_template() -> str:
    """
    Create a template YAML string for new scenarios.

    Returns:
        YAML template string.
    """
    return """# Test Scenario Template
scenarios:
  - id: TEST_XXX_01
    name: "Scenario Name"
    description: "Detailed description of the test scenario"
    category: INSERT  # INSERT, UPDATE, DELETE, MIXED, EDGE
    enabled: true
    
    setup:
      base_state: "base_state.xlsx"
      clear_db_before: false
      sync_base_first: true
    
    actions:
      - type: add_sheet  # add_sheet, remove_sheet, add_deal, remove_deal,
                         # update_deal_field, add_position, remove_position,
                         # update_position_field
        sheet_name: "Июнь 2025"
        deals:
          - client_name: "ООО Тест"
            invoice_info: "1001 от 01.06.2025"
            invoice_number: "1001"
            invoice_date: "01.06.2025"
            seller: "Продавец А"
            is_shipped: "нет"
            is_paid: "нет"
            total_revenue: 10000.00
            total_margin: 2000.00
            total_cost: 8000.00
            items:
              - product_name: "Товар 1"
                quantity: 10
                purchase_price: 100.00
                sale_price: 150.00
                supplier_name: "Поставщик"
                pickup_date: "01"
    
    expected:
      changes:
        insertions: 2  # 1 deal + 1 item
        updates: 0
        deletions: 0
      
      db_state:
        deals_count: "+1"  # Relative change
        positions_count: "+1"
        deals_in_period:
          "Июнь 2025": 1
      
      events:
        - type: DealCreated
          count: 1
        - type: DealItemAdded
          count: 1
      
      sync_success: true
"""

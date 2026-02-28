"""
Excel Builder for programmatic Excel file generation and modification.

Creates and modifies Excel files for testing sync operations.
Follows the exact structure expected by ExcelParserService.
"""

from __future__ import annotations

import shutil
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from loguru import logger
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from .models import DealData, ItemData


# Excel column indices matching parser expectations
COLUMN_INDICES = {
    # Deal (master row) columns
    "client_name": 0,       # A - Client name
    "invoice_info": 1,      # B - Invoice info (number + date)
    "is_shipped": 2,        # C - Shipped status
    "upd_number": 3,        # D - UPD number
    "is_paid": 4,           # E - Paid status
    "total_revenue": 5,     # F - Total revenue
    "total_margin": 6,      # G - Total margin
    "seller": 7,            # H - Seller name
    "total_cost": 8,        # I - Total cost
    "kickback_amount": 9,   # J - Kickback amount
}

# Item (detail row) columns - different from deal row
ITEM_COLUMN_INDICES = {
    "product_name": 1,      # B - Product name
    "quantity": 2,          # C - Quantity
    "purchase_price": 3,    # D - Purchase price
    "sale_price": 4,        # E - Sale price
    "revenue": 5,           # F - Revenue
    "margin": 6,            # G - Margin
    "cost": 8,              # I - Cost
    "supplier_name": 9,     # J - Supplier name
    "pickup_date": 10,      # K - Pickup date
}

# Header row content for validation
HEADER_MARKER = "Клиент"


class ExcelBuilder:
    """Builder for creating and modifying Excel files for sync testing."""

    def __init__(self, source_path: Optional[Path] = None) -> None:
        """
        Initialize ExcelBuilder.

        Args:
            source_path: Optional path to existing Excel file to load.
                        If None, creates a new empty workbook.
        """
        self._source_path = source_path
        if source_path and source_path.exists():
            self._workbook = load_workbook(str(source_path))
            logger.debug(f"Loaded workbook from {source_path}")
        else:
            self._workbook = Workbook()
            # Remove default sheet
            if "Sheet" in self._workbook.sheetnames:
                del self._workbook["Sheet"]
            logger.debug("Created new empty workbook")

    @classmethod
    def from_file(cls, path: Path) -> "ExcelBuilder":
        """Create builder from existing Excel file."""
        if not path.exists():
            raise FileNotFoundError(f"Excel file not found: {path}")
        return cls(source_path=path)

    @classmethod
    def create_new(cls) -> "ExcelBuilder":
        """Create builder with new empty workbook."""
        return cls(source_path=None)

    @classmethod
    def copy_from(cls, source_path: Path, dest_path: Path) -> "ExcelBuilder":
        """Create builder by copying existing file to new location."""
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        shutil.copy2(source_path, dest_path)
        return cls(source_path=dest_path)

    @property
    def sheet_names(self) -> list[str]:
        """Get list of sheet names."""
        return self._workbook.sheetnames

    def _get_or_create_sheet(self, sheet_name: str) -> Worksheet:
        """Get existing sheet or create new one."""
        if sheet_name in self._workbook.sheetnames:
            return self._workbook[sheet_name]
        else:
            sheet = self._workbook.create_sheet(sheet_name)
            self._write_header_row(sheet)
            return sheet

    def _write_header_row(self, sheet: Worksheet) -> None:
        """Write header row to sheet."""
        headers = [
            "Клиент",
            "Счет",
            "Отгружен",
            "УПД",
            "Оплачен",
            "Выручка",
            "Маржа",
            "Продавец",
            "Себест.",
            "Откат",
        ]
        for col, header in enumerate(headers, start=1):
            sheet.cell(row=1, column=col, value=header)

    def _find_header_row(self, sheet: Worksheet) -> int:
        """Find the header row index (1-based)."""
        for row_idx in range(1, min(10, sheet.max_row + 1)):
            cell_value = sheet.cell(row=row_idx, column=1).value
            if cell_value and HEADER_MARKER in str(cell_value):
                return row_idx
        return 1  # Default to first row

    def _find_deal_row(
        self, sheet: Worksheet, deal_key: str, period: str
    ) -> Optional[int]:
        """Find row index of a deal by its key."""
        header_row = self._find_header_row(sheet)
        for row_idx in range(header_row + 1, sheet.max_row + 1):
            client_name = sheet.cell(row=row_idx, column=1).value
            if client_name:  # This is a deal row
                invoice_info = sheet.cell(
                    row=row_idx, column=COLUMN_INDICES["invoice_info"] + 1
                ).value
                seller = sheet.cell(
                    row=row_idx, column=COLUMN_INDICES["seller"] + 1
                ).value
                row_key = self._build_deal_key(invoice_info, seller, period)
                if row_key == deal_key:
                    return row_idx
        return None

    def _build_deal_key(
        self, invoice_info: Optional[str], seller: Optional[str], period: str
    ) -> str:
        """Build deal key from components."""
        # Parse invoice_info to get number and date
        invoice_number = ""
        invoice_date = ""
        if invoice_info:
            parts = str(invoice_info).split(" от ")
            if len(parts) >= 1:
                invoice_number = parts[0].strip().lower()
            if len(parts) >= 2:
                invoice_date = parts[1].strip().lower()

        seller_str = (seller or "").strip().lower()
        period_str = period.strip().lower()

        return f"{invoice_number}|{invoice_date}|{seller_str}|{period_str}"

    def _get_next_row(self, sheet: Worksheet) -> int:
        """Get the next available row index."""
        return sheet.max_row + 1

    def _get_deal_items_range(
        self, sheet: Worksheet, deal_row: int
    ) -> tuple[int, int]:
        """Get the range of item rows for a deal (start_row, end_row)."""
        start_row = deal_row + 1
        end_row = deal_row

        for row_idx in range(start_row, sheet.max_row + 1):
            client_name = sheet.cell(row=row_idx, column=1).value
            if client_name:  # Next deal found
                break
            end_row = row_idx

        return start_row, end_row

    # ========== Public API ==========

    def add_sheet(
        self, sheet_name: str, deals: Optional[list[DealData]] = None
    ) -> "ExcelBuilder":
        """
        Add a new sheet (period) with optional deals.

        Args:
            sheet_name: Name of the sheet (e.g., "Май 2025")
            deals: Optional list of deals to add to the sheet
        """
        if sheet_name in self._workbook.sheetnames:
            raise ValueError(f"Sheet '{sheet_name}' already exists")

        sheet = self._workbook.create_sheet(sheet_name)
        self._write_header_row(sheet)
        logger.debug(f"Added sheet: {sheet_name}")

        if deals:
            for deal in deals:
                self._write_deal_to_sheet(sheet, deal, sheet_name)

        return self

    def remove_sheet(self, sheet_name: str) -> "ExcelBuilder":
        """Remove a sheet from the workbook."""
        if sheet_name not in self._workbook.sheetnames:
            raise ValueError(f"Sheet '{sheet_name}' not found")

        del self._workbook[sheet_name]
        logger.debug(f"Removed sheet: {sheet_name}")
        return self

    def add_deal(
        self, sheet_name: str, deal: DealData
    ) -> "ExcelBuilder":
        """Add a new deal to an existing sheet."""
        sheet = self._get_or_create_sheet(sheet_name)
        self._write_deal_to_sheet(sheet, deal, sheet_name)
        logger.debug(f"Added deal to {sheet_name}: {deal.client_name}")
        return self

    def remove_deal(self, sheet_name: str, deal_key: str) -> "ExcelBuilder":
        """Remove a deal and all its positions from a sheet."""
        if sheet_name not in self._workbook.sheetnames:
            raise ValueError(f"Sheet '{sheet_name}' not found")

        sheet = self._workbook[sheet_name]
        deal_row = self._find_deal_row(sheet, deal_key, sheet_name)

        if deal_row is None:
            raise ValueError(f"Deal '{deal_key}' not found in sheet '{sheet_name}'")

        # Find item range
        start_item, end_item = self._get_deal_items_range(sheet, deal_row)

        # Delete rows from bottom to top to preserve indices
        rows_to_delete = list(range(deal_row, end_item + 1))
        for row in reversed(rows_to_delete):
            sheet.delete_rows(row)

        logger.debug(f"Removed deal {deal_key} from {sheet_name}")
        return self

    def update_deal_field(
        self,
        sheet_name: str,
        deal_key: str,
        field_name: str,
        value: Any,
    ) -> "ExcelBuilder":
        """Update a specific field of a deal."""
        if sheet_name not in self._workbook.sheetnames:
            raise ValueError(f"Sheet '{sheet_name}' not found")

        sheet = self._workbook[sheet_name]
        deal_row = self._find_deal_row(sheet, deal_key, sheet_name)

        if deal_row is None:
            raise ValueError(f"Deal '{deal_key}' not found in sheet '{sheet_name}'")

        if field_name not in COLUMN_INDICES:
            raise ValueError(f"Unknown deal field: {field_name}")

        col = COLUMN_INDICES[field_name] + 1  # openpyxl is 1-indexed
        sheet.cell(row=deal_row, column=col, value=value)
        logger.debug(f"Updated deal {deal_key} field {field_name} = {value}")
        return self

    def add_position(
        self,
        sheet_name: str,
        deal_key: str,
        item: ItemData,
    ) -> "ExcelBuilder":
        """Add a new position to an existing deal."""
        if sheet_name not in self._workbook.sheetnames:
            raise ValueError(f"Sheet '{sheet_name}' not found")

        sheet = self._workbook[sheet_name]
        deal_row = self._find_deal_row(sheet, deal_key, sheet_name)

        if deal_row is None:
            raise ValueError(f"Deal '{deal_key}' not found in sheet '{sheet_name}'")

        # Find where to insert (after last item of this deal)
        _, end_item = self._get_deal_items_range(sheet, deal_row)
        insert_row = end_item + 1

        # Insert new row
        sheet.insert_rows(insert_row)
        self._write_item_row(sheet, insert_row, item)

        logger.debug(f"Added position to deal {deal_key}: {item.product_name}")
        return self

    def remove_position(
        self,
        sheet_name: str,
        deal_key: str,
        position_number: int,
    ) -> "ExcelBuilder":
        """Remove a position from a deal by position number."""
        if sheet_name not in self._workbook.sheetnames:
            raise ValueError(f"Sheet '{sheet_name}' not found")

        sheet = self._workbook[sheet_name]
        deal_row = self._find_deal_row(sheet, deal_key, sheet_name)

        if deal_row is None:
            raise ValueError(f"Deal '{deal_key}' not found in sheet '{sheet_name}'")

        start_item, end_item = self._get_deal_items_range(sheet, deal_row)

        # Find position by number (1-indexed)
        current_pos = 1
        for row_idx in range(start_item, end_item + 1):
            if current_pos == position_number:
                sheet.delete_rows(row_idx)
                logger.debug(
                    f"Removed position {position_number} from deal {deal_key}"
                )
                return self
            current_pos += 1

        raise ValueError(
            f"Position {position_number} not found in deal '{deal_key}'"
        )

    def update_position_field(
        self,
        sheet_name: str,
        deal_key: str,
        position_number: int,
        field_name: str,
        value: Any,
    ) -> "ExcelBuilder":
        """Update a specific field of a position."""
        if sheet_name not in self._workbook.sheetnames:
            raise ValueError(f"Sheet '{sheet_name}' not found")

        sheet = self._workbook[sheet_name]
        deal_row = self._find_deal_row(sheet, deal_key, sheet_name)

        if deal_row is None:
            raise ValueError(f"Deal '{deal_key}' not found in sheet '{sheet_name}'")

        if field_name not in ITEM_COLUMN_INDICES:
            raise ValueError(f"Unknown item field: {field_name}")

        start_item, end_item = self._get_deal_items_range(sheet, deal_row)

        # Find position by number
        current_pos = 1
        for row_idx in range(start_item, end_item + 1):
            if current_pos == position_number:
                col = ITEM_COLUMN_INDICES[field_name] + 1
                sheet.cell(row=row_idx, column=col, value=value)
                logger.debug(
                    f"Updated position {position_number} field {field_name} = {value}"
                )
                return self
            current_pos += 1

        raise ValueError(
            f"Position {position_number} not found in deal '{deal_key}'"
        )

    def save(self, path: Path) -> Path:
        """Save workbook to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        self._workbook.save(str(path))
        logger.info(f"Saved Excel file: {path}")
        return path

    # ========== Private Helpers ==========

    def _write_deal_to_sheet(
        self, sheet: Worksheet, deal: DealData, period: str
    ) -> int:
        """Write a deal and its items to the sheet. Returns deal row index."""
        row = self._get_next_row(sheet)

        # Write deal (master) row
        sheet.cell(row=row, column=COLUMN_INDICES["client_name"] + 1, value=deal.client_name)
        sheet.cell(row=row, column=COLUMN_INDICES["invoice_info"] + 1, value=deal.invoice_info)
        sheet.cell(row=row, column=COLUMN_INDICES["is_shipped"] + 1, value=deal.is_shipped or "нет")
        sheet.cell(row=row, column=COLUMN_INDICES["upd_number"] + 1, value=deal.upd_number)
        sheet.cell(row=row, column=COLUMN_INDICES["is_paid"] + 1, value=deal.is_paid or "нет")
        sheet.cell(row=row, column=COLUMN_INDICES["total_revenue"] + 1, value=self._to_number(deal.total_revenue))
        sheet.cell(row=row, column=COLUMN_INDICES["total_margin"] + 1, value=self._to_number(deal.total_margin))
        sheet.cell(row=row, column=COLUMN_INDICES["seller"] + 1, value=deal.seller)
        sheet.cell(row=row, column=COLUMN_INDICES["total_cost"] + 1, value=self._to_number(deal.total_cost))
        sheet.cell(row=row, column=COLUMN_INDICES["kickback_amount"] + 1, value=self._to_number(deal.kickback_amount))

        deal_row = row

        # Write item (detail) rows
        for item in deal.items:
            row += 1
            self._write_item_row(sheet, row, item)

        return deal_row

    def _write_item_row(self, sheet: Worksheet, row: int, item: ItemData) -> None:
        """Write an item row to the sheet."""
        # Column A (client_name) should be empty for item rows
        sheet.cell(row=row, column=1, value=None)

        sheet.cell(row=row, column=ITEM_COLUMN_INDICES["product_name"] + 1, value=item.product_name)
        sheet.cell(row=row, column=ITEM_COLUMN_INDICES["quantity"] + 1, value=self._to_number(item.quantity))
        sheet.cell(row=row, column=ITEM_COLUMN_INDICES["purchase_price"] + 1, value=self._to_number(item.purchase_price))
        sheet.cell(row=row, column=ITEM_COLUMN_INDICES["sale_price"] + 1, value=self._to_number(item.sale_price))
        sheet.cell(row=row, column=ITEM_COLUMN_INDICES["revenue"] + 1, value=self._to_number(item.revenue))
        sheet.cell(row=row, column=ITEM_COLUMN_INDICES["margin"] + 1, value=self._to_number(item.margin))
        sheet.cell(row=row, column=ITEM_COLUMN_INDICES["cost"] + 1, value=self._to_number(item.cost))
        sheet.cell(row=row, column=ITEM_COLUMN_INDICES["supplier_name"] + 1, value=item.supplier_name)
        sheet.cell(row=row, column=ITEM_COLUMN_INDICES["pickup_date"] + 1, value=item.pickup_date)

    def _to_number(self, value: Optional[Decimal | float | int]) -> Optional[float]:
        """Convert Decimal to float for Excel."""
        if value is None:
            return None
        return float(value)


def create_base_state_file(output_path: Path) -> Path:
    """
    Create a base state Excel file with sample data for testing.

    Returns path to created file.
    """
    builder = ExcelBuilder.create_new()

    # Add May 2025 sheet with sample deals
    may_deals = [
        DealData(
            client_name="ЛЕНТЕХСТРОЙ",
            invoice_info="5938 от 16.05.2025",
            invoice_number="5938",
            invoice_date="16.05.2025",
            seller="КРЕПЕЖ-ИНСТРУМЕНТ ООО",
            is_shipped="нет",
            is_paid="нет",
            total_revenue=Decimal("145270.00"),
            total_margin=Decimal("29713.68"),
            total_cost=Decimal("30536.32"),
            items=[
                ItemData(
                    product_name="Нож строительный КВТ",
                    quantity=Decimal("20"),
                    purchase_price=Decimal("100.50"),
                    sale_price=Decimal("356"),
                    revenue=Decimal("7120"),
                    margin=Decimal("5110"),
                    cost=Decimal("2010"),
                    supplier_name="ЭТМ",
                    pickup_date="18",
                ),
                ItemData(
                    product_name="Перчатки рабочие",
                    quantity=Decimal("100"),
                    purchase_price=Decimal("25.00"),
                    sale_price=Decimal("45"),
                    revenue=Decimal("4500"),
                    margin=Decimal("2000"),
                    cost=Decimal("2500"),
                    supplier_name="ЭТМ",
                    pickup_date="18",
                ),
            ],
        ),
        DealData(
            client_name="ООО СТРОЙКА",
            invoice_info="5939 от 17.05.2025",
            invoice_number="5939",
            invoice_date="17.05.2025",
            seller="КРЕПЕЖ-ИНСТРУМЕНТ ООО",
            is_shipped="да",
            is_paid="да",
            total_revenue=Decimal("50000.00"),
            total_margin=Decimal("10000.00"),
            total_cost=Decimal("40000.00"),
            items=[
                ItemData(
                    product_name="Дрель электрическая",
                    quantity=Decimal("5"),
                    purchase_price=Decimal("2000.00"),
                    sale_price=Decimal("2500"),
                    revenue=Decimal("12500"),
                    margin=Decimal("2500"),
                    cost=Decimal("10000"),
                    supplier_name="ИНСТРУМЕНТ-СЕРВИС",
                    pickup_date="17",
                ),
            ],
        ),
    ]

    builder.add_sheet("Май 2025", may_deals)

    # Add April 2025 sheet
    april_deals = [
        DealData(
            client_name="ООО РЕМОНТ",
            invoice_info="5900 от 10.04.2025",
            invoice_number="5900",
            invoice_date="10.04.2025",
            seller="КРЕПЕЖ-ИНСТРУМЕНТ ООО",
            is_shipped="да",
            is_paid="да",
            total_revenue=Decimal("25000.00"),
            total_margin=Decimal("5000.00"),
            total_cost=Decimal("20000.00"),
            items=[
                ItemData(
                    product_name="Краска фасадная",
                    quantity=Decimal("10"),
                    purchase_price=Decimal("1500.00"),
                    sale_price=Decimal("2000"),
                    revenue=Decimal("20000"),
                    margin=Decimal("5000"),
                    cost=Decimal("15000"),
                    supplier_name="КРАСКИ-ЛАКИ",
                    pickup_date="11",
                ),
                ItemData(
                    product_name="Кисти малярные",
                    quantity=Decimal("50"),
                    purchase_price=Decimal("100.00"),
                    sale_price=Decimal("150"),
                    revenue=Decimal("7500"),
                    margin=Decimal("2500"),
                    cost=Decimal("5000"),
                    supplier_name="КРАСКИ-ЛАКИ",
                    pickup_date="11",
                ),
            ],
        ),
    ]

    builder.add_sheet("Апрель 2025", april_deals)

    return builder.save(output_path)

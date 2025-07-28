"""
Excel Parser Application Service.

Refactored version of the original excel_parser.py using domain models and modern architecture.
"""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal
from pathlib import Path

import pandas as pd
from loguru import logger

from domain.exceptions import SyncFileError
from domain.models import Deal, DealItem, SyncSession
from domain.value_objects import Money, SignedMoney, Period, Status

from .models import ParseResult, ParseStats


class ExcelParserService:
    """
    Excel parser application service.

    Refactored version of the original ExcelParser using domain models
    and following clean architecture principles.
    """

    def __init__(self) -> None:
        """Initialize parser service."""
        self.stats = ParseStats()

    async def parse_file(self, file_path: str, sync_session: SyncSession) -> ParseResult:
        """
        Parse Excel file and return structured result.

        Args:
            file_path: Path to Excel file
            sync_session: Associated sync session

        Returns:
            ParseResult with deals and statistics

        Raises:
            SyncFileError: If file cannot be read or processed
        """
        logger.info(f"Starting Excel file parsing: {file_path}")

        try:
            # Validate file existence and get metadata
            file_info = self._get_file_info(file_path)

            # Read Excel sheets
            sheets_data = self._read_excel_file(file_path)
            self.stats.total_sheets = len(sheets_data)

            all_deals = []

            # Process each sheet
            for sheet_name, df in sheets_data.items():
                logger.info(f"Processing sheet: {sheet_name}")
                try:
                    deals = await self._parse_sheet(df, sheet_name.strip())
                    all_deals.extend(deals)
                    self.stats.processed_sheets += 1
                    logger.info(f"✅ Sheet '{sheet_name}': found {len(deals)} deals")
                except Exception as e:
                    self.stats.failed_sheets += 1
                    error_msg = f"Error processing sheet '{sheet_name}': {str(e)}"
                    self.stats.errors.append(error_msg)
                    logger.error(error_msg)
                    continue

            # Update sync session statistics
            sync_session.stats.total_deals = self.stats.total_deals
            sync_session.stats.processed_deals = self.stats.processed_deals
            sync_session.stats.failed_deals = self.stats.failed_deals
            sync_session.stats.total_items = self.stats.total_items
            sync_session.stats.processed_items = self.stats.processed_items
            sync_session.stats.failed_items = self.stats.failed_items
            sync_session.stats.errors.extend(self.stats.errors)
            sync_session.stats.warnings.extend(self.stats.warnings)

            # Create result
            result = ParseResult(
                deals=all_deals,
                stats=self.stats,
                sync_session=sync_session,
                file_path=file_path,
                file_size=file_info["size"],
                file_hash=file_info["hash"],
            )

            logger.info(f"Parsing completed. Total deals: {len(all_deals)}")
            self._log_final_stats()

            return result

        except Exception as e:
            # If it's already a SyncFileError, just re-raise it
            if isinstance(e, SyncFileError):
                raise

            error_msg = f"Critical error parsing file '{file_path}': {str(e)}"
            logger.error(error_msg)
            self.stats.errors.append(error_msg)
            raise SyncFileError(file_path, error_msg) from e

    def _get_file_info(self, file_path: str) -> dict:
        """Get file metadata for validation."""
        path = Path(file_path)

        if not path.exists():
            raise SyncFileError(file_path, "File does not exist")

        if not path.is_file():
            raise SyncFileError(file_path, "Path is not a file")

        # Calculate file hash
        with open(file_path, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()

        return {"size": path.stat().st_size, "hash": file_hash}

    def _read_excel_file(self, file_path: str) -> dict:
        """Read Excel file and return sheets data."""
        try:
            return pd.read_excel(file_path, sheet_name=None, header=None)
        except Exception as e:
            raise SyncFileError(file_path, f"Cannot read Excel file: {str(e)}") from e

    async def _parse_sheet(self, df: pd.DataFrame, sheet_name: str) -> list[Deal]:
        """Parse individual Excel sheet."""
        if df.empty:
            self.stats.warnings.append(f"Sheet '{sheet_name}' is empty")
            return []

        # Find header row
        header_row = self._find_header_row(df)
        if header_row is None:
            self.stats.warnings.append(f"No header row found in sheet '{sheet_name}', using row 1")
            header_row = 1

        if len(df) <= header_row:
            self.stats.errors.append(f"Sheet '{sheet_name}' has insufficient rows")
            return []

        logger.info(f"Sheet '{sheet_name}': header row at {header_row}")

        try:
            # Set headers and data
            df.columns = df.iloc[header_row]
            data_df = df.iloc[header_row + 1 :].reset_index(drop=True)
        except Exception as e:
            self.stats.errors.append(f"Error setting headers for sheet '{sheet_name}': {str(e)}")
            return []

        # Extract period from sheet name
        try:
            period = Period.from_sheet_name(sheet_name)
        except Exception as e:
            self.stats.errors.append(f"Cannot parse period from sheet '{sheet_name}': {str(e)}")
            return []

        # Parse deals
        return await self._parse_deals(data_df, period)

    def _find_header_row(self, df: pd.DataFrame) -> int | None:
        """Find row containing headers."""
        try:
            for i in range(min(5, len(df))):
                try:
                    row = df.iloc[i]
                    for val in row:
                        if pd.notna(val) and "Клиент" in str(val):
                            return i
                except Exception:
                    continue
            return None
        except Exception:
            return None

    async def _parse_deals(self, df: pd.DataFrame, period: Period) -> list[Deal]:
        """Parse deals from DataFrame."""
        deals = []
        current_deal = None
        row_counter = 0

        try:
            # Get column names and handle NaN
            columns = self._normalize_columns(df.columns)
            df.columns = columns

            client_col = columns[0] if len(columns) > 0 else None
            if client_col is None:
                self.stats.warnings.append("No client column found")
                return []

            logger.info(f"Columns: {columns}")

            for _, row in df.iterrows():
                row_counter += 1
                try:
                    client_value = row[client_col]

                    if pd.notna(client_value) and str(client_value).strip():
                        # Master record - new deal
                        if current_deal is not None:
                            # Finalize previous deal
                            try:
                                current_deal.calculate_totals()
                                deals.append(current_deal)
                                self.stats.processed_deals += 1
                            except Exception as e:
                                self.stats.failed_deals += 1
                                error_msg = f"Error calculating totals for deal '{current_deal.client_name}' (row {row_counter}): {str(e)}"
                                self.stats.errors.append(error_msg)

                        # Create new deal
                        try:
                            current_deal = await self._create_deal_from_row(row, columns, period)
                            self.stats.total_deals += 1
                        except Exception as e:
                            self.stats.failed_deals += 1
                            error_msg = f"Error creating deal from row {row_counter}: {str(e)}"
                            self.stats.errors.append(error_msg)
                            # Create minimal deal to maintain structure
                            current_deal = self._create_error_deal(
                                f"ERROR_ROW_{row_counter}", period
                            )

                    elif current_deal is not None:
                        # Detail record - item
                        try:
                            item = await self._create_item_from_row(row, columns)
                            if item and item.product_name.strip():
                                current_deal.add_item(item)
                                self.stats.processed_items += 1
                            self.stats.total_items += 1
                        except Exception as e:
                            self.stats.failed_items += 1
                            error_msg = f"Error creating item from row {row_counter} for deal '{current_deal.client_name}': {str(e)}"
                            self.stats.errors.append(error_msg)
                            # Add error item to maintain structure
                            error_item = DealItem(product_name=f"ERROR_ROW_{row_counter}")
                            current_deal.add_item(error_item)

                except Exception as e:
                    error_msg = f"Critical error processing row {row_counter}: {str(e)}"
                    self.stats.errors.append(error_msg)
                    logger.error(error_msg)
                    continue

            # Add last deal
            if current_deal is not None:
                try:
                    current_deal.calculate_totals()
                    deals.append(current_deal)
                    self.stats.processed_deals += 1
                except Exception as e:
                    self.stats.failed_deals += 1
                    error_msg = f"Error finalizing last deal '{current_deal.client_name}': {str(e)}"
                    self.stats.errors.append(error_msg)
                    # Add anyway
                    deals.append(current_deal)

            return deals

        except Exception as e:
            error_msg = f"Critical error parsing deals: {str(e)}"
            self.stats.errors.append(error_msg)
            logger.error(error_msg)
            return deals

    def _normalize_columns(self, columns) -> list[str]:
        """Normalize column names and handle NaN values."""
        normalized = []
        for i, col in enumerate(columns):
            if pd.notna(col):
                normalized.append(str(col).strip())
            else:
                normalized.append(f"col_{i}")
        return normalized

    async def _create_deal_from_row(
        self, row: pd.Series, columns: list[str], period: Period
    ) -> Deal:
        """Create Deal from master record row."""

        def safe_get(col_idx: int, default=None):
            try:
                if col_idx < len(columns) and columns[col_idx] in row.index:
                    val = row[columns[col_idx]]
                    return val if pd.notna(val) else default
                return default
            except (KeyError, TypeError):
                return default

        # Extract basic fields
        client_name = self._safe_string(safe_get(0)) or "UNKNOWN_CLIENT"
        invoice_info = self._safe_string(safe_get(1))
        invoice_number, invoice_date = self._parse_invoice_info(invoice_info)

        # Create deal with required fields
        deal = Deal(
            client_name=client_name,
            invoice_info=invoice_info,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            period=period,
        )

        # Optional fields
        try:
            if len(columns) > 2:
                is_shipped_raw = self._safe_string(safe_get(2))
                deal.is_shipped = Status.from_string(is_shipped_raw)

            if len(columns) > 3:
                deal.upd_number = self._safe_string(safe_get(3))

            if len(columns) > 4:
                is_paid_raw = self._safe_string(safe_get(4))
                deal.is_paid = Status.from_string(is_paid_raw)

            if len(columns) > 5:
                revenue_val = safe_get(5)
                if revenue_val is not None:
                    deal.total_revenue = Money(amount=Decimal(str(revenue_val)))

            if len(columns) > 6:
                margin_val = safe_get(6)
                if margin_val is not None:
                    deal.total_margin = SignedMoney(amount=Decimal(str(margin_val)))

            if len(columns) > 7:
                deal.seller = self._safe_string(safe_get(7))

            if len(columns) > 8:
                cost_val = safe_get(8)
                if cost_val is not None:
                    deal.total_cost = Money(amount=Decimal(str(cost_val)))

            if len(columns) > 9:
                kickback_val = safe_get(9)
                if kickback_val is not None:
                    deal.kickback_amount = Money(amount=Decimal(str(kickback_val)))

        except Exception as e:
            warning_msg = f"Warning parsing optional fields for deal '{client_name}': {str(e)}"
            self.stats.warnings.append(warning_msg)
            logger.warning(warning_msg)

        return deal

    async def _create_item_from_row(self, row: pd.Series, columns: list[str]) -> DealItem | None:
        """Create DealItem from detail record row."""

        def safe_get(col_idx: int, default=None):
            try:
                if col_idx < len(columns) and columns[col_idx] in row.index:
                    val = row[columns[col_idx]]
                    return val if pd.notna(val) else default
                return default
            except (KeyError, TypeError):
                return default

        # Check if we have product name
        product_name = self._safe_string(safe_get(1))
        if not product_name:
            return None

        item = DealItem(product_name=product_name)

        try:
            # Quantity
            if len(columns) > 2:
                qty_val = safe_get(2)
                if qty_val is not None:
                    item.quantity = Decimal(str(qty_val))

            # Purchase price
            if len(columns) > 3:
                purchase_val = safe_get(3)
                if purchase_val is not None:
                    item.purchase_price = Money(amount=Decimal(str(purchase_val)))

            # Sale price
            if len(columns) > 4:
                sale_val = safe_get(4)
                if sale_val is not None:
                    item.sale_price = Money(amount=Decimal(str(sale_val)))

            # Revenue
            if len(columns) > 5:
                revenue_val = safe_get(5)
                if revenue_val is not None:
                    item.revenue = Money(amount=Decimal(str(revenue_val)))

            # Margin
            if len(columns) > 6:
                margin_val = safe_get(6)
                if margin_val is not None:
                    item.margin = SignedMoney(amount=Decimal(str(margin_val)))

            # Cost
            if len(columns) > 8:
                cost_val = safe_get(8)
                if cost_val is not None:
                    item.cost = Money(amount=Decimal(str(cost_val)))

            # Supplier
            if len(columns) > 9:
                item.supplier_name = self._safe_string(safe_get(9))

            # Pickup date
            if len(columns) > 10:
                item.pickup_date = self._safe_pickup_date(safe_get(10))

            # Calculate missing fields
            item.calculate_fields()

        except Exception as e:
            warning_msg = f"Warning parsing item fields for '{product_name}': {str(e)}"
            self.stats.warnings.append(warning_msg)
            logger.warning(warning_msg)

        return item

    def _create_error_deal(self, client_name: str, period: Period) -> Deal:
        """Create minimal deal for error cases."""
        return Deal(client_name=client_name, invoice_info="", period=period)

    @staticmethod
    def _safe_string(value) -> str:
        """Safely convert value to string."""
        if pd.isna(value) or value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _safe_pickup_date(value) -> str:
        """Safely convert pickup date with proper number formatting."""
        if pd.isna(value) or value is None:
            return ""

        try:
            num_value = float(value)
            if num_value.is_integer():
                return str(int(num_value))
            else:
                return str(num_value).strip()
        except (ValueError, TypeError):
            return str(value).strip()

    @staticmethod
    def _parse_invoice_info(invoice_info: str) -> tuple[str, str]:
        """Parse invoice information and return number and date."""
        try:
            if not invoice_info:
                return "", ""

            info = str(invoice_info).strip()

            # Pattern: number + "от" + date
            pattern = r"(\d+)\s+от\s+(\d{1,2}\.\d{1,2}\.\d{4})"
            match = re.search(pattern, info)

            if match:
                return match.group(1), match.group(2)

            # Alternative pattern: number + space + date
            pattern2 = r"(\d+)\s+(\d{1,2}\.\d{1,2}\.\d{4})"
            match2 = re.search(pattern2, info)

            if match2:
                return match2.group(1), match2.group(2)

            return "", ""

        except Exception:
            return "", ""

    def _log_final_stats(self) -> None:
        """Log final parsing statistics."""
        logger.info("=" * 80)
        logger.info("PARSING STATISTICS")
        logger.info("=" * 80)

        logger.info(f"📋 SHEETS: {self.stats.processed_sheets}/{self.stats.total_sheets} processed")
        logger.info(f"🏢 DEALS: {self.stats.processed_deals}/{self.stats.total_deals} processed")
        logger.info(f"📦 ITEMS: {self.stats.processed_items}/{self.stats.total_items} processed")

        if self.stats.errors:
            logger.warning(f"❌ ERRORS: {len(self.stats.errors)}")
            for error in self.stats.errors[:5]:  # Show first 5
                logger.warning(f"  - {error}")

        if self.stats.warnings:
            logger.warning(f"⚠️ WARNINGS: {len(self.stats.warnings)}")
            for warning in self.stats.warnings[:3]:  # Show first 3
                logger.warning(f"  - {warning}")

        logger.info(
            f"📊 Success rates: Sheets {self.stats.success_rate_sheets:.1f}%, Deals {self.stats.success_rate_deals:.1f}%, Items {self.stats.success_rate_items:.1f}%"
        )
        logger.info("=" * 80)

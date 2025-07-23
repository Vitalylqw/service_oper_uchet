"""
Data validator for Excel files.

Validates Excel data structure, business logic and financial consistency.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

from ...application.excel_parser import ParseResult
from ...domain.models import Deal, DealItem
from .models import ErrorSeverity, ValidationError, ValidationResult


class DataValidator:
    """
    Data validator for Excel files and parsed deals.

    Performs comprehensive validation including:
    - Excel structure validation
    - Business logic validation
    - Financial consistency checks
    - Data completeness validation
    """

    def __init__(self):
        """Initialize validator."""
        self._expected_headers = self._get_expected_headers()
        logger.info("DataValidator initialized")

    def validate_excel_file(self, file_path: str | Path) -> ValidationResult:
        """
        Validate Excel file structure before parsing.

        Args:
            file_path: Path to Excel file

        Returns:
            ValidationResult with structure validation results
        """
        file_path = Path(file_path)
        result = ValidationResult(is_valid=True, file_path=str(file_path))

        logger.info(f"Starting Excel structure validation for: {file_path}")

        try:
            # Проверяем существование файла
            if not file_path.exists():
                result.add_error(
                    ValidationError(
                        severity=ErrorSeverity.CRITICAL,
                        code="FILE_NOT_FOUND",
                        message=f"Файл не найден: {file_path}",
                    )
                )
                return result

            # Проверяем расширение файла
            if file_path.suffix.lower() not in {".xlsx", ".xls"}:
                result.add_error(
                    ValidationError(
                        severity=ErrorSeverity.CRITICAL,
                        code="INVALID_FILE_FORMAT",
                        message=f"Неподдерживаемый формат файла: {file_path.suffix}",
                    )
                )
                return result

            # Загружаем Excel файл
            try:
                excel_file = pd.ExcelFile(file_path)
                sheet_names = excel_file.sheet_names
                result.stats.total_sheets = len(sheet_names)
            except Exception as e:
                result.add_error(
                    ValidationError(
                        severity=ErrorSeverity.CRITICAL,
                        code="FILE_READ_ERROR",
                        message=f"Ошибка чтения Excel файла: {str(e)}",
                    )
                )
                return result

            # Валидируем каждый лист
            for sheet_name in sheet_names:
                self._validate_sheet_structure(excel_file, sheet_name, result)

            logger.info(f"Excel structure validation completed: {result.summary}")
            return result

        except Exception as e:
            logger.error(f"Unexpected error during Excel validation: {e}")
            result.add_error(
                ValidationError(
                    severity=ErrorSeverity.CRITICAL,
                    code="VALIDATION_ERROR",
                    message=f"Неожиданная ошибка валидации: {str(e)}",
                )
            )
            return result

    def validate_parsed_data(self, parse_result: ParseResult) -> ValidationResult:
        """
        Validate parsed deals data.

        Args:
            parse_result: Result from Excel parser

        Returns:
            ValidationResult with business logic validation results
        """
        result = ValidationResult(is_valid=True, file_path=parse_result.file_path)

        logger.info(f"Starting business logic validation for {len(parse_result.deals)} deals")

        result.stats.total_deals = len(parse_result.deals)

        for deal in parse_result.deals:
            self._validate_deal(deal, result)

        logger.info(f"Business logic validation completed: {result.summary}")
        return result

    def _validate_sheet_structure(
        self, excel_file: pd.ExcelFile, sheet_name: str, result: ValidationResult
    ) -> None:
        """Validate individual sheet structure."""
        try:
            # Читаем первые несколько строк для проверки заголовков
            df = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=5)

            if df.empty:
                result.add_error(
                    ValidationError(
                        severity=ErrorSeverity.WARNING,
                        code="EMPTY_SHEET",
                        message=f"Лист '{sheet_name}' пустой",
                        sheet_name=sheet_name,
                    )
                )
                return

            # Проверяем наличие обязательных заголовков
            self._validate_headers(df, sheet_name, result)

            result.stats.valid_sheets += 1

        except Exception as e:
            result.add_error(
                ValidationError(
                    severity=ErrorSeverity.ERROR,
                    code="SHEET_READ_ERROR",
                    message=f"Ошибка чтения листа '{sheet_name}': {str(e)}",
                    sheet_name=sheet_name,
                )
            )

    def _validate_headers(
        self, df: pd.DataFrame, sheet_name: str, result: ValidationResult
    ) -> None:
        """Validate Excel headers structure."""
        actual_headers = [str(col).strip().lower() for col in df.columns if pd.notna(col)]

        # Проверяем наличие основных заголовков
        missing_headers = []
        for expected_header in self._expected_headers:
            if not any(expected_header.lower() in actual for actual in actual_headers):
                missing_headers.append(expected_header)

        if missing_headers:
            result.add_error(
                ValidationError(
                    severity=ErrorSeverity.ERROR,
                    code="MISSING_HEADERS",
                    message=f"Отсутствуют обязательные заголовки: {', '.join(missing_headers)}",
                    sheet_name=sheet_name,
                    context={"missing_headers": missing_headers, "actual_headers": actual_headers},
                )
            )

    def _validate_deal(self, deal: Deal, result: ValidationResult) -> None:
        """Validate individual deal."""
        is_valid = True

        # Проверяем обязательные поля сделки
        if not deal.client_name or deal.client_name.strip() == "":
            result.add_error(
                ValidationError(
                    severity=ErrorSeverity.ERROR,
                    code="MISSING_CLIENT_NAME",
                    message="Отсутствует название клиента",
                    deal_key=deal.deal_key,
                )
            )
            is_valid = False

        if not deal.invoice_info or deal.invoice_info.strip() == "":
            result.add_error(
                ValidationError(
                    severity=ErrorSeverity.WARNING,
                    code="MISSING_INVOICE_INFO",
                    message="Отсутствует информация о счете",
                    deal_key=deal.deal_key,
                )
            )

        # Валидируем позиции товаров
        if not deal.items:
            result.add_error(
                ValidationError(
                    severity=ErrorSeverity.WARNING,
                    code="NO_ITEMS",
                    message="Сделка не содержит позиций товаров",
                    deal_key=deal.deal_key,
                )
            )
        else:
            result.stats.total_items += len(deal.items)
            for item in deal.items:
                self._validate_deal_item(item, deal, result)

        # Валидируем финансовые показатели
        self._validate_financial_consistency(deal, result)

        if is_valid:
            result.stats.valid_deals += 1
        else:
            result.stats.invalid_deals += 1

    def _validate_deal_item(self, item: DealItem, deal: Deal, result: ValidationResult) -> None:
        """Validate individual deal item."""
        is_valid = True

        # Проверяем название товара
        if not item.product_name or item.product_name.strip() == "":
            result.add_error(
                ValidationError(
                    severity=ErrorSeverity.ERROR,
                    code="MISSING_PRODUCT_NAME",
                    message="Отсутствует название товара",
                    deal_key=deal.deal_key,
                    item_key=item.item_key,
                )
            )
            is_valid = False

        # Проверяем числовые значения
        if item.quantity and item.quantity <= 0:
            result.add_error(
                ValidationError(
                    severity=ErrorSeverity.WARNING,
                    code="INVALID_QUANTITY",
                    message=f"Некорректное количество товара: {item.quantity}",
                    deal_key=deal.deal_key,
                    item_key=item.item_key,
                    cell_value=item.quantity,
                    expected_value="> 0",
                )
            )

        # Проверяем цены
        if item.purchase_price and item.sale_price:
            if item.purchase_price.amount > item.sale_price.amount:
                result.add_error(
                    ValidationError(
                        severity=ErrorSeverity.WARNING,
                        code="NEGATIVE_MARGIN",
                        message="Цена закупки больше цены продажи (отрицательная маржа)",
                        deal_key=deal.deal_key,
                        item_key=item.item_key,
                        context={
                            "purchase_price": item.purchase_price.amount,
                            "sale_price": item.sale_price.amount,
                        },
                    )
                )

        if is_valid:
            result.stats.valid_items += 1
        else:
            result.stats.invalid_items += 1

    def _validate_financial_consistency(self, deal: Deal, result: ValidationResult) -> None:
        """Validate financial consistency within deal."""
        if not deal.items:
            return

        # Проверяем соответствие итоговых сумм расчетным
        calculated_revenue = sum(item.revenue.amount for item in deal.items if item.revenue)
        calculated_margin = sum(item.margin.amount for item in deal.items if item.margin)

        # Проверяем выручку
        if deal.total_revenue and calculated_revenue > 0:
            diff = abs(deal.total_revenue.amount - calculated_revenue)
            if diff > 0.01:  # Допускаем погрешность в 1 копейку
                result.add_error(
                    ValidationError(
                        severity=ErrorSeverity.WARNING,
                        code="REVENUE_MISMATCH",
                        message=f"Несоответствие общей выручки: заявлено {deal.total_revenue.amount}, "
                        f"рассчитано {calculated_revenue}, разница {diff}",
                        deal_key=deal.deal_key,
                        context={
                            "declared_revenue": deal.total_revenue.amount,
                            "calculated_revenue": calculated_revenue,
                            "difference": diff,
                        },
                    )
                )

        # Проверяем маржу
        if deal.total_margin and calculated_margin > 0:
            diff = abs(deal.total_margin.amount - calculated_margin)
            if diff > 0.01:
                result.add_error(
                    ValidationError(
                        severity=ErrorSeverity.WARNING,
                        code="MARGIN_MISMATCH",
                        message=f"Несоответствие общей маржи: заявлено {deal.total_margin.amount}, "
                        f"рассчитано {calculated_margin}, разница {diff}",
                        deal_key=deal.deal_key,
                        context={
                            "declared_margin": deal.total_margin.amount,
                            "calculated_margin": calculated_margin,
                            "difference": diff,
                        },
                    )
                )

    def _get_expected_headers(self) -> list[str]:
        """Get list of expected Excel headers."""
        return [
            "Клиент",
            "Продавец",
            "Счет",
            "Номер счета",
            "Дата счета",
            "УПД",
            "Отгружен",
            "Оплачен",
            "Выручка",
            "Маржа",
            "Стоимость",
            "Товар",
            "Поставщик",
            "Количество",
            "Цена закупки",
            "Цена продажи",
        ]

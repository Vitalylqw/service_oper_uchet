"""
Unit tests for data validator.

Tests Excel structure validation, business logic validation and financial consistency checks.
"""

from __future__ import annotations

import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.application.data_validator import (
    DataValidator,
    ErrorSeverity,
    ValidationError,
    ValidationResult,
    ValidationWarning,
)
from src.application.excel_parser import ParseResult
from src.domain.models import Deal, DealItem, SyncSession, SyncType
from src.domain.value_objects import Money, Period, Status


# Global fixtures available to all test classes
@pytest.fixture
def validator():
    """Create DataValidator instance."""
    return DataValidator()


@pytest.fixture
def sample_deal():
    """Create sample valid deal."""
    item1 = DealItem(
        product_name="Товар 1",
        supplier_name="Поставщик 1",
        quantity=Decimal("10"),
        purchase_price=Money(amount=Decimal("100")),
        sale_price=Money(amount=Decimal("150")),
        revenue=Money(amount=Decimal("1500")),
        cost=Money(amount=Decimal("1000")),
        margin=Money(amount=Decimal("500")),
    )

    item2 = DealItem(
        product_name="Товар 2",
        supplier_name="Поставщик 2",
        quantity=Decimal("5"),
        purchase_price=Money(amount=Decimal("200")),
        sale_price=Money(amount=Decimal("300")),
        revenue=Money(amount=Decimal("1500")),
        cost=Money(amount=Decimal("1000")),
        margin=Money(amount=Decimal("500")),
    )

    deal = Deal(
        client_name="Тестовый клиент",
        seller="Тестовый продавец",
        invoice_info="Счет №123 от 01.01.2025",
        invoice_number="123",
        invoice_date="01.01.2025",
        is_shipped=Status.SHIPPED,
        is_paid=Status.PAID,
        total_revenue=Money(amount=Decimal("3000")),
        total_cost=Money(amount=Decimal("2000")),
        total_margin=Money(amount=Decimal("1000")),
        period=Period(month="Январь", year="2025", full_name="Январь 2025"),
        items=[item1, item2],
    )

    return deal


@pytest.fixture
def sample_parse_result(sample_deal):
    """Create sample ParseResult."""
    sync_session = SyncSession(
        session_id="test-session", sync_type=SyncType.FULL, started_at="2025-01-01T10:00:00"
    )

    return ParseResult(
        deals=[sample_deal],
        sync_session=sync_session,
        file_path="/test/file.xlsx",
        file_size=1024,
        file_hash="testhash",
    )


class TestDataValidator:
    """Test cases for DataValidator class."""


class TestDataValidatorFileValidation:
    """Test Excel file structure validation."""

    def test_validate_nonexistent_file(self, validator):
        """Test validation of non-existent file."""
        result = validator.validate_excel_file("/nonexistent/file.xlsx")

        assert not result.is_valid
        assert result.has_critical_errors

        errors = result.get_errors_by_severity(ErrorSeverity.CRITICAL)
        assert len(errors) == 1
        assert errors[0].code == "FILE_NOT_FOUND"
        assert "Файл не найден" in errors[0].message

    def test_validate_invalid_file_format(self, validator):
        """Test validation of invalid file format."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name

        try:
            result = validator.validate_excel_file(tmp_path)

            assert not result.is_valid
            assert result.has_critical_errors

            errors = result.get_errors_by_severity(ErrorSeverity.CRITICAL)
            assert len(errors) == 1
            assert errors[0].code == "INVALID_FILE_FORMAT"
            assert "Неподдерживаемый формат файла" in errors[0].message
        finally:
            Path(tmp_path).unlink()

    @patch("pandas.ExcelFile")
    def test_validate_excel_read_error(self, mock_excel_file, validator):
        """Test handling of Excel read errors."""
        mock_excel_file.side_effect = Exception("Excel read error")

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = validator.validate_excel_file(tmp_path)

            assert not result.is_valid
            assert result.has_critical_errors

            errors = result.get_errors_by_severity(ErrorSeverity.CRITICAL)
            assert len(errors) == 1
            assert errors[0].code == "FILE_READ_ERROR"
            assert "Ошибка чтения Excel файла" in errors[0].message
        finally:
            Path(tmp_path).unlink()

    @patch("pandas.ExcelFile")
    @patch("pandas.read_excel")
    def test_validate_valid_excel_structure(self, mock_read_excel, mock_excel_file, validator):
        """Test validation of valid Excel structure."""
        # Мокаем ExcelFile
        mock_file = Mock()
        mock_file.sheet_names = ["Sheet1", "Sheet2"]
        mock_excel_file.return_value = mock_file

        # Мокаем DataFrame с правильными заголовками
        mock_df = pd.DataFrame(
            {
                "Клиент": ["Тест"],
                "Продавец": ["Тест"],
                "Счет": ["123"],
                "Номер счета": ["123"],
                "Дата счета": ["01.01.2025"],
                "УПД": ["УПД123"],
                "Отгружен": ["Да"],
                "Оплачен": ["Нет"],
                "Выручка": ["1000"],
                "Маржа": ["500"],
                "Стоимость": ["500"],
                "Товар": ["Товар1"],
                "Поставщик": ["Поставщик1"],
                "Количество": ["10"],
                "Цена закупки": ["50"],
                "Цена продажи": ["100"],
            }
        )
        mock_read_excel.return_value = mock_df

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = validator.validate_excel_file(tmp_path)

            assert result.is_valid
            assert not result.has_critical_errors
            assert result.stats.total_sheets == 2
            assert result.stats.valid_sheets == 2
        finally:
            Path(tmp_path).unlink()

    @patch("pandas.ExcelFile")
    @patch("pandas.read_excel")
    def test_validate_missing_headers(self, mock_read_excel, mock_excel_file, validator):
        """Test detection of missing headers."""
        # Мокаем ExcelFile
        mock_file = Mock()
        mock_file.sheet_names = ["Sheet1"]
        mock_excel_file.return_value = mock_file

        # Мокаем DataFrame с неполными заголовками
        mock_df = pd.DataFrame({"Неизвестная колонка": ["Тест"], "Еще одна": ["Тест"]})
        mock_read_excel.return_value = mock_df

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = validator.validate_excel_file(tmp_path)

            assert not result.is_valid
            assert result.has_errors

            errors = result.get_errors_by_severity(ErrorSeverity.ERROR)
            header_errors = [e for e in errors if e.code == "MISSING_HEADERS"]
            assert len(header_errors) == 1
            assert "Отсутствуют обязательные заголовки" in header_errors[0].message
        finally:
            Path(tmp_path).unlink()

    @patch("pandas.ExcelFile")
    @patch("pandas.read_excel")
    def test_validate_empty_sheet(self, mock_read_excel, mock_excel_file, validator):
        """Test handling of empty sheets."""
        # Мокаем ExcelFile
        mock_file = Mock()
        mock_file.sheet_names = ["EmptySheet"]
        mock_excel_file.return_value = mock_file

        # Мокаем пустой DataFrame
        mock_read_excel.return_value = pd.DataFrame()

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = validator.validate_excel_file(tmp_path)

            assert result.is_valid  # Пустые листы не критичны
            assert result.has_warnings

            warnings = result.get_errors_by_severity(ErrorSeverity.WARNING)
            empty_warnings = [w for w in warnings if w.code == "EMPTY_SHEET"]
            assert len(empty_warnings) == 1
            assert "пустой" in empty_warnings[0].message
        finally:
            Path(tmp_path).unlink()


class TestDataValidatorBusinessLogic:
    """Test business logic validation."""

    def test_validate_valid_deal(self, validator, sample_parse_result):
        """Test validation of valid deal."""
        result = validator.validate_parsed_data(sample_parse_result)

        assert result.is_valid
        assert result.stats.total_deals == 1
        assert result.stats.valid_deals == 1
        assert result.stats.invalid_deals == 0
        assert result.stats.total_items == 2
        assert result.stats.valid_items == 2

    def test_validate_deal_missing_client_name(self, validator, sample_parse_result):
        """Test validation of deal with missing client name."""
        sample_parse_result.deals[0].client_name = ""

        result = validator.validate_parsed_data(sample_parse_result)

        assert not result.is_valid
        assert result.stats.invalid_deals == 1

        errors = result.get_errors_by_severity(ErrorSeverity.ERROR)
        client_errors = [e for e in errors if e.code == "MISSING_CLIENT_NAME"]
        assert len(client_errors) == 1

    def test_validate_deal_missing_invoice_info(self, validator, sample_parse_result):
        """Test validation of deal with missing invoice info."""
        sample_parse_result.deals[0].invoice_info = ""

        result = validator.validate_parsed_data(sample_parse_result)

        assert result.is_valid  # Это только предупреждение
        assert result.has_warnings

        warnings = result.get_errors_by_severity(ErrorSeverity.WARNING)
        invoice_warnings = [w for w in warnings if w.code == "MISSING_INVOICE_INFO"]
        assert len(invoice_warnings) == 1

    def test_validate_deal_no_items(self, validator, sample_parse_result):
        """Test validation of deal without items."""
        sample_parse_result.deals[0].items = []

        result = validator.validate_parsed_data(sample_parse_result)

        assert result.is_valid  # Это только предупреждение
        assert result.has_warnings

        warnings = result.get_errors_by_severity(ErrorSeverity.WARNING)
        no_items_warnings = [w for w in warnings if w.code == "NO_ITEMS"]
        assert len(no_items_warnings) == 1

    def test_validate_item_missing_product_name(self, validator, sample_parse_result):
        """Test validation of item with missing product name."""
        sample_parse_result.deals[0].items[0].product_name = ""

        result = validator.validate_parsed_data(sample_parse_result)

        assert not result.is_valid
        assert result.stats.invalid_items == 1

        errors = result.get_errors_by_severity(ErrorSeverity.ERROR)
        product_errors = [e for e in errors if e.code == "MISSING_PRODUCT_NAME"]
        assert len(product_errors) == 1

    def test_validate_item_invalid_quantity(self, validator, sample_parse_result):
        """Test validation of item with invalid quantity."""
        sample_parse_result.deals[0].items[0].quantity = Decimal("-5")

        result = validator.validate_parsed_data(sample_parse_result)

        assert result.is_valid  # Это только предупреждение
        assert result.has_warnings

        warnings = result.get_errors_by_severity(ErrorSeverity.WARNING)
        quantity_warnings = [w for w in warnings if w.code == "INVALID_QUANTITY"]
        assert len(quantity_warnings) == 1

    def test_validate_item_negative_margin(self, validator, sample_parse_result):
        """Test validation of item with negative margin."""
        item = sample_parse_result.deals[0].items[0]
        item.purchase_price = Money(amount=Decimal("200"))
        item.sale_price = Money(amount=Decimal("100"))

        result = validator.validate_parsed_data(sample_parse_result)

        assert result.is_valid  # Это только предупреждение
        assert result.has_warnings

        warnings = result.get_errors_by_severity(ErrorSeverity.WARNING)
        margin_warnings = [w for w in warnings if w.code == "NEGATIVE_MARGIN"]
        assert len(margin_warnings) == 1


class TestDataValidatorFinancialValidation:
    """Test financial consistency validation."""

    def test_validate_revenue_mismatch(self, validator, sample_parse_result):
        """Test detection of revenue mismatch."""
        # Устанавливаем неправильную общую выручку
        sample_parse_result.deals[0].total_revenue = Money(amount=Decimal("5000"))

        result = validator.validate_parsed_data(sample_parse_result)

        assert result.is_valid  # Это только предупреждение
        assert result.has_warnings

        warnings = result.get_errors_by_severity(ErrorSeverity.WARNING)
        revenue_warnings = [w for w in warnings if w.code == "REVENUE_MISMATCH"]
        assert len(revenue_warnings) == 1
        assert "Несоответствие общей выручки" in revenue_warnings[0].message

    def test_validate_margin_mismatch(self, validator, sample_parse_result):
        """Test detection of margin mismatch."""
        # Устанавливаем неправильную общую маржу
        sample_parse_result.deals[0].total_margin = Money(amount=Decimal("2000"))

        result = validator.validate_parsed_data(sample_parse_result)

        assert result.is_valid  # Это только предупреждение
        assert result.has_warnings

        warnings = result.get_errors_by_severity(ErrorSeverity.WARNING)
        margin_warnings = [w for w in warnings if w.code == "MARGIN_MISMATCH"]
        assert len(margin_warnings) == 1
        assert "Несоответствие общей маржи" in margin_warnings[0].message

    def test_validate_small_financial_differences_ignored(self, validator, sample_parse_result):
        """Test that small financial differences are ignored."""
        # Устанавливаем разницу в 1 копейку (должна игнорироваться)
        sample_parse_result.deals[0].total_revenue = Money(amount=Decimal("3000.01"))

        result = validator.validate_parsed_data(sample_parse_result)

        assert result.is_valid
        assert not result.has_warnings or not any(
            w.code == "REVENUE_MISMATCH"
            for w in result.get_errors_by_severity(ErrorSeverity.WARNING)
        )


class TestValidationModels:
    """Test validation models."""

    def test_validation_error_creation(self):
        """Test ValidationError creation and properties."""
        error = ValidationError(
            severity=ErrorSeverity.ERROR,
            code="TEST_ERROR",
            message="Test error message",
            sheet_name="Sheet1",
            row_number=5,
            column_name="Column A",
        )

        assert error.is_blocking
        assert error.location_info == "лист 'Sheet1', строка 5, колонка 'Column A'"
        assert error.code == "TEST_ERROR"
        assert "Test error message" in str(error)
        assert "[ERROR]" in str(error)

    def test_validation_warning_creation(self):
        """Test ValidationWarning convenience class."""
        warning = ValidationWarning(code="TEST_WARNING", message="Test warning message")

        assert warning.severity == ErrorSeverity.WARNING
        assert not warning.is_blocking

    def test_validation_result_statistics(self):
        """Test ValidationResult statistics."""
        result = ValidationResult(is_valid=True, file_path="/test/file.xlsx")

        # Добавляем различные типы ошибок
        result.add_error(
            ValidationError(
                severity=ErrorSeverity.CRITICAL, code="CRITICAL_ERROR", message="Critical error"
            )
        )

        result.add_error(
            ValidationError(severity=ErrorSeverity.ERROR, code="ERROR", message="Error")
        )

        result.add_warning("WARNING", "Warning message")

        assert not result.is_valid  # Должно стать False из-за критической ошибки
        assert result.stats.critical_errors == 1
        assert result.stats.errors == 1
        assert result.stats.warnings == 1
        assert result.stats.total_issues == 3
        assert result.has_critical_errors
        assert result.has_errors
        assert result.has_warnings

    def test_validation_result_filtering(self):
        """Test ValidationResult filtering methods."""
        result = ValidationResult(is_valid=True, file_path="/test/file.xlsx")

        # Добавляем ошибки с разными атрибутами
        result.add_error(
            ValidationError(
                severity=ErrorSeverity.ERROR,
                code="SHEET_ERROR",
                message="Sheet error",
                sheet_name="Sheet1",
            )
        )

        result.add_error(
            ValidationError(
                severity=ErrorSeverity.WARNING, code="GENERAL_WARNING", message="General warning"
            )
        )

        # Тестируем фильтрацию
        errors = result.get_errors_by_severity(ErrorSeverity.ERROR)
        assert len(errors) == 1
        assert errors[0].code == "SHEET_ERROR"

        sheet_errors = result.get_errors_by_sheet("Sheet1")
        assert len(sheet_errors) == 1
        assert sheet_errors[0].code == "SHEET_ERROR"

        blocking_errors = result.get_blocking_errors()
        assert len(blocking_errors) == 1
        assert blocking_errors[0].severity == ErrorSeverity.ERROR

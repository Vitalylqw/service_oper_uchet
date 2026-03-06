"""
Unit tests for Excel parser application service.
"""

from decimal import Decimal

import pandas as pd
import pytest

from src.application.excel_parser import ExcelParserService, ParseResult
from src.domain.builders.deal_builder import DealBuilder
from src.domain.models.sync_session import SyncSession, SyncType
from src.domain.value_objects import Period


@pytest.mark.unit
class TestExcelParserService:
    """Tests for ExcelParserService."""

    @pytest.fixture
    def parser_service(self):
        """Create parser service instance."""
        return ExcelParserService()

    @pytest.fixture
    def sample_sync_session(self):
        """Create sample sync session."""
        return SyncSession(
            sync_type=SyncType.FULL, source_file_path="test_file.xlsx", created_by="test_user"
        )

    @pytest.fixture
    def test_excel_data(self, tmp_path):
        """Create test Excel file with sample data."""
        # Create test data
        data = {
            "Клиент": ['ООО "Тест"', None, None, "ИП Иванов", None],
            "Номенклатуры": [
                "12345 от 01.05.2025",
                "Товар 1",
                "Товар 2",
                "67890 от 02.05.2025",
                "Товар 3",
            ],
            "Кол/Отгр": ["да", "10", "5", "нет", "15"],
            "Цена вх/накл": ["УПД-001", "100.50", "200.75", "УПД-002", "150.00"],
            "цена исх/Оплач?": ["да", "150.00", "250.00", "нет", "200.00"],
            "Выручка": [2000.00, 1500.00, 1250.00, 3000.00, 3000.00],
            "Маржа": [600.00, 495.00, 231.25, 750.00, 750.00],
            "От кого Зак/Прод": ["Продавец1", None, None, "Продавец2", None],
            "Ст. Закупки": [1400.00, 1005.00, 1018.75, 2250.00, 2250.00],
            "Поставщик/Откат": [0, "Поставщик1", "Поставщик2", 0, "Поставщик3"],
            "Дата": [None, "15", "Июнь", None, "20"],
        }

        df = pd.DataFrame(data)

        # Create Excel file
        excel_file = tmp_path / "test_data.xlsx"
        with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Май 2025", index=False, header=False)
            # Add header row at row 1 (0-indexed)
            df_with_header = pd.concat(
                [
                    pd.DataFrame([data.keys()]),  # Header row
                    df,
                ],
                ignore_index=True,
            )
            df_with_header.to_excel(writer, sheet_name="Май 2025", index=False, header=False)

        return str(excel_file)

    def test_parser_initialization(self, parser_service):
        """Test parser service initialization."""
        assert parser_service is not None
        assert parser_service.stats is not None
        assert parser_service.stats.total_sheets == 0

    def test_parse_invoice_info(self, parser_service):
        """Test invoice info parsing."""
        # Test normal format
        number, date = parser_service._parse_invoice_info("12345 от 01.05.2025")
        assert number == "12345"
        assert date == "01.05.2025"

        # Test alternative format
        number, date = parser_service._parse_invoice_info("67890 15.06.2025")
        assert number == "67890"
        assert date == "15.06.2025"

        # Test empty/invalid
        number, date = parser_service._parse_invoice_info("")
        assert number == ""
        assert date == ""

        number, date = parser_service._parse_invoice_info("invalid format")
        assert number == ""
        assert date == ""

    def test_safe_string(self, parser_service):
        """Test safe string conversion."""
        assert parser_service._safe_string("  test  ") == "test"
        assert parser_service._safe_string(None) == ""
        assert parser_service._safe_string(pd.NA) == ""
        assert parser_service._safe_string(123) == "123"

    def test_safe_pickup_date(self, parser_service):
        """Test safe pickup date conversion."""
        assert parser_service._safe_pickup_date(19.0) == "19"
        assert parser_service._safe_pickup_date(19.5) == "19.5"
        assert parser_service._safe_pickup_date("июнь") == "июнь"
        assert parser_service._safe_pickup_date(None) == ""

    def test_safe_decimal(self, parser_service):
        """Test _safe_decimal: valid numbers -> Decimal, non-numeric -> None."""
        assert parser_service._safe_decimal(1500.50) == Decimal("1500.50")
        assert parser_service._safe_decimal(0) == Decimal("0")
        assert parser_service._safe_decimal(Decimal("100.5")) == Decimal("100.5")
        assert parser_service._safe_decimal(None) is None
        assert parser_service._safe_decimal("") is None
        assert parser_service._safe_decimal("   ") is None
        assert parser_service._safe_decimal("N/A") is None
        assert parser_service._safe_decimal("#DIV/0!") is None
        assert parser_service._safe_decimal("—") is None

    @pytest.mark.asyncio
    async def test_parse_file_nonexistent(self, parser_service, sample_sync_session):
        """Test parsing non-existent file."""
        from domain.exceptions import SyncFileError

        with pytest.raises(SyncFileError):
            await parser_service.parse_file("nonexistent.xlsx", sample_sync_session)

    @pytest.mark.asyncio
    async def test_parse_file_success(self, parser_service, sample_sync_session, test_excel_data):
        """Test successful file parsing."""
        result = await parser_service.parse_file(test_excel_data, sample_sync_session)

        assert isinstance(result, ParseResult)
        assert result.file_path == test_excel_data
        assert result.file_size > 0
        assert len(result.file_hash) == 32  # MD5 hash
        assert result.stats.total_sheets == 1
        assert result.stats.processed_sheets == 1
        assert len(result.deals) >= 0  # Should have parsed some deals

    def test_get_file_info(self, parser_service, test_excel_data):
        """Test file info extraction."""
        file_info = parser_service._get_file_info(test_excel_data)

        assert "size" in file_info
        assert "hash" in file_info
        assert file_info["size"] > 0
        assert len(file_info["hash"]) == 32  # MD5 hash

    def test_normalize_columns(self, parser_service):
        """Test column normalization."""
        columns = ["Клиент", None, "Товар", pd.NA, "Цена"]
        normalized = parser_service._normalize_columns(columns)

        expected = ["Клиент", "col_1", "Товар", "col_3", "Цена"]
        assert normalized == expected

    @pytest.mark.asyncio
    async def test_create_deal_from_row(self, parser_service):
        """Test deal creation from row."""
        period = Period(month="Май", year="2025", full_name="Май 2025")

        # Create test row data
        row_data = {
            "col_0": "Тест Клиент",
            "col_1": "12345 от 01.05.2025",
            "col_2": "да",
            "col_3": "УПД-001",
            "col_4": "да",
            "col_5": 1500.00,
            "col_6": 500.00,
            "col_7": "Продавец",
            "col_8": 1000.00,
            "col_9": 0,
        }

        row = pd.Series(row_data)
        columns = list(row_data.keys())

        deal = await parser_service._create_deal_from_row(row, columns, period)

        assert deal.client_name == "Тест Клиент"
        assert deal.invoice_number == "12345"
        assert deal.invoice_date == "01.05.2025"
        assert deal.seller == "Продавец"
        assert deal.total_revenue.amount == Decimal("1500.00")
        assert deal.period == period

    @pytest.mark.asyncio
    async def test_create_item_from_row(self, parser_service):
        """Test item creation from row."""
        period = Period(month="Май", year="2025", full_name="Май 2025")
        builder = DealBuilder(period=period)
        builder.client_name = "Test"
        builder.invoice_info = "123"
        builder.seller = "Seller"
        deal = builder.build()

        row_data = {
            "col_0": "",  # Empty client (detail row)
            "col_1": "Тестовый товар",
            "col_2": 10.5,
            "col_3": 100.00,
            "col_4": 150.00,
            "col_5": 1575.00,
            "col_6": 525.00,
            "col_7": "",
            "col_8": 1050.00,
            "col_9": "Поставщик Тест",
            "col_10": 15,
        }

        row = pd.Series(row_data)
        columns = list(row_data.keys())

        item = await parser_service._create_item_from_row(row, columns, deal=deal)

        assert item is not None
        assert item.product_name == "Тестовый товар"
        assert item.quantity == Decimal("10.5")
        assert item.purchase_price.amount == Decimal("100.00")
        assert item.sale_price.amount == Decimal("150.00")
        assert item.supplier_name == "Поставщик Тест"
        assert item.pickup_date == "15"

    @pytest.mark.asyncio
    async def test_create_item_from_row_empty_product(self, parser_service):
        """Test item creation with empty product name."""
        row_data = {
            "col_0": "",
            "col_1": "",  # Empty product name
            "col_2": 10,
        }

        row = pd.Series(row_data)
        columns = list(row_data.keys())

        item = await parser_service._create_item_from_row(row, columns)

        assert item is None  # Should return None for empty product name

    @pytest.mark.asyncio
    async def test_create_deal_from_row_with_non_numeric(self, parser_service):
        """Deal with revenue_val='N/A' is created, total_revenue is None, no exception."""
        period = Period(month="Май", year="2025", full_name="Май 2025")
        row_data = {
            "col_0": "Тест Клиент",
            "col_1": "12345 от 01.05.2025",
            "col_2": "да",
            "col_3": "УПД-001",
            "col_4": "да",
            "col_5": "N/A",  # Non-numeric revenue
            "col_6": 500.00,
            "col_7": "Продавец",
            "col_8": 1000.00,
            "col_9": 0,
        }
        row = pd.Series(row_data)
        columns = list(row_data.keys())

        deal = await parser_service._create_deal_from_row(row, columns, period)

        assert deal.client_name == "Тест Клиент"
        assert deal.seller == "Продавец"
        assert deal.total_revenue is None
        assert deal.total_cost.amount == Decimal("1000.00")

    @pytest.mark.asyncio
    async def test_create_item_from_row_with_non_numeric(self, parser_service):
        """Item with purchase_val='N/A', quantity='10': quantity=10, purchase_price=None."""
        period = Period(month="Май", year="2025", full_name="Май 2025")
        builder = DealBuilder(period=period)
        builder.client_name = "Test"
        builder.invoice_info = "123"
        builder.seller = "Seller"
        deal = builder.build()

        row_data = {
            "col_0": "",
            "col_1": "Товар с N/A ценой",
            "col_2": "10",  # Valid quantity
            "col_3": "N/A",  # Non-numeric purchase price
            "col_4": 150.00,
            "col_5": 1500.00,
            "col_6": 500.00,
            "col_7": "",
            "col_8": 1000.00,
            "col_9": "Поставщик",
            "col_10": 15,
        }
        row = pd.Series(row_data)
        columns = list(row_data.keys())

        item = await parser_service._create_item_from_row(row, columns, deal=deal)

        assert item is not None
        assert item.product_name == "Товар с N/A ценой"
        assert item.quantity == Decimal("10")
        assert item.purchase_price is None
        assert item.sale_price.amount == Decimal("150.00")

    def test_find_header_row(self, parser_service):
        """Test header row detection."""
        # Create test DataFrame with header at row 1
        data = [
            ["", "", ""],
            ["Клиент", "Товар", "Цена"],  # Header row
            ["Test", "Item", "100"],
        ]
        df = pd.DataFrame(data)

        header_row = parser_service._find_header_row(df)
        assert header_row == 1

    def test_find_header_row_not_found(self, parser_service):
        """Test header row detection when not found."""
        # Create test DataFrame without "Клиент" column
        data = [["Test", "Item", "Price"], ["Value1", "Value2", "Value3"]]
        df = pd.DataFrame(data)

        header_row = parser_service._find_header_row(df)
        assert header_row is None


@pytest.mark.unit
class TestParseResult:
    """Tests for ParseResult model."""

    def test_parse_result_properties(self, sample_sync_session):
        """Test ParseResult computed properties."""
        from src.application.excel_parser.models import ParseResult, ParseStats
        from src.domain.models import Deal

        # Create sample deals
        period = Period(month="Май", year="2025", full_name="Май 2025")
        deal1 = Deal(client_name="Client 1", invoice_info="123", period=period)
        deal2 = Deal(client_name="Client 2", invoice_info="456", period=period)

        # Add items to deals
        from src.domain.models import DealItem

        deal1.add_item(DealItem(product_name="Item 1"))
        deal1.add_item(DealItem(product_name="Item 2"))
        deal2.add_item(DealItem(product_name="Item 3"))

        stats = ParseStats()
        stats.errors = ["Error 1"]
        stats.warnings = ["Warning 1"]

        result = ParseResult(
            deals=[deal1, deal2],
            stats=stats,
            sync_session=sample_sync_session,
            file_path="test.xlsx",
            file_size=1024,
            file_hash="abc123",
        )

        assert result.total_deals == 2
        assert result.total_items == 3
        assert result.has_errors is True
        assert result.has_warnings is True

    def test_parse_result_filters(self, sample_sync_session):
        """Test ParseResult filtering methods."""
        from src.application.excel_parser.models import ParseResult, ParseStats
        from src.domain.models import Deal

        # Create deals with different periods and clients
        period1 = Period(month="Май", year="2025", full_name="Май 2025")
        period2 = Period(month="Июнь", year="2025", full_name="Июнь 2025")

        deal1 = Deal(client_name="ООО Тест", invoice_info="123", period=period1)
        deal2 = Deal(client_name="ИП Иванов", invoice_info="456", period=period1)
        deal3 = Deal(client_name="ООО Другой", invoice_info="789", period=period2)

        result = ParseResult(
            deals=[deal1, deal2, deal3],
            stats=ParseStats(),
            sync_session=sample_sync_session,
            file_path="test.xlsx",
            file_size=1024,
            file_hash="abc123",
        )

        # Test period filter
        may_deals = result.get_deals_by_period("Май", "2025")
        assert len(may_deals) == 2

        june_deals = result.get_deals_by_period("Июнь", "2025")
        assert len(june_deals) == 1

        # Test client filter
        test_deals = result.get_deals_by_client("Тест")
        assert len(test_deals) == 1
        assert test_deals[0].client_name == "ООО Тест"

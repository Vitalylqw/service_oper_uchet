"""
Integration tests for Excel parser using a compact real `.xlsx` fixture.
"""

from __future__ import annotations

import pandas as pd
import pytest

from domain.exceptions import SyncFileError
from src.application.excel_parser import ExcelParserService, ParseResult
from src.domain.models import SyncSession
from src.domain.models.sync_session import SyncType


@pytest.fixture
def integration_excel_file(tmp_path) -> str:
    """Create a compact workbook that exercises the parser end-to-end."""
    rows = [
        [
            "Клиент",
            "Номенклатуры",
            "Кол/Отгр",
            "Цена вх/накл",
            "цена исх/Оплач?",
            "Выручка",
            "Маржа",
            "От кого Зак/Прод",
            "Ст. Закупки",
            "Поставщик/Откат",
            "Дата",
        ],
        ["ООО Альфа", "001 от 01.05.2025", "да", "УПД-001", "да", 2000, 500, "Продавец 1", 1500, 0, None],
        [None, "Товар 1", "10", "100", "150", 1500, 400, None, 1100, "Поставщик А", "15"],
        [None, "Товар 2", "5", "120", "180", 500, 100, None, 400, "Поставщик Б", "18"],
        ["ООО Бета", "002 от 02.05.2025", "нет", "УПД-002", "нет", 3000, 600, "Продавец 2", 2400, 0, None],
        [None, "Товар 3", "20", "120", "150", 3000, 600, None, 2400, "Поставщик В", "20"],
    ]
    excel_file = tmp_path / "parser_integration.xlsx"
    pd.DataFrame(rows).to_excel(
        excel_file,
        sheet_name="Май 2025",
        index=False,
        header=False,
        engine="openpyxl",
    )
    return str(excel_file)


@pytest.fixture
def sync_session(integration_excel_file: str) -> SyncSession:
    """Create sync session for parser integration tests."""
    return SyncSession(
        sync_type=SyncType.FULL,
        source_file_path=integration_excel_file,
        source_file_hash="integration_test_hash",
        source_file_size=1024,
        created_by="integration_test",
    )


@pytest.fixture
def parser_service() -> ExcelParserService:
    """Create parser service."""
    return ExcelParserService()


@pytest.mark.integration
class TestExcelParserIntegration:
    """Integration tests for Excel parser."""

    @pytest.mark.asyncio
    async def test_parse_excel_file_basic_metrics(
        self,
        parser_service: ExcelParserService,
        integration_excel_file: str,
        sync_session: SyncSession,
    ):
        """Parser should process the compact workbook end-to-end."""
        result = await parser_service.parse_file(integration_excel_file, sync_session)

        assert isinstance(result, ParseResult)
        assert len(result.deals) == 2
        assert result.total_items == 3

        stats = result.stats
        assert stats.total_sheets == 1
        assert stats.processed_sheets == 1
        assert stats.total_deals == 2
        assert stats.processed_items == 3
        assert stats.errors == []

    @pytest.mark.asyncio
    async def test_parse_excel_file_data_structure(
        self,
        parser_service: ExcelParserService,
        integration_excel_file: str,
        sync_session: SyncSession,
    ):
        """Parsed deals and items should keep the expected structure."""
        result = await parser_service.parse_file(integration_excel_file, sync_session)

        assert result.file_path == integration_excel_file
        assert result.file_size > 0
        assert len(result.file_hash) == 32

        first_deal = result.deals[0]
        assert first_deal.client_name == "ООО Альфа"
        assert first_deal.period.full_name == "Май 2025"
        assert first_deal.seller == "Продавец 1"
        assert len(first_deal.items) == 2

        first_item = first_deal.items[0]
        assert first_item.product_name == "Товар 1"
        assert first_item.deal_id == first_deal.id
        assert first_item.supplier_name == "Поставщик А"

    @pytest.mark.asyncio
    async def test_parse_excel_file_business_logic(
        self,
        parser_service: ExcelParserService,
        integration_excel_file: str,
        sync_session: SyncSession,
    ):
        """Totals and periods should remain internally consistent."""
        result = await parser_service.parse_file(integration_excel_file, sync_session)

        periods = {deal.period.full_name for deal in result.deals}
        assert periods == {"Май 2025"}

        for deal in result.deals:
            assert deal.total_revenue is not None
            assert deal.total_revenue.amount > 0
            if deal.total_margin is not None:
                assert deal.total_margin.amount <= deal.total_revenue.amount

    @pytest.mark.asyncio
    async def test_parse_excel_file_known_clients(
        self,
        parser_service: ExcelParserService,
        integration_excel_file: str,
        sync_session: SyncSession,
    ):
        """Parser should preserve client names from the workbook."""
        result = await parser_service.parse_file(integration_excel_file, sync_session)

        client_names = {deal.client_name for deal in result.deals}
        assert client_names == {"ООО Альфа", "ООО Бета"}

    @pytest.mark.asyncio
    async def test_parse_excel_file_error_handling(
        self, parser_service: ExcelParserService, sync_session: SyncSession
    ):
        """Non-existent files should raise `SyncFileError`."""
        with pytest.raises(SyncFileError):
            await parser_service.parse_file("nonexistent_file.xlsx", sync_session)

    @pytest.mark.asyncio
    async def test_parse_excel_file_totals_calculation(
        self,
        parser_service: ExcelParserService,
        integration_excel_file: str,
        sync_session: SyncSession,
    ):
        """Items should stay attached to deals after parsing."""
        result = await parser_service.parse_file(integration_excel_file, sync_session)

        for deal in result.deals:
            assert deal.items
            for item in deal.items:
                assert item.deal_id == deal.id
                assert item.revenue is not None
                assert item.revenue.amount > 0

    @pytest.mark.asyncio
    async def test_parse_excel_sync_session_integration(
        self,
        parser_service: ExcelParserService,
        integration_excel_file: str,
        sync_session: SyncSession,
    ):
        """Sync session stats should be updated by the parser."""
        result = await parser_service.parse_file(integration_excel_file, sync_session)

        assert sync_session.stats.total_deals == result.stats.total_deals
        assert sync_session.stats.processed_deals == result.stats.processed_deals
        assert sync_session.stats.total_items == result.stats.total_items
        assert sync_session.stats.processed_items == result.stats.processed_items

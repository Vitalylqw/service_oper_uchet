"""
Интеграционные тесты для Excel Parser с реальными данными.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from domain.exceptions import SyncFileError

from src.application.excel_parser import ExcelParserService, ParseResult
from src.domain.models import SyncSession
from src.domain.models.sync_session import SyncType


@pytest.fixture
def real_excel_file() -> str:
    """Fixture для реального Excel файла."""
    file_path = "Data_source_excel.xlsx"

    if not Path(file_path).exists():
        pytest.skip(f"Real Excel file {file_path} not found")

    return file_path


@pytest.fixture
def sync_session() -> SyncSession:
    """Fixture для сессии синхронизации."""
    return SyncSession(sync_type=SyncType.FULL, source_file="Data_source_excel.xlsx")


@pytest.fixture
def parser_service() -> ExcelParserService:
    """Fixture для сервиса парсера."""
    return ExcelParserService()


@pytest.mark.integration
class TestExcelParserIntegration:
    """Интеграционные тесты для Excel парсера."""

    @pytest.mark.asyncio
    async def test_parse_real_excel_file_basic_metrics(
        self, parser_service: ExcelParserService, real_excel_file: str, sync_session: SyncSession
    ):
        """Тест основных метрик парсинга реального Excel файла."""
        # Arrange & Act
        result = await parser_service.parse_file(real_excel_file, sync_session)

        # Assert - основные метрики
        assert isinstance(result, ParseResult)
        assert result.deals is not None
        assert len(result.deals) > 0

        # Проверяем статистику
        stats = result.stats
        assert stats.total_sheets >= 2  # Ожидаем минимум 2 листа
        assert stats.processed_sheets == stats.total_sheets  # Все листы обработаны
        assert stats.total_deals >= 10  # Ожидаем минимум 10 сделок
        assert stats.processed_deals == stats.total_deals  # Все сделки обработаны
        assert stats.total_items >= 50  # Ожидаем минимум 50 товаров
        assert stats.processed_items == stats.total_items  # Все товары обработаны

        # Проверяем успешность
        assert stats.success_rate_sheets == 100.0
        assert stats.success_rate_deals == 100.0
        assert stats.success_rate_items == 100.0

    @pytest.mark.asyncio
    async def test_parse_real_excel_file_data_structure(
        self, parser_service: ExcelParserService, real_excel_file: str, sync_session: SyncSession
    ):
        """Тест структуры данных в результате парсинга."""
        # Arrange & Act
        result = await parser_service.parse_file(real_excel_file, sync_session)

        # Assert - структура результата
        assert result.file_path == real_excel_file
        assert result.file_size > 0
        assert result.file_hash is not None
        assert len(result.file_hash) == 32  # MD5 hash length

        # Проверяем структуру первой сделки
        first_deal = result.deals[0]
        assert first_deal.client_name is not None
        assert len(first_deal.client_name.strip()) > 0
        assert first_deal.period is not None
        assert first_deal.period.month is not None
        assert first_deal.period.year is not None
        assert first_deal.id is not None
        assert first_deal.created_at is not None

        # Проверяем что есть товары в сделке
        assert len(first_deal.items) > 0

        # Проверяем структуру первого товара
        first_item = first_deal.items[0]
        assert first_item.product_name is not None
        assert len(first_item.product_name.strip()) > 0
        assert first_item.id is not None
        assert first_item.deal_id == first_deal.id

    @pytest.mark.asyncio
    async def test_parse_real_excel_file_business_logic(
        self, parser_service: ExcelParserService, real_excel_file: str, sync_session: SyncSession
    ):
        """Тест бизнес-логики и вычислений."""
        # Arrange & Act
        result = await parser_service.parse_file(real_excel_file, sync_session)

        # Assert - бизнес-логика
        deals_with_revenue = [
            d for d in result.deals if d.total_revenue and d.total_revenue.amount > 0
        ]
        assert len(deals_with_revenue) > 0, "Должны быть сделки с выручкой"

        # Проверяем валюту
        for deal in deals_with_revenue:
            assert deal.total_revenue.currency == "RUB"

            # Если есть маржа, проверяем что она меньше выручки
            if deal.total_margin and deal.total_margin.amount > 0:
                assert deal.total_margin.amount <= deal.total_revenue.amount

        # Проверяем периоды
        periods = {deal.period.full_name for deal in result.deals}
        assert len(periods) >= 1, "Должен быть хотя бы один период"

        # Проверяем что все периоды содержат год
        for period_name in periods:
            assert "2025" in period_name

    @pytest.mark.asyncio
    async def test_parse_real_excel_file_known_clients(
        self, parser_service: ExcelParserService, real_excel_file: str, sync_session: SyncSession
    ):
        """Тест наличия известных клиентов из реального файла."""
        # Arrange & Act
        result = await parser_service.parse_file(real_excel_file, sync_session)

        # Assert - известные клиенты
        client_names = {deal.client_name for deal in result.deals}

        # Проверяем наличие ожидаемых клиентов (из предыдущего анализа)
        expected_clients = {"ЛЕНТЕХСТРОЙ", "БАЛТИНВЕСТСТРОЙ", "Ригель"}
        found_clients = expected_clients.intersection(client_names)

        assert len(found_clients) > 0, f"Не найдены ожидаемые клиенты: {expected_clients}"

    @pytest.mark.asyncio
    async def test_parse_real_excel_file_error_handling(
        self, parser_service: ExcelParserService, sync_session: SyncSession
    ):
        """Тест обработки ошибок при неверном файле."""
        # Arrange & Act & Assert
        with pytest.raises(SyncFileError):  # Проверяем только тип исключения
            await parser_service.parse_file("nonexistent_file.xlsx", sync_session)

    @pytest.mark.asyncio
    async def test_parse_real_excel_file_totals_calculation(
        self, parser_service: ExcelParserService, real_excel_file: str, sync_session: SyncSession
    ):
        """Тест корректности вычисления итогов."""
        # Arrange & Act
        result = await parser_service.parse_file(real_excel_file, sync_session)

        # Assert - проверяем вычисления для сделок с товарами
        for deal in result.deals:
            if len(deal.items) > 0:
                # Если у товаров есть суммы, проверяем что итоги в сделке рассчитаны
                items_with_revenue = [
                    item for item in deal.items if item.revenue and item.revenue.amount > 0
                ]

                if items_with_revenue and deal.total_revenue:
                    # Итог должен быть больше 0
                    assert deal.total_revenue.amount > 0

                    # Все товары должны иметь корректные ID связи
                    for item in deal.items:
                        assert item.deal_id == deal.id

    @pytest.mark.asyncio
    async def test_parse_real_excel_sync_session_integration(
        self, parser_service: ExcelParserService, real_excel_file: str, sync_session: SyncSession
    ):
        """Тест интеграции с SyncSession."""
        # Arrange - сохраняем начальные значения
        initial_total_deals = sync_session.stats.total_deals
        initial_processed_deals = sync_session.stats.processed_deals
        initial_total_items = sync_session.stats.total_items
        initial_processed_items = sync_session.stats.processed_items

        # Act
        result = await parser_service.parse_file(real_excel_file, sync_session)

        # Assert - sync session должна быть обновлена
        assert sync_session.stats.total_deals > initial_total_deals
        assert sync_session.stats.processed_deals > initial_processed_deals
        assert sync_session.stats.total_items > initial_total_items
        assert sync_session.stats.processed_items > initial_processed_items

        # Статистика в результате и сессии должна совпадать
        assert result.stats.total_deals == sync_session.stats.total_deals
        assert result.stats.processed_deals == sync_session.stats.processed_deals
        assert result.stats.total_items == sync_session.stats.total_items
        assert result.stats.processed_items == sync_session.stats.processed_items

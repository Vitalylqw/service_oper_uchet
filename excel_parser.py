#!/usr/bin/env python3
"""
Парсер Excel файлов для системы учета операций
Учитывает структуру мастер/подчиненных записей
"""

from __future__ import annotations

import logging
import re
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ParseStats:
    """Статистика парсинга"""

    total_sheets: int = 0
    processed_sheets: int = 0
    failed_sheets: int = 0
    total_deals: int = 0
    processed_deals: int = 0
    failed_deals: int = 0
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class DealItem:
    """Позиция товара в сделке (подчиненная запись)"""

    product_name: str
    quantity: float | None = None
    purchase_price: float | None = None
    sale_price: float | None = None
    revenue: float | None = None
    margin: float | None = None
    cost: float | None = None
    supplier_name: str | None = None
    pickup_date: str | None = None  # Дата забора товара


@dataclass
class Deal:
    """Сделка (мастер-запись)"""

    client_name: str
    invoice_info: str  # Полный текст: "5938 от 16.06.2025"
    invoice_number: str | None = None  # Номер счета: "5938"
    invoice_date: str | None = None  # Дата счета: "16.06.2025"
    is_shipped: str | None = None  # Отгружен ли товар
    upd_number: str | None = None  # Номер УПД на реализацию
    is_paid: str | None = None  # Оплачен ли счет
    total_revenue: float | None = None
    total_margin: float | None = None
    seller: str | None = None  # Продавец
    total_cost: float | None = None
    kickback_amount: float | None = None  # Сумма отката
    # Период отчета
    period_full: str | None = None  # Полное название: "Май 2025"
    period_month: str | None = None  # Месяц: "Май"
    period_year: str | None = None  # Год: "2025"
    items: list[DealItem] = field(default_factory=list)


class ExcelParser:
    """Парсер Excel файлов с учетом сложной структуры"""

    def __init__(self):
        self.deals: list[Deal] = []
        self.stats = ParseStats()

    def _log_error(self, error_msg: str, exception: Exception = None) -> None:
        """Логирует ошибку и добавляет в статистику"""
        full_msg = f"{error_msg}"
        if exception:
            full_msg += f" Ошибка: {str(exception)}"

        logger.error(full_msg)
        self.stats.errors.append(full_msg)

        if exception:
            logger.debug(f"Трассировка: {traceback.format_exc()}")

    def _log_warning(self, warning_msg: str) -> None:
        """Логирует предупреждение и добавляет в статистику"""
        logger.warning(warning_msg)
        self.stats.warnings.append(warning_msg)

    def _print_final_stats(self) -> None:
        """Выводит итоговую статистику парсинга"""
        print("\n" + "=" * 80)
        print("ИТОГОВАЯ СТАТИСТИКА ПАРСИНГА")
        print("=" * 80)

        print("📋 ЛИСТЫ EXCEL:")
        print(f"  Всего листов: {self.stats.total_sheets}")
        print(f"  ✅ Обработано успешно: {self.stats.processed_sheets}")
        print(f"  ❌ Ошибок при обработке: {self.stats.failed_sheets}")

        print("\n🏢 СДЕЛКИ:")
        print(f"  Всего сделок: {self.stats.total_deals}")
        print(f"  ✅ Обработано успешно: {self.stats.processed_deals}")
        print(f"  ❌ Ошибок при обработке: {self.stats.failed_deals}")

        print("\n📦 ПОЗИЦИИ ТОВАРОВ:")
        print(f"  Всего позиций: {self.stats.total_items}")
        print(f"  ✅ Обработано успешно: {self.stats.processed_items}")
        print(f"  ❌ Ошибок при обработке: {self.stats.failed_items}")

        if self.stats.errors:
            print(f"\n❌ ОШИБКИ ({len(self.stats.errors)}):")
            for i, error in enumerate(self.stats.errors[:10], 1):  # Показываем первые 10
                print(f"  {i}. {error}")
            if len(self.stats.errors) > 10:
                print(f"  ... и еще {len(self.stats.errors) - 10} ошибок")

        if self.stats.warnings:
            print(f"\n⚠️ ПРЕДУПРЕЖДЕНИЯ ({len(self.stats.warnings)}):")
            for i, warning in enumerate(self.stats.warnings[:5], 1):  # Показываем первые 5
                print(f"  {i}. {warning}")
            if len(self.stats.warnings) > 5:
                print(f"  ... и еще {len(self.stats.warnings) - 5} предупреждений")

        success_rate_sheets = (
            (self.stats.processed_sheets / self.stats.total_sheets * 100)
            if self.stats.total_sheets > 0
            else 0
        )
        success_rate_deals = (
            (self.stats.processed_deals / self.stats.total_deals * 100)
            if self.stats.total_deals > 0
            else 0
        )
        success_rate_items = (
            (self.stats.processed_items / self.stats.total_items * 100)
            if self.stats.total_items > 0
            else 0
        )

        print("\n📊 ПРОЦЕНТ УСПЕШНОСТИ:")
        print(f"  Листы: {success_rate_sheets:.1f}%")
        print(f"  Сделки: {success_rate_deals:.1f}%")
        print(f"  Позиции: {success_rate_items:.1f}%")
        print("=" * 80)

    @staticmethod
    def _safe_round(value: float | None, decimals: int = 2) -> float | None:
        """Безопасное округление значения"""
        if value is None:
            return None
        try:
            return round(float(value), decimals)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_string(value: Any) -> str:
        """Безопасное преобразование в строку с удалением пробелов"""
        if pd.isna(value) or value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _safe_pickup_date(value: Any) -> str:
        """Безопасное преобразование даты забора с правильным форматированием чисел"""
        if pd.isna(value) or value is None:
            return ""

        # Если это число (например, 19.0), конвертируем в целое
        try:
            num_value = float(value)
            # Проверяем, является ли число целым (например, 19.0)
            if num_value.is_integer():
                return str(int(num_value))
            else:
                return str(num_value).strip()
        except (ValueError, TypeError):
            # Если не число, возвращаем как строку
            return str(value).strip()

    @staticmethod
    def _parse_invoice_info(invoice_info: str) -> tuple[str, str]:
        """
        Парсит информацию о счете и возвращает номер и дату

        Args:
            invoice_info: Строка типа "5938 от 16.06.2025"

        Returns:
            Кортеж (номер, дата)
        """
        try:
            if not invoice_info:
                return "", ""

            # Убираем лишние пробелы
            info = str(invoice_info).strip()

            # Ищем паттерн: число + "от" + дата
            pattern = r"(\d+)\s+от\s+(\d{1,2}\.\d{1,2}\.\d{4})"
            match = re.search(pattern, info)

            if match:
                number = match.group(1)
                date = match.group(2)
                return number, date

            # Если не получилось разобрать, попробуем другие варианты
            # Может быть формат "5938 16.06.2025" без "от"
            pattern2 = r"(\d+)\s+(\d{1,2}\.\d{1,2}\.\d{4})"
            match2 = re.search(pattern2, info)

            if match2:
                number = match2.group(1)
                date = match2.group(2)
                return number, date

            # Если ничего не нашли, возвращаем пустые строки
            return "", ""

        except Exception:
            # При любой ошибке возвращаем пустые строки
            return "", ""

    def parse_file(self, file_path: str) -> list[Deal]:
        """
        Парсит Excel файл и возвращает список сделок

        Args:
            file_path: Путь к Excel файлу

        Returns:
            Список сделок со всеми позициями
        """
        logger.info(f"Начинаю парсинг файла: {file_path}")

        try:
            # Проверяем существование файла
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Файл не найден: {file_path}")

            # Читаем все листы
            sheets = pd.read_excel(file_path, sheet_name=None, header=None)
            self.stats.total_sheets = len(sheets)

            all_deals = []

            for sheet_name, df in sheets.items():
                logger.info(f"Обрабатываю лист: {sheet_name}")
                try:
                    deals = self._parse_sheet(df, sheet_name.strip())
                    all_deals.extend(deals)
                    self.stats.processed_sheets += 1
                    logger.info(f"✅ Лист '{sheet_name}': найдено сделок: {len(deals)}")
                except Exception as e:
                    self.stats.failed_sheets += 1
                    self._log_error(f"Ошибка при обработке листа '{sheet_name}'", e)
                    # Продолжаем обработку других листов
                    continue

            logger.info(f"Всего обработано сделок: {len(all_deals)}")
            self._print_final_stats()
            return all_deals

        except Exception as e:
            self._log_error(f"Критическая ошибка при парсинге файла '{file_path}'", e)
            self._print_final_stats()
            return []  # Возвращаем пустой список вместо исключения

    def _parse_sheet(self, df: pd.DataFrame, sheet_name: str) -> list[Deal]:
        """Парсит отдельный лист Excel"""

        try:
            if df.empty:
                self._log_warning(f"Лист '{sheet_name}' пуст")
                return []

            # Находим строку с заголовками (обычно строка 2)
            header_row = self._find_header_row(df)
            if header_row is None:
                self._log_warning(
                    f"Не найдена строка заголовков в листе '{sheet_name}', используем строку 1"
                )
                header_row = 1  # Пытаемся использовать вторую строку по умолчанию

                if len(df) <= header_row:
                    self._log_error(f"Лист '{sheet_name}' содержит недостаточно строк")
                    return []

            logger.info(f"Лист '{sheet_name}': строка заголовков: {header_row}")

            try:
                # Устанавливаем заголовки
                df.columns = df.iloc[header_row]
                data_df = df.iloc[header_row + 1 :].reset_index(drop=True)
            except Exception as e:
                self._log_error(f"Ошибка при установке заголовков для листа '{sheet_name}'", e)
                return []

            # Извлекаем период из названия листа
            period_full, period_month, period_year = self._parse_period_info(sheet_name)

            # Парсим сделки
            deals = self._parse_deals(data_df, period_full, period_month, period_year)

            return deals

        except Exception as e:
            self._log_error(f"Критическая ошибка при парсинге листа '{sheet_name}'", e)
            return []

    def _find_header_row(self, df: pd.DataFrame) -> int | None:
        """Находит строку с заголовками"""

        try:
            # Ищем строку, которая содержит "Клиент"
            for i in range(min(5, len(df))):
                try:
                    row = df.iloc[i]
                    for val in row:
                        if pd.notna(val) and "Клиент" in str(val):
                            return i
                except Exception as e:
                    self._log_warning(f"Ошибка при проверке строки {i} на заголовки: {str(e)}")
                    continue

            return None

        except Exception as e:
            self._log_error("Критическая ошибка при поиске строки заголовков", e)
            return None

    @staticmethod
    def _parse_period_info(sheet_name: str) -> tuple[str, str, str]:
        """
        Парсит информацию о периоде из названия листа

        Args:
            sheet_name: Название листа типа "Май 2025"

        Returns:
            Кортеж (полное_название, месяц, год)
        """
        try:
            if not sheet_name:
                return "", "", ""

            # Убираем лишние пробелы
            full_name = str(sheet_name).strip()

            # Словарь месяцев
            months_map = {
                "январь": "Январь",
                "февраль": "Февраль",
                "март": "Март",
                "апрель": "Апрель",
                "май": "Май",
                "июнь": "Июнь",
                "июль": "Июль",
                "август": "Август",
                "сентябрь": "Сентябрь",
                "октябрь": "Октябрь",
                "ноябрь": "Ноябрь",
                "декабрь": "Декабрь",
            }

            sheet_lower = full_name.lower()

            # Ищем месяц в названии
            found_month = ""
            for month_key, month_value in months_map.items():
                if month_key in sheet_lower:
                    found_month = month_value
                    break

            # Ищем год в названии (4 цифры)
            year_match = re.search(r"\b(\d{4})\b", full_name)
            found_year = year_match.group(1) if year_match else ""

            return full_name, found_month, found_year

        except Exception:
            # При ошибке возвращаем хотя бы исходное название
            return str(sheet_name) if sheet_name else "", "", ""

    def _parse_deals(
        self, df: pd.DataFrame, period_full: str, period_month: str, period_year: str
    ) -> list[Deal]:
        """Парсит сделки из DataFrame"""

        deals = []
        current_deal = None
        row_counter = 0

        try:
            # Получаем названия колонок и фильтруем NaN
            raw_columns = list(df.columns)
            columns = []
            for col in raw_columns:
                if pd.notna(col):
                    columns.append(col)
                else:
                    columns.append(f"col_{len(columns)}")  # Заменяем NaN на col_N

            # Обновляем названия колонок в DataFrame
            df.columns = columns

            client_col = columns[0] if len(columns) > 0 else None

            if client_col is None:
                self._log_warning("Не найдена колонка клиента")
                return []

            logger.info(f"Колонки: {columns}")

            for _idx, row in df.iterrows():
                row_counter += 1
                try:
                    # Проверяем, является ли это мастер-записью
                    client_value = row[client_col]

                    if pd.notna(client_value) and str(client_value).strip():
                        # Это мастер-запись - начинаем новую сделку
                        if current_deal is not None:
                            # Рассчитываем итоги для завершенной сделки
                            try:
                                self._calculate_deal_totals(current_deal)
                                deals.append(current_deal)
                                self.stats.processed_deals += 1
                            except Exception as e:
                                self.stats.failed_deals += 1
                                self._log_error(
                                    f"Ошибка при расчете итогов сделки '{current_deal.client_name}' (строка {row_counter})",
                                    e,
                                )

                        # Создаем новую сделку
                        try:
                            current_deal = self._create_deal_from_row(
                                row, columns, period_full, period_month, period_year
                            )
                            self.stats.total_deals += 1
                        except Exception as e:
                            self.stats.failed_deals += 1
                            self._log_error(
                                f"Ошибка при создании сделки из строки {row_counter}", e
                            )
                            # Создаем пустую сделку с минимальными данными
                            current_deal = Deal(
                                client_name=f"ОШИБКА_СТРОКА_{row_counter}",
                                invoice_info="",
                                period_full=period_full,
                                period_month=period_month,
                                period_year=period_year,
                            )

                    elif current_deal is not None:
                        # Это подчиненная запись - добавляем позицию к текущей сделке
                        try:
                            item = self._create_item_from_row(row, columns)
                            if item and item.product_name and str(item.product_name).strip():
                                current_deal.items.append(item)
                                self.stats.processed_items += 1
                            self.stats.total_items += 1
                        except Exception as e:
                            self.stats.failed_items += 1
                            self._log_error(
                                f"Ошибка при создании позиции из строки {row_counter} для сделки '{current_deal.client_name}'",
                                e,
                            )
                            # Добавляем пустую позицию для сохранения структуры
                            error_item = DealItem(product_name=f"ОШИБКА_СТРОКА_{row_counter}")
                            current_deal.items.append(error_item)

                except Exception as e:
                    self._log_error(f"Критическая ошибка при обработке строки {row_counter}", e)
                    continue

            # Добавляем последнюю сделку
            if current_deal is not None:
                try:
                    self._calculate_deal_totals(current_deal)
                    deals.append(current_deal)
                    self.stats.processed_deals += 1
                except Exception as e:
                    self.stats.failed_deals += 1
                    self._log_error(
                        f"Ошибка при финализации последней сделки '{current_deal.client_name}'", e
                    )
                    # Все равно добавляем сделку
                    deals.append(current_deal)

            return deals

        except Exception as e:
            self._log_error("Критическая ошибка при парсинге сделок", e)
            return deals  # Возвращаем что удалось обработать

    def _create_deal_from_row(
        self,
        row: pd.Series,
        columns: list[str],
        period_full: str,
        period_month: str,
        period_year: str,
    ) -> Deal:
        """Создает объект сделки из мастер-записи"""

        try:

            def safe_get(col_name: str, default=None):
                """Безопасно получает значение колонки"""
                try:
                    if col_name in columns and col_name in row.index:
                        val = row[col_name]
                        return val if pd.notna(val) else default
                    return default
                except (KeyError, TypeError):
                    return default

            def safe_float(val) -> float | None:
                """Безопасно преобразует в float с округлением до 2 знаков"""
                if pd.isna(val):
                    return None
                try:
                    return round(float(val), 2)
                except (ValueError, TypeError):
                    return None

            # Маппинг колонок (по позиции, так как названия могут отличаться)
            client_name = self._safe_string(safe_get(columns[0] if len(columns) > 0 else ""))
            if not client_name:
                client_name = "НЕИЗВЕСТНЫЙ_КЛИЕНТ"

            invoice_info = self._safe_string(safe_get(columns[1] if len(columns) > 1 else ""))
            invoice_number, invoice_date = self._parse_invoice_info(invoice_info)

            deal = Deal(
                client_name=client_name,
                invoice_info=invoice_info,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                is_shipped=self._safe_string(safe_get(columns[2] if len(columns) > 2 else "")),
                upd_number=self._safe_string(safe_get(columns[3] if len(columns) > 3 else "")),
                is_paid=self._safe_string(safe_get(columns[4] if len(columns) > 4 else "")),
            )

            # Числовые поля
            if len(columns) > 5:
                deal.total_revenue = safe_float(safe_get(columns[5]))
            if len(columns) > 6:
                deal.total_margin = safe_float(safe_get(columns[6]))
            if len(columns) > 7:
                deal.seller = self._safe_string(safe_get(columns[7]))
            if len(columns) > 8:
                deal.total_cost = safe_float(safe_get(columns[8]))
            if len(columns) > 9:
                deal.kickback_amount = safe_float(safe_get(columns[9]))

            # Устанавливаем информацию о периоде
            deal.period_full = period_full
            deal.period_month = period_month
            deal.period_year = period_year

            return deal

        except Exception:
            # При ошибке создаем минимальную сделку
            error_client = "ОШИБКА_СОЗДАНИЯ_СДЕЛКИ"
            try:
                # Пытаемся хотя бы получить имя клиента
                if len(columns) > 0 and columns[0] in row.index:
                    error_client = self._safe_string(row[columns[0]]) or error_client
            except Exception:
                pass

            return Deal(
                client_name=error_client,
                invoice_info="",
                period_full=period_full,
                period_month=period_month,
                period_year=period_year,
            )

    def _create_item_from_row(self, row: pd.Series, columns: list[str]) -> DealItem | None:
        """Создает позицию товара из подчиненной записи"""

        try:

            def safe_get(col_name: str, default=None):
                try:
                    if col_name in columns and col_name in row.index:
                        val = row[col_name]
                        return val if pd.notna(val) else default
                    return default
                except (KeyError, TypeError):
                    return default

            def safe_float(val) -> float | None:
                """Безопасно преобразует в float с округлением до 2 знаков"""
                if pd.isna(val):
                    return None
                try:
                    return round(float(val), 2)
                except (ValueError, TypeError):
                    return None

            # Проверяем, есть ли наименование товара
            product_name = self._safe_string(safe_get(columns[1] if len(columns) > 1 else ""))
            if not product_name:
                return None

            item = DealItem(product_name=product_name)

            # Заполняем остальные поля с защитой от ошибок
            try:
                if len(columns) > 2:
                    item.quantity = safe_float(safe_get(columns[2]))
                if len(columns) > 3:
                    item.purchase_price = safe_float(safe_get(columns[3]))
                if len(columns) > 4:
                    item.sale_price = safe_float(safe_get(columns[4]))
                if len(columns) > 5:
                    item.revenue = safe_float(safe_get(columns[5]))
                if len(columns) > 6:
                    item.margin = safe_float(safe_get(columns[6]))
                if len(columns) > 8:
                    item.cost = safe_float(safe_get(columns[8]))
                if len(columns) > 9:
                    item.supplier_name = self._safe_string(safe_get(columns[9]))
                if len(columns) > 10:
                    item.pickup_date = self._safe_pickup_date(safe_get(columns[10]))
            except Exception as e:
                # Логируем предупреждение, но продолжаем с частично заполненным объектом
                self._log_warning(f"Ошибка при заполнении полей позиции '{product_name}': {str(e)}")

            # Рассчитываем поля, если они не заполнены
            try:
                self._calculate_item_fields(item)
            except Exception as e:
                self._log_warning(f"Ошибка при расчете полей позиции '{product_name}': {str(e)}")

            return item

        except Exception:
            # При критической ошибке возвращаем None
            return None

    def _calculate_item_fields(self, item: DealItem) -> None:
        """Рассчитывает недостающие поля для позиции товара"""

        try:
            # Рассчитываем выручку (количество * цена продажи)
            if item.revenue is None and item.quantity and item.sale_price:
                item.revenue = self._safe_round(item.quantity * item.sale_price)
        except Exception as e:
            self._log_warning(
                f"Ошибка при расчете выручки для позиции '{item.product_name}': {str(e)}"
            )

        try:
            # Рассчитываем стоимость закупки (количество * цена закупки)
            if item.cost is None and item.quantity and item.purchase_price:
                item.cost = self._safe_round(item.quantity * item.purchase_price)
        except Exception as e:
            self._log_warning(
                f"Ошибка при расчете стоимости для позиции '{item.product_name}': {str(e)}"
            )

        try:
            # Рассчитываем маржу (выручка - стоимость закупки)
            if item.margin is None and item.revenue and item.cost:
                item.margin = self._safe_round(item.revenue - item.cost)
        except Exception as e:
            self._log_warning(
                f"Ошибка при расчете маржи для позиции '{item.product_name}': {str(e)}"
            )

    def _calculate_deal_totals(self, deal: Deal) -> None:
        """Рассчитывает итоговые поля для сделки"""

        try:
            if not deal.items:
                return

            # Суммируем по всем позициям
            try:
                total_revenue = sum(item.revenue for item in deal.items if item.revenue)
                if deal.total_revenue is None:
                    deal.total_revenue = self._safe_round(total_revenue)
            except Exception as e:
                self._log_warning(
                    f"Ошибка при расчете общей выручки для сделки '{deal.client_name}': {str(e)}"
                )

            try:
                total_cost = sum(item.cost for item in deal.items if item.cost)
                if deal.total_cost is None:
                    deal.total_cost = self._safe_round(total_cost)
            except Exception as e:
                self._log_warning(
                    f"Ошибка при расчете общей стоимости для сделки '{deal.client_name}': {str(e)}"
                )

            try:
                total_margin = sum(item.margin for item in deal.items if item.margin)
                if deal.total_margin is None:
                    deal.total_margin = self._safe_round(total_margin)
            except Exception as e:
                self._log_warning(
                    f"Ошибка при расчете общей маржи для сделки '{deal.client_name}': {str(e)}"
                )

        except Exception as e:
            self._log_error(f"Критическая ошибка при расчете итогов сделки '{deal.client_name}'", e)

    def export_to_dict(self, deals: list[Deal]) -> dict[str, Any]:
        """Экспортирует сделки в словарь для дальнейшей обработки"""

        result = {"deals": [], "total_deals": len(deals), "parsed_at": datetime.now().isoformat()}

        for deal in deals:
            deal_dict = {
                "client_name": deal.client_name,
                "invoice_info": deal.invoice_info,
                "invoice_number": deal.invoice_number,
                "invoice_date": deal.invoice_date,
                "is_shipped": deal.is_shipped,
                "upd_number": deal.upd_number,
                "is_paid": deal.is_paid,
                "total_revenue": deal.total_revenue,
                "total_margin": deal.total_margin,
                "seller": deal.seller,
                "total_cost": deal.total_cost,
                "kickback_amount": deal.kickback_amount,
                "period_full": deal.period_full,
                "period_month": deal.period_month,
                "period_year": deal.period_year,
                "items": [],
            }

            for item in deal.items:
                item_dict = {
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "purchase_price": item.purchase_price,
                    "sale_price": item.sale_price,
                    "revenue": item.revenue,
                    "margin": item.margin,
                    "cost": item.cost,
                    "supplier_name": item.supplier_name,
                    "pickup_date": item.pickup_date,
                }
                deal_dict["items"].append(item_dict)

            result["deals"].append(deal_dict)

        return result


def main():
    """Основная функция для тестирования парсера"""

    parser = ExcelParser()

    try:
        print("🚀 Начинаю парсинг Excel файла...")
        deals = parser.parse_file("Data_source_excel.xlsx")

        print(f"\n✅ Парсинг завершен! Получено сделок: {len(deals)}")

        # Показываем детальную статистику
        total_items = sum(len(deal.items) for deal in deals)
        print(f"📦 Всего позиций товаров: {total_items}")

        # Показываем первую сделку как пример
        if deals:
            first_deal = deals[0]
            print("\n📋 ПРИМЕР ПЕРВОЙ СДЕЛКИ:")
            print(f"  👤 Клиент: {first_deal.client_name}")
            print(f"  📄 Счет (полный): {first_deal.invoice_info}")
            print(f"  🔢 Номер счета: {first_deal.invoice_number}")
            print(f"  📅 Дата счета: {first_deal.invoice_date}")
            print(f"  📆 Период (полный): {first_deal.period_full}")
            print(f"  🗓️ Месяц: {first_deal.period_month}")
            print(f"  📋 Год: {first_deal.period_year}")
            print(f"  🚚 Отгружен: {first_deal.is_shipped}")
            print(f"  👨‍💼 Продавец: {first_deal.seller}")
            print(f"  📦 Позиций товаров: {len(first_deal.items)}")

            if first_deal.items:
                print("\n  🛒 ПЕРВАЯ ПОЗИЦИЯ:")
                item = first_deal.items[0]
                print(f"    📦 Товар: {item.product_name}")
                print(f"    🔢 Количество: {item.quantity}")
                print(f"    💰 Цена продажи: {item.sale_price}")
                print(f"    🏭 Поставщик: {item.supplier_name}")
        else:
            print("\n⚠️ Не удалось получить ни одной сделки")

        # Экспортируем в JSON для проверки
        try:
            import json

            result = parser.export_to_dict(deals)
            with open("parsed_deals.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print("\n💾 Результат сохранен в parsed_deals.json")
        except Exception as e:
            parser._log_error("Ошибка при сохранении JSON файла", e)

    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        if hasattr(parser, "stats"):
            parser._print_final_stats()
        raise


if __name__ == "__main__":
    main()

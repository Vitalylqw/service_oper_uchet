"""Tests for parser-level period filtering."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.application.excel_parser import ExcelParserService


@pytest.fixture
def multi_sheet_excel(tmp_path: Path) -> str:
    """Create a small workbook with two valid period sheets."""
    data = {
        "Клиент": ['ООО "Тест"', None],
        "Номенклатуры": ["12345 от 01.05.2025", "Товар 1"],
        "Кол/Отгр": ["да", "10"],
        "Цена вх/накл": ["УПД-001", "100.50"],
        "цена исх/Оплач?": ["да", "150.00"],
        "Выручка": [1500.00, 1500.00],
        "Маржа": [495.00, 495.00],
        "От кого Зак/Прод": ["Продавец", None],
        "Ст. Закупки": [1005.00, 1005.00],
        "Поставщик/Откат": [0, "Поставщик"],
        "Дата": [None, "15"],
    }

    df = pd.DataFrame(data)
    header_row = pd.DataFrame([list(data.keys())])
    may_sheet = pd.concat([header_row, df], ignore_index=True)
    june_sheet = pd.concat([header_row, df], ignore_index=True)

    excel_file = tmp_path / "period_filter.xlsx"
    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        may_sheet.to_excel(writer, sheet_name="Май 2025", index=False, header=False)
        june_sheet.to_excel(writer, sheet_name="Июнь 2025", index=False, header=False)

    return str(excel_file)


@pytest.mark.unit
def test_read_excel_file_allowed_periods_limits_processed_sheets(multi_sheet_excel: str):
    """Parser should load only requested period sheets when allowed_periods is set."""
    parser = ExcelParserService()
    sheets_data = parser._read_excel_file(
        multi_sheet_excel,
        allowed_periods=["Июнь 2025"],
    )

    assert list(sheets_data.keys()) == ["Июнь 2025"]

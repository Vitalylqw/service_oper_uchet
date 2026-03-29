"""Tests for the CLI sync command group."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from src.cli.main import cli
from src.cli.sync import (
    FilteredExcelParserService,
    _list_available_periods,
    _normalize_period_name,
    _period_sort_key,
    _resolve_explicit_periods,
)


class _StubParser:
    """Simple async parser stub for CLI tests."""

    def __init__(self, result) -> None:
        self._result = result
        self.allowed_periods = None

    async def parse_file(
        self,
        file_path: str,
        sync_session: object | None,
        allowed_periods: list[str] | None = None,
    ):
        self.allowed_periods = allowed_periods
        return self._result


def test_filtered_parser_keeps_only_selected_periods() -> None:
    """CLI parser adapter should pass requested periods into the parser."""
    deals = [
        SimpleNamespace(period_month="Январь", period_year="2025", items=[1, 2]),
        SimpleNamespace(period_month="Февраль", period_year="2025", items=[3]),
    ]
    parse_result = SimpleNamespace(
        deals=deals,
        stats=SimpleNamespace(
            total_deals=2,
            processed_deals=2,
            total_items=3,
            processed_items=3,
            total_sheets=2,
            processed_sheets=2,
        ),
    )
    stub_parser = _StubParser(parse_result)
    parser = FilteredExcelParserService(stub_parser, ["Февраль 2025"])

    result = __import__("asyncio").run(parser.parse_file("test.xlsx", None))

    assert result is parse_result
    assert stub_parser.allowed_periods == ["Февраль 2025"]


def test_period_helpers_normalize_and_sort() -> None:
    """Period helpers should normalize user input and sort descending."""
    assert _normalize_period_name(" январь.2025 ") == "Январь 2025"
    assert _period_sort_key("Февраль 2025") > _period_sort_key("Январь 2025")


def test_resolve_explicit_periods_defaults_to_latest(tmp_path, monkeypatch) -> None:
    """`sync periods` without explicit values should default to the latest period."""
    excel_file = tmp_path / "test.xlsx"
    excel_file.write_text("placeholder", encoding="utf-8")

    monkeypatch.setattr(
        "src.cli.sync._list_available_periods",
        lambda file_path: ["Март 2025", "Февраль 2025", "Январь 2025"],
    )

    periods = _resolve_explicit_periods(Path(excel_file), ())

    assert periods == ["Март 2025"]


def test_sync_periods_command_wires_selected_periods(monkeypatch, tmp_path) -> None:
    """CLI command should pass resolved periods to the sync executor."""
    excel_file = tmp_path / "test.xlsx"
    excel_file.write_text("placeholder", encoding="utf-8")

    monkeypatch.setattr("src.cli.main.initialize_runtime", lambda log_level, env_file: None)
    monkeypatch.setattr("src.cli.sync._validate_excel_path", lambda path: Path(path))
    monkeypatch.setattr(
        "src.cli.sync._resolve_explicit_periods",
        lambda file_path, periods: ["Февраль 2025"],
    )

    captured = {}

    def fake_execute_sync_command(file_path, sync_type, periods):
        captured["file_path"] = Path(file_path)
        captured["sync_type"] = sync_type
        captured["periods"] = periods
        return SimpleNamespace(
            sync_session_id="session-1",
            summary=SimpleNamespace(
                success=True,
                file_path=str(file_path),
                total_deals_processed=1,
                total_items_processed=2,
                insertions_count=0,
                updates_count=1,
                deletions_count=0,
                duration_seconds=1.25,
            ),
            warnings=[],
            errors=[],
        )

    monkeypatch.setattr("src.cli.sync._execute_sync_command", fake_execute_sync_command)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "sync",
            "periods",
            "--file",
            str(excel_file),
            "--periods",
            "Февраль 2025",
        ],
    )

    assert result.exit_code == 0
    assert captured["sync_type"] == "partial"
    assert captured["periods"] == ["Февраль 2025"]


def test_list_available_periods_reads_archive_without_openpyxl(monkeypatch, tmp_path) -> None:
    """Workbook period listing should use archive metadata on the happy path."""
    excel_file = tmp_path / "periods.xlsx"
    excel_file.write_bytes(
        b"PK\x03\x04"
    )

    monkeypatch.setattr(
        "src.cli.sync._read_sheet_names_from_archive",
        lambda file_path: ["Лист1", "Январь 2025", "Февраль 2025"],
    )
    monkeypatch.setattr(
        "src.cli.sync.load_workbook",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("openpyxl fallback not expected")),
    )

    periods = _list_available_periods(excel_file)

    assert periods == ["Февраль 2025", "Январь 2025"]

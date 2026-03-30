"""Tests for the CLI dashboard command group."""

from __future__ import annotations

from click.testing import CliRunner

from src.cli.main import cli


def test_cli_help_shows_dashboard_group(monkeypatch) -> None:
    """Root CLI help should expose the dashboard command group."""
    monkeypatch.setattr("src.cli.main.initialize_runtime", lambda log_level, env_file: None)

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "dashboard" in result.output


def test_dashboard_latest_passes_no_browser(monkeypatch) -> None:
    """Dashboard latest should call wrapper with no-browser flag."""
    monkeypatch.setattr("src.cli.main.initialize_runtime", lambda log_level, env_file: None)
    calls: list[tuple[list[str], bool]] = []
    monkeypatch.setattr(
        "src.cli.dashboard._run_generate_dashboard",
        lambda argv, suppress_browser=False: calls.append((argv, suppress_browser)) or 0,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["dashboard", "latest", "--no-browser"])

    assert result.exit_code == 0
    assert calls == [(["--mode", "latest"], True)]


def test_dashboard_compare_passes_selected_ids(monkeypatch) -> None:
    """Dashboard compare should map IDs into generator argv."""
    monkeypatch.setattr("src.cli.main.initialize_runtime", lambda log_level, env_file: None)
    calls: list[tuple[list[str], bool]] = []
    monkeypatch.setattr(
        "src.cli.dashboard._run_generate_dashboard",
        lambda argv, suppress_browser=False: calls.append((argv, suppress_browser)) or 0,
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["dashboard", "compare", "--id1", "70", "--id2", "71", "--no-browser"],
    )

    assert result.exit_code == 0
    assert calls == [(["--mode", "compare", "--id1", "70", "--id2", "71"], True)]


def test_dashboard_excel_health_passes_periods_and_threshold(monkeypatch, tmp_path) -> None:
    """Excel health command should map options into dashboard argv."""
    monkeypatch.setattr("src.cli.main.initialize_runtime", lambda log_level, env_file: None)
    calls: list[tuple[list[str], bool]] = []
    monkeypatch.setattr(
        "src.cli.dashboard._run_excel_health_dashboard",
        lambda argv, suppress_browser=False: calls.append((argv, suppress_browser)) or 0,
    )
    excel_file = tmp_path / "input.xlsx"
    excel_file.write_text("placeholder", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dashboard",
            "excel-health",
            "--file",
            str(excel_file),
            "--periods",
            "Март 2026",
            "--threshold",
            "1000",
            "--no-browser",
        ],
    )

    assert result.exit_code == 0
    assert calls == [
        (
            [
                "--excel-path",
                str(excel_file),
                "--periods",
                "Март 2026",
                "--threshold",
                "1000.0",
                "--no-browser",
            ],
            True,
        )
    ]

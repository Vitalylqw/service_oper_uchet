"""Tests for the CLI snapshot command group."""

from __future__ import annotations

from click.testing import CliRunner

from src.cli.main import cli
from src.cli.snapshot import SnapshotRow


def test_cli_help_shows_snapshot_group(monkeypatch) -> None:
    """Root CLI help should expose the snapshot command group."""
    monkeypatch.setattr("src.cli.main.initialize_runtime", lambda log_level, env_file: None)

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "snapshot" in result.output


def test_snapshot_create_prints_summary(monkeypatch) -> None:
    """Snapshot create should show saved snapshot summary."""
    monkeypatch.setattr("src.cli.main.initialize_runtime", lambda log_level, env_file: None)
    monkeypatch.setattr(
        "src.cli.snapshot._create_snapshot",
        lambda label, source: {
            "snapshot_id": 42,
            "label": label,
            "source": source,
            "deals_total_rows": 100,
            "pos_total_rows": 250,
            "deal_periods": 3,
            "position_periods": 4,
            "health_issues": 1,
        },
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["snapshot", "create", "--label", "test_cli", "--source", "cli-test"],
    )

    assert result.exit_code == 0
    assert "Snapshot created: id=42, label=test_cli" in result.output
    assert "Source: cli-test" in result.output
    assert "Deals: 100" in result.output
    assert "Positions: 250" in result.output
    assert "Health issues: 1" in result.output


def test_snapshot_list_prints_rows(monkeypatch) -> None:
    """Snapshot list should print recent snapshot rows."""
    monkeypatch.setattr("src.cli.main.initialize_runtime", lambda log_level, env_file: None)
    monkeypatch.setattr(
        "src.cli.snapshot._load_snapshots",
        lambda limit: [
            SnapshotRow(
                snapshot_id=7,
                label="nightly",
                source="cli",
                created_at="2026-03-30 18:00:00",
                deals=631,
                positions=3872,
            )
        ],
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["snapshot", "list", "--limit", "5"])

    assert result.exit_code == 0
    assert "id | label | source | created_at | deals | positions" in result.output
    assert "7 | nightly | cli | 2026-03-30 18:00:00 | 631 | 3872" in result.output

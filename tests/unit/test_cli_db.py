"""Tests for the CLI database command group."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from src.cli import common
from src.cli.main import cli


def test_load_runtime_env_promotes_legacy_db_variables(tmp_path, monkeypatch) -> None:
    """CLI runtime should map legacy config.env keys to DatabaseConfig keys."""
    env_file = tmp_path / "test.env"
    env_file.write_text(
        "\n".join(
            [
                "DB_TYPE=postgresql",
                "DB_HOST=test-host",
                "DB_PORT=15432",
                "DB_NAME=test-db",
                "DB_USER=test-user",
                "DB_PASSWORD=test-pass",
            ]
        ),
        encoding="utf-8",
    )

    for key in [
        "ENV_FILE",
        "DB_TYPE",
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "DB_DB_TYPE",
        "DB_DB_HOST",
        "DB_DB_PORT",
        "DB_DB_NAME",
        "DB_DB_USER",
        "DB_DB_PASSWORD",
        "db_type",
        "db_db_type",
        "db_db_host",
        "db_db_port",
        "db_db_name",
        "db_db_user",
        "db_db_password",
    ]:
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setattr(common, "_DOTENV_LOADED", False)

    loaded_path = common.load_runtime_env(str(env_file))

    assert loaded_path == Path(env_file).resolve()
    assert common.os.environ["DB_DB_TYPE"] == "postgresql"
    assert common.os.environ["DB_DB_HOST"] == "test-host"
    assert common.os.environ["DB_DB_PORT"] == "15432"
    assert common.os.environ["DB_DB_NAME"] == "test-db"
    assert common.os.environ["DB_DB_USER"] == "test-user"
    assert common.os.environ["DB_DB_PASSWORD"] == "test-pass"


def test_cli_help_shows_db_group(monkeypatch) -> None:
    """Root CLI help should expose the db command group."""
    monkeypatch.setattr("src.cli.main.initialize_runtime", lambda log_level, env_file: None)

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "db" in result.output


def test_db_align_maps_apply_fixes_flag(monkeypatch) -> None:
    """CLI align command should map `--apply-fixes` to the existing script."""
    calls = []

    monkeypatch.setattr("src.cli.main.initialize_runtime", lambda log_level, env_file: None)
    monkeypatch.setattr(
        "src.cli.db.run_align_script",
        lambda apply_fixes, stamp: calls.append((apply_fixes, stamp)) or 0,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["db", "align", "--apply-fixes", "--stamp"])

    assert result.exit_code == 0
    assert calls == [(True, True)]

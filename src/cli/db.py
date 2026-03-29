"""Database-related CLI commands."""

from __future__ import annotations

import click
from loguru import logger

from .common import build_database_manager, run_alembic_upgrade, run_align_script, run_async


@click.group(help="Операции с базой данных.")
def db() -> None:
    """Database command group."""


@db.command("test")
def test_connection() -> None:
    """Check database connectivity."""
    manager = build_database_manager()

    try:
        success = run_async(manager.test_connection())
    except Exception as exc:
        raise click.ClickException(f"Ошибка проверки подключения к БД: {exc}") from exc
    finally:
        try:
            run_async(manager.close())
        except Exception as close_exc:
            logger.debug("Database close failed after test: {}", close_exc)

    if not success:
        raise click.ClickException("Подключение к БД не удалось")

    click.echo("Database connection: OK")


@db.command("migrate")
def migrate() -> None:
    """Apply database migrations up to head."""
    try:
        run_alembic_upgrade("head")
    except Exception as exc:
        raise click.ClickException(f"Ошибка применения миграций: {exc}") from exc

    click.echo("Alembic upgrade to head completed")


@db.command("align")
@click.option(
    "--apply-fixes",
    is_flag=True,
    help="Применить известные безопасные исправления схемы перед повторной проверкой.",
)
@click.option(
    "--stamp",
    is_flag=True,
    help="После успешной проверки/исправлений проставить baseline revision.",
)
def align(apply_fixes: bool, stamp: bool) -> None:
    """Align an existing database to the baseline contract."""
    try:
        exit_code = run_align_script(apply_fixes=apply_fixes, stamp=stamp)
    except Exception as exc:
        raise click.ClickException(f"Ошибка запуска align-сценария: {exc}") from exc

    if exit_code != 0:
        raise click.ClickException(f"Align-сценарий завершился с кодом {exit_code}")

    click.echo("Database alignment completed")


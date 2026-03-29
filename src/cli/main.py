"""Main entry point for the `so-uchet` CLI."""

from __future__ import annotations

import click

from .common import initialize_runtime
from .db import db
from .sync import sync


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="DEBUG",
    show_default=True,
    help="Уровень логирования CLI.",
)
@click.option(
    "--env-file",
    type=click.Path(dir_okay=False, path_type=str),
    default=None,
    help="Путь к env-файлу. По умолчанию используется config.env.",
)
@click.pass_context
def cli(ctx: click.Context, log_level: str, env_file: str | None) -> None:
    """Единая CLI-точка входа для Service Oper Uchet."""
    initialize_runtime(log_level=log_level.upper(), env_file=env_file)
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level.upper()
    ctx.obj["env_file"] = env_file


cli.add_command(db)
cli.add_command(sync)

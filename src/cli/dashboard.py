"""Dashboard-related CLI commands."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import click

from .common import PROJECT_ROOT

DASHBOARD_PATH = PROJECT_ROOT / "dashboard"
if str(DASHBOARD_PATH) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_PATH))

import excel_health_dashboard as excel_health_dashboard_module  # noqa: E402
import generate_dashboard as generate_dashboard_module  # noqa: E402

DEFAULT_EXCEL_FILE = (
    PROJECT_ROOT / "data" / "real_data_for_testing" / "Data_source_excel.xlsx"
)


@click.group(help="Генерация dashboard-отчётов.")
def dashboard() -> None:
    """Dashboard command group."""


@dashboard.command("latest")
@click.option(
    "--no-browser",
    is_flag=True,
    help="Не открывать сгенерированный отчёт в браузере.",
)
def dashboard_latest(no_browser: bool) -> None:
    """Generate dashboard for the latest snapshot."""
    exit_code = _run_generate_dashboard(
        ["--mode", "latest"],
        suppress_browser=no_browser,
    )
    _raise_on_failure(exit_code, "Ошибка генерации latest dashboard")


@dashboard.command("compare")
@click.option("--label1", type=str, default=None, help="Метка snapshot A.")
@click.option("--label2", type=str, default=None, help="Метка snapshot B.")
@click.option("--id1", type=int, default=None, help="ID snapshot A.")
@click.option("--id2", type=int, default=None, help="ID snapshot B.")
@click.option(
    "--no-browser",
    is_flag=True,
    help="Не открывать сгенерированный отчёт в браузере.",
)
def dashboard_compare(
    label1: str | None,
    label2: str | None,
    id1: int | None,
    id2: int | None,
    no_browser: bool,
) -> None:
    """Generate dashboard comparing two snapshots."""
    argv = ["--mode", "compare"]
    if label1:
        argv.extend(["--label1", label1])
    if label2:
        argv.extend(["--label2", label2])
    if id1 is not None:
        argv.extend(["--id1", str(id1)])
    if id2 is not None:
        argv.extend(["--id2", str(id2)])

    exit_code = _run_generate_dashboard(argv, suppress_browser=no_browser)
    _raise_on_failure(exit_code, "Ошибка генерации compare dashboard")


@dashboard.command("excel-health")
@click.option(
    "--file",
    "file_path",
    type=click.Path(exists=False, dir_okay=False, path_type=Path),
    default=DEFAULT_EXCEL_FILE,
    show_default=True,
    help="Путь к Excel-файлу.",
)
@click.option(
    "--periods",
    multiple=True,
    help='Конкретные периоды, например: --periods "Январь 2025".',
)
@click.option(
    "--threshold",
    type=float,
    default=None,
    help="Порог расхождения в рублях.",
)
@click.option(
    "--no-browser",
    is_flag=True,
    help="Не открывать сгенерированный отчёт в браузере.",
)
def dashboard_excel_health(
    file_path: Path,
    periods: tuple[str, ...],
    threshold: float | None,
    no_browser: bool,
) -> None:
    """Generate Excel Health dashboard."""
    argv = ["--excel-path", str(file_path)]
    if periods:
        argv.append("--periods")
        argv.extend(periods)
    if threshold is not None:
        argv.extend(["--threshold", str(threshold)])
    if no_browser:
        argv.append("--no-browser")

    exit_code = _run_excel_health_dashboard(argv, suppress_browser=no_browser)
    _raise_on_failure(exit_code, "Ошибка генерации Excel Health dashboard")


def _run_generate_dashboard(argv: list[str], suppress_browser: bool = False) -> int:
    """Run the standalone dashboard generator with CLI-provided argv."""
    return _run_dashboard_entrypoint(
        generate_dashboard_module,
        argv,
        suppress_browser=suppress_browser,
    )


def _run_excel_health_dashboard(argv: list[str], suppress_browser: bool = False) -> int:
    """Run the standalone Excel health generator with CLI-provided argv."""
    return _run_dashboard_entrypoint(
        excel_health_dashboard_module,
        argv,
        suppress_browser=suppress_browser,
    )


def _run_dashboard_entrypoint(module: Any, argv: list[str], suppress_browser: bool) -> int:
    """Invoke a standalone argparse module while controlling browser side effects."""
    with _patched_argv(module, argv), _patched_browser(module, suppress_browser):
        result = module.main()
    return 0 if result is None else int(result)


@contextmanager
def _patched_argv(module: Any, argv: list[str]) -> Iterator[None]:
    """Temporarily replace sys.argv for standalone argparse modules."""
    original_argv = sys.argv[:]
    entry_name = getattr(module, "__file__", module.__name__)
    sys.argv = [entry_name, *argv]
    try:
        yield
    finally:
        sys.argv = original_argv


@contextmanager
def _patched_browser(module: Any, suppress_browser: bool) -> Iterator[None]:
    """Temporarily suppress browser opening for dashboard scripts."""
    if not suppress_browser or not hasattr(module, "webbrowser"):
        yield
        return

    original_open = module.webbrowser.open
    module.webbrowser.open = lambda *args, **kwargs: True
    try:
        yield
    finally:
        module.webbrowser.open = original_open


def _raise_on_failure(exit_code: int, message: str) -> None:
    """Raise ClickException for non-zero exit codes from dashboard scripts."""
    if exit_code != 0:
        raise click.ClickException(f"{message}: код {exit_code}")

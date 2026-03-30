"""Snapshot-related CLI commands."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import click
from sqlalchemy import create_engine, text

from .common import PROJECT_ROOT

try:
    from infrastructure.database.connection import DatabaseConfig
except ImportError:  # pragma: no cover - fallback for repo-local imports
    from src.infrastructure.database.connection import DatabaseConfig

DASHBOARD_PATH = PROJECT_ROOT / "dashboard"
if str(DASHBOARD_PATH) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_PATH))

from db_snapshot_service import collect_snapshot, save_snapshot  # noqa: E402


@dataclass(frozen=True)
class SnapshotRow:
    """Presentation model for snapshot list output."""

    snapshot_id: int
    label: str
    source: str
    created_at: str
    deals: int
    positions: int


@click.group(help="Операции со snapshot-снимками БД.")
def snapshot() -> None:
    """Snapshot command group."""


@snapshot.command("create")
@click.option(
    "--label",
    type=str,
    default=None,
    help="Метка snapshot. По умолчанию генерируется автоматически.",
)
@click.option(
    "--source",
    type=str,
    default="cli",
    show_default=True,
    help="Источник создания snapshot.",
)
def create_snapshot(label: str | None, source: str) -> None:
    """Create a DB snapshot using the existing dashboard service."""
    resolved_label = label or f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        result = _create_snapshot(resolved_label, source)
    except Exception as exc:
        raise click.ClickException(f"Ошибка создания snapshot: {exc}") from exc

    click.echo(f"Snapshot created: id={result['snapshot_id']}, label={result['label']}")
    click.echo(f"Source: {result['source']}")
    click.echo(f"Deals: {result['deals_total_rows']}")
    click.echo(f"Positions: {result['pos_total_rows']}")
    click.echo(f"Deal periods: {result['deal_periods']}")
    click.echo(f"Position periods: {result['position_periods']}")
    click.echo(f"Health issues: {result['health_issues']}")


@snapshot.command("list")
@click.option(
    "--limit",
    type=click.IntRange(min=1),
    default=20,
    show_default=True,
    help="Сколько последних snapshot показать.",
)
def list_snapshots(limit: int) -> None:
    """List recent database snapshots."""
    try:
        rows = _load_snapshots(limit)
    except Exception as exc:
        raise click.ClickException(f"Ошибка загрузки snapshot: {exc}") from exc

    if not rows:
        click.echo("Snapshots not found")
        return

    click.echo("id | label | source | created_at | deals | positions")
    for row in rows:
        click.echo(
            f"{row.snapshot_id} | {row.label} | {row.source} | {row.created_at} | "
            f"{row.deals} | {row.positions}"
        )


def _create_snapshot(label: str, source: str) -> dict[str, Any]:
    """Create a DB snapshot and return summary fields for CLI output."""
    engine = _build_sync_engine()
    try:
        with engine.connect() as conn:
            snap = collect_snapshot(conn, label=label, source=source)
            snapshot_id = save_snapshot(conn, snap)
    finally:
        engine.dispose()

    health_issues = sum(
        1
        for value in snap.health_checks.values()
        if isinstance(value, dict) and value.get("status") in {"WARN", "FAIL"}
    )

    return {
        "snapshot_id": snapshot_id,
        "label": snap.label,
        "source": snap.source,
        "deals_total_rows": snap.deals_total_rows,
        "pos_total_rows": snap.pos_total_rows,
        "deal_periods": len(snap.deal_periods),
        "position_periods": len(snap.position_periods),
        "health_issues": health_issues,
    }


def _load_snapshots(limit: int) -> list[SnapshotRow]:
    """Load recent snapshots from the database."""
    engine = _build_sync_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT id, label, source, created_at, deals_total_rows, pos_total_rows
                    FROM db_snapshots
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
            rows = result.mappings().all()
    finally:
        engine.dispose()

    return [
        SnapshotRow(
            snapshot_id=row["id"],
            label=row["label"] or "-",
            source=row["source"],
            created_at=_format_datetime(row["created_at"]),
            deals=row["deals_total_rows"],
            positions=row["pos_total_rows"],
        )
        for row in rows
    ]


def _build_sync_engine():
    """Create sync SQLAlchemy engine for snapshot commands."""
    config = DatabaseConfig()
    return create_engine(config.sync_database_url, echo=False, future=True)


def _format_datetime(value: Any) -> str:
    """Format timestamps for console output."""
    if value is None:
        return "-"
    if hasattr(value, "isoformat"):
        return value.isoformat(sep=" ", timespec="seconds")
    return str(value)

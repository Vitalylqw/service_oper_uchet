"""Bulk refresh of Excel source row metadata in read models.

This worker intentionally does not create domain events and does not trigger
atomic deal rewrites. It updates only read-side source metadata used for
traceability and report ordering.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from loguru import logger
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models import Deal

from ..database.models import ReadModelDeal, ReadModelPosition


@dataclass
class SourceLocationRefreshResult:
    """Result counters for source row metadata refresh."""

    deals_seen: int = 0
    positions_seen: int = 0
    deal_rows_refreshed: int = 0
    position_rows_refreshed: int = 0
    warnings: list[str] = field(default_factory=list)


class SourceLocationRefresher:
    """Refresh Excel source row numbers in read models using chunked bulk updates."""

    def __init__(self, session: AsyncSession, chunk_size: int = 1000) -> None:
        """Initialize refresher.

        Args:
            session: Active SQLAlchemy async session.
            chunk_size: Maximum rows per bulk SQL statement.
        """
        self.session = session
        self.chunk_size = chunk_size

    async def refresh(self, deals: list[Deal]) -> SourceLocationRefreshResult:
        """Refresh source row numbers for parsed deals and their positions.

        Args:
            deals: Parsed deals from the current Excel sync scope.

        Returns:
            SourceLocationRefreshResult with counters and non-fatal warnings.
        """
        result = SourceLocationRefreshResult()
        if not deals:
            return result

        try:
            deal_rows = self._build_deal_rows(deals, result)
            position_rows = self._build_position_rows(deals, result)

            result.deals_seen = len(deal_rows)
            result.positions_seen = len(position_rows)

            bind = self.session.get_bind()
            dialect_name = bind.dialect.name if bind is not None else ""

            if deal_rows:
                result.deal_rows_refreshed = await self._refresh_deals(
                    deal_rows,
                    dialect_name,
                )
            if position_rows:
                result.position_rows_refreshed = await self._refresh_positions(
                    position_rows,
                    dialect_name,
                )
        except Exception:
            await self.session.rollback()
            raise

        logger.info(
            "Source row refresh completed: deals_seen={} deals_updated={} "
            "positions_seen={} positions_updated={} warnings={}",
            result.deals_seen,
            result.deal_rows_refreshed,
            result.positions_seen,
            result.position_rows_refreshed,
            len(result.warnings),
        )
        return result

    def _build_deal_rows(
        self,
        deals: list[Deal],
        result: SourceLocationRefreshResult,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        period_rows: dict[tuple[str, str], list[int]] = defaultdict(list)

        for deal in deals:
            row_number = deal.source_row_number
            if row_number is None:
                result.warnings.append(
                    f"Deal has no source row: period={deal.period_month} "
                    f"{deal.period_year} deal_key={deal.deal_key}"
                )
            else:
                period_rows[(deal.period_year, deal.period_month)].append(row_number)

            rows.append(
                {
                    "deal_key": deal.deal_key,
                    "period_year": deal.period_year,
                    "period_month": deal.period_month,
                    "source_row_number": row_number,
                }
            )

        for (year, month), row_numbers in period_rows.items():
            duplicates = [row for row, count in Counter(row_numbers).items() if count > 1]
            for duplicate in sorted(duplicates):
                result.warnings.append(
                    f"Duplicate deal source row in period {month} {year}: row {duplicate}"
                )

        return rows

    def _build_position_rows(
        self,
        deals: list[Deal],
        result: SourceLocationRefreshResult,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        for deal in deals:
            deal_position_rows: list[int] = []
            for item in deal.items:
                row_number = item.source_row_number
                if row_number is None:
                    result.warnings.append(
                        f"Position has no source row: deal_key={deal.deal_key} "
                        f"position={item.position_number}"
                    )
                else:
                    deal_position_rows.append(row_number)

                rows.append(
                    {
                        "deal_key": deal.deal_key,
                        "period_year": deal.period_year,
                        "period_month": deal.period_month,
                        "position_number": item.position_number,
                        "source_row_number": row_number,
                    }
                )

            duplicates = [
                row for row, count in Counter(deal_position_rows).items() if count > 1
            ]
            for duplicate in sorted(duplicates):
                result.warnings.append(
                    f"Duplicate position source row in deal {deal.deal_key}: row {duplicate}"
                )

        return rows

    async def _refresh_deals(
        self,
        rows: list[dict[str, Any]],
        dialect_name: str,
    ) -> int:
        updated = 0
        for chunk in self._chunks(rows):
            if dialect_name == "postgresql":
                updated += await self._refresh_deals_postgresql(chunk)
            else:
                updated += await self._refresh_deals_generic(chunk)
        return updated

    async def _refresh_positions(
        self,
        rows: list[dict[str, Any]],
        dialect_name: str,
    ) -> int:
        updated = 0
        for chunk in self._chunks(rows):
            if dialect_name == "postgresql":
                updated += await self._refresh_positions_postgresql(chunk)
            else:
                updated += await self._refresh_positions_generic(chunk)
        return updated

    async def _refresh_deals_postgresql(self, rows: list[dict[str, Any]]) -> int:
        values_sql, params = self._values_sql(
            rows,
            ("deal_key", "period_year", "period_month", "source_row_number"),
        )
        params = self._stringify_pg_integer_params(params, ("source_row_number",))
        stmt = text(
            f"""
            UPDATE read_deals AS d
            SET source_row_number = v.source_row_number::integer,
                updated_at = now()
            FROM (VALUES {values_sql})
                AS v(deal_key, period_year, period_month, source_row_number)
            WHERE d.deal_key = v.deal_key
              AND d.period_year = v.period_year
              AND d.period_month = v.period_month
              AND d.source_row_number IS DISTINCT FROM v.source_row_number::integer
            """
        )
        result = await self.session.execute(stmt, params)
        return int(result.rowcount or 0)

    async def _refresh_positions_postgresql(self, rows: list[dict[str, Any]]) -> int:
        values_sql, params = self._values_sql(
            rows,
            (
                "deal_key",
                "period_year",
                "period_month",
                "position_number",
                "source_row_number",
            ),
        )
        params = self._stringify_pg_integer_params(
            params,
            ("position_number", "source_row_number"),
        )
        stmt = text(
            f"""
            UPDATE read_positions AS p
            SET source_row_number = v.source_row_number::integer,
                updated_at = now()
            FROM (VALUES {values_sql})
                AS v(deal_key, period_year, period_month, position_number, source_row_number)
            WHERE p.deal_key = v.deal_key
              AND p.period_year = v.period_year
              AND p.period_month = v.period_month
              AND p.position_number = v.position_number::integer
              AND p.source_row_number IS DISTINCT FROM v.source_row_number::integer
            """
        )
        result = await self.session.execute(stmt, params)
        return int(result.rowcount or 0)

    async def _refresh_deals_generic(self, rows: list[dict[str, Any]]) -> int:
        updated = 0
        for row in rows:
            stmt = (
                update(ReadModelDeal)
                .where(ReadModelDeal.deal_key == row["deal_key"])
                .where(ReadModelDeal.period_year == row["period_year"])
                .where(ReadModelDeal.period_month == row["period_month"])
                .where(
                    ReadModelDeal.source_row_number.is_distinct_from(
                        row["source_row_number"]
                    )
                )
                .values(source_row_number=row["source_row_number"])
            )
            result = await self.session.execute(stmt)
            updated += int(result.rowcount or 0)
        return updated

    async def _refresh_positions_generic(self, rows: list[dict[str, Any]]) -> int:
        updated = 0
        for row in rows:
            stmt = (
                update(ReadModelPosition)
                .where(ReadModelPosition.deal_key == row["deal_key"])
                .where(ReadModelPosition.period_year == row["period_year"])
                .where(ReadModelPosition.period_month == row["period_month"])
                .where(ReadModelPosition.position_number == row["position_number"])
                .where(
                    ReadModelPosition.source_row_number.is_distinct_from(
                        row["source_row_number"]
                    )
                )
                .values(source_row_number=row["source_row_number"])
            )
            result = await self.session.execute(stmt)
            updated += int(result.rowcount or 0)
        return updated

    def _chunks(self, rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        return [
            rows[index : index + self.chunk_size]
            for index in range(0, len(rows), self.chunk_size)
        ]

    @staticmethod
    def _values_sql(
        rows: list[dict[str, Any]],
        columns: tuple[str, ...],
    ) -> tuple[str, dict[str, Any]]:
        values_parts: list[str] = []
        params: dict[str, Any] = {}

        for row_index, row in enumerate(rows):
            placeholders = []
            for column in columns:
                param_name = f"{column}_{row_index}"
                placeholders.append(f":{param_name}")
                params[param_name] = row[column]
            values_parts.append(f"({', '.join(placeholders)})")

        return ", ".join(values_parts), params

    @staticmethod
    def _stringify_pg_integer_params(
        params: dict[str, Any],
        columns: tuple[str, ...],
    ) -> dict[str, Any]:
        """Keep asyncpg VALUES type inference stable for integer metadata columns."""
        integer_suffixes = tuple(f"{column}_" for column in columns)
        return {
            key: str(value)
            if value is not None and key.startswith(integer_suffixes)
            else value
            for key, value in params.items()
        }

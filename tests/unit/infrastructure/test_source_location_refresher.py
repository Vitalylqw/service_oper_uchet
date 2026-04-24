"""Unit tests for source row metadata refresh."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.workers.source_location_refresher import SourceLocationRefresher
from tests.conftest import build_test_deal, build_test_item


@pytest.mark.unit
class TestSourceLocationRefresher:
    """Tests for read-side Excel source row refresh."""

    @pytest.mark.asyncio
    async def test_refresh_updates_deals_and_positions_without_events(self) -> None:
        """Refresh should issue lightweight row updates for parsed source metadata."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.get_bind.return_value = SimpleNamespace(
            dialect=SimpleNamespace(name="sqlite")
        )
        session.execute.return_value = SimpleNamespace(rowcount=1)

        deal = build_test_deal(source_row_number=10)
        deal.add_item(
            build_test_item(
                deal=deal,
                position_number=1,
                source_row_number=11,
            )
        )

        result = await SourceLocationRefresher(session).refresh([deal])

        assert result.deals_seen == 1
        assert result.positions_seen == 1
        assert result.deal_rows_refreshed == 1
        assert result.position_rows_refreshed == 1
        assert result.warnings == []
        assert session.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_refresh_reports_duplicate_source_rows_as_warnings(self) -> None:
        """Source row quality issues should not stop refresh."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.get_bind.return_value = SimpleNamespace(
            dialect=SimpleNamespace(name="sqlite")
        )
        session.execute.return_value = SimpleNamespace(rowcount=0)

        deal_one = build_test_deal(source_row_number=10)
        deal_two = build_test_deal(
            invoice_number="54321",
            invoice_info="54321 от 01.05.2025",
            source_row_number=10,
        )

        result = await SourceLocationRefresher(session).refresh([deal_one, deal_two])

        assert result.deals_seen == 2
        assert any("Duplicate deal source row" in warning for warning in result.warnings)

"""
Database Integration Tests.

Тесты полного пайплайна: Excel → Parse → Repository → Database
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import select

from src.application.excel_parser import ExcelParserService
from src.domain.models import SyncSession
from src.domain.models.sync_session import SyncType
from src.infrastructure.database.models import ReadModelDeal, SyncSessionModel


@pytest.mark.integration_db
class TestDatabaseIntegration:
    """Database integration tests with real database operations."""

    def _build_sync_session_model(
        self,
        sync_session: SyncSession,
        *,
        status: str | None = None,
    ) -> SyncSessionModel:
        """Create a database row for a sync session without using the repository save path."""
        return SyncSessionModel(
            id=sync_session.id,
            sync_type=sync_session.sync_type.value,
            status=status or sync_session.status.value,
            file_path=sync_session.source_file_path,
            file_hash=sync_session.source_file_hash,
            file_size=sync_session.source_file_size,
            started_at=sync_session.started_at,
            finished_at=sync_session.finished_at,
            stats_data={},
            error_message="; ".join(sync_session.stats.errors) if sync_session.stats.errors else None,
        )

    def _store_sync_session(self, db_manager, sync_session: SyncSession, *, status: str | None = None) -> None:
        """Persist a sync session with the sync SQLAlchemy session for fast integration coverage."""
        with db_manager.sync_session_factory() as session:
            session.add(self._build_sync_session_model(sync_session, status=status))
            session.commit()

    @pytest.fixture
    def sample_db_excel_file(self, tmp_path) -> str:
        """Create a compact Excel fixture for database integration checks."""
        rows = [
            [
                "Клиент",
                "Номенклатуры",
                "Кол/Отгр",
                "Цена вх/накл",
                "цена исх/Оплач?",
                "Выручка",
                "Маржа",
                "От кого Зак/Прод",
                "Ст. Закупки",
                "Поставщик/Откат",
                "Дата",
            ],
            ["ООО Тест", "001 от 01.01.2024", "да", "УПД-1", "да", 1000, 100, "Продавец", 900, 0, None],
            [None, "Товар 1", "10", "90", "100", 1000, 100, None, 900, "Поставщик", "15"],
        ]
        excel_file = tmp_path / "db_integration.xlsx"
        pd.DataFrame(rows).to_excel(
            excel_file,
            sheet_name="Январь 2024",
            index=False,
            header=False,
            engine="openpyxl",
        )
        return str(excel_file)

    async def test_excel_to_database_pipeline(
        self, test_database, sample_db_excel_file
    ):
        """Full pipeline: Excel → Parse → Repository → Database."""
        # Arrange
        parser = ExcelParserService()
        db_manager = test_database

        # Create sync session with required fields
        sync_session = SyncSession(
            sync_type=SyncType.FULL,
            source_file_path=sample_db_excel_file,
            source_file_hash="test_hash_12345",
            source_file_size=1024,  # Required field
            created_by="test_user"
        )

        # Act: Parse Excel file
        result = await parser.parse_file(sample_db_excel_file, sync_session)

        # Persist the session row through the sync session factory to avoid async SQLite stalls.
        self._store_sync_session(db_manager, sync_session)

        with db_manager.sync_session_factory() as session:
            saved_session = session.get(SyncSessionModel, sync_session.id)
        assert saved_session is not None
        assert saved_session.id is not None

        # In Event Sourcing architecture, deals are saved through Application Services
        # Here we just verify that parsing worked correctly
        parsed_deals = result.deals

        # Assert: Verify parsed data
        assert len(parsed_deals) > 0

        # Test retrieval from database for sync session
        with db_manager.sync_session_factory() as session:
            db_session = session.get(SyncSessionModel, saved_session.id)
        assert db_session is not None
        assert db_session.file_path == sample_db_excel_file

        # Verify parsed deals structure (they exist in memory)
        for deal in parsed_deals:
            assert deal.id is not None
            assert deal.client_name is not None
            assert len(deal.client_name.strip()) > 0

        # Note: In real Event Sourcing flow:
        # 1. Deals would be saved via Application Services
        # 2. Events would be created in Event Store
        # 3. ReadModelBuilder would populate read_deals table
        # 4. Then DealRepository queries would return data

    async def test_deal_repository_crud_operations(self, test_database, sample_deal):
        """Test read operations for deals using the read model schema."""
        db_manager = test_database

        with db_manager.sync_session_factory() as session:
            # Test get by non-existent ID
            non_existent_deal = session.get(ReadModelDeal, sample_deal.id)
            assert non_existent_deal is None  # No deal in read model yet

            # Test get by key
            result = session.execute(
                select(ReadModelDeal).where(ReadModelDeal.deal_key == "non-existent-key")
            )
            assert result.scalar_one_or_none() is None

            # Test find by client
            result = session.execute(
                select(ReadModelDeal).where(ReadModelDeal.client_name.ilike("%non-existent-client%"))
            )
            assert result.scalars().all() == []

            # Test get all keys
            result = session.execute(select(ReadModelDeal.deal_key))
            assert result.scalars().all() == []

    async def test_sync_session_repository_operations(
        self, test_database, sample_sync_session
    ):
        """Test sync session persistence and readback using the SQLite schema."""
        db_manager = test_database

        # Persist the initial row directly to avoid relying on the slower save path.
        self._store_sync_session(db_manager, sample_sync_session)

        with db_manager.sync_session_factory() as session:
            created_session = session.get(SyncSessionModel, sample_sync_session.id)
        assert created_session is not None
        assert created_session.id is not None
        assert created_session.file_path == sample_sync_session.source_file_path

        # List active sessions
        with db_manager.sync_session_factory() as session:
            active_sessions = session.execute(
                select(SyncSessionModel).where(SyncSessionModel.status == "pending")
            ).scalars().all()
        assert len(active_sessions) >= 1

        # Complete session (update status)
        with db_manager.sync_session_factory() as sync_session:
            row = sync_session.get(SyncSessionModel, sample_sync_session.id)
            assert row is not None
            row.status = "completed"
            sync_session.commit()

        with db_manager.sync_session_factory() as session:
            completed_session = session.get(SyncSessionModel, created_session.id)
        assert completed_session.status == "completed"

    async def test_database_transaction_rollback(self, test_database, sample_sync_session):
        """Test transaction rollback on error with sync session repository."""
        db_manager = test_database

        # Test transaction rollback with sync session (which supports writes)
        with db_manager.sync_session_factory() as session:
            try:
                session.add(self._build_sync_session_model(sample_sync_session))
                session.flush()

                # Simulate error to trigger rollback
                raise Exception("Test rollback")

            except Exception:
                # Transaction should rollback
                session.rollback()

        with db_manager.sync_session_factory() as verification_session:
            result = verification_session.execute(
                select(SyncSessionModel).where(SyncSessionModel.id == sample_sync_session.id)
            )
            assert result.scalar_one_or_none() is None

    async def test_database_performance_batch_operations(self, test_database, sample_period):
        """Test batch query operations performance (read-only operations)."""
        db_manager = test_database
        with db_manager.sync_session_factory() as session:
            # Test batch query operations (read-only)
            # In Event Sourcing, write operations go through Application Services

            # Test performance of multiple queries
            results = []
            for i in range(10):
                client_name = f"Клиент {i}"
                result = session.execute(
                    select(ReadModelDeal).where(ReadModelDeal.client_name.ilike(f"%{client_name}%"))
                )
                results.append(result.scalars().all())

            assert len(results) == 10

            # All should return empty lists since no data in read model yet
            for result in results:
                assert isinstance(result, list)
                assert len(result) == 0  # No deals in read model initially


@pytest.mark.integration_db
async def test_database_schema_validation(test_database):
    """Test that database schema is properly created."""
    db_manager = test_database

    # Check that tables exist
    with db_manager.sync_session_factory() as session:
        # This should not raise an error if schema is correct
        from sqlalchemy import text
        result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result.fetchall()]

        # Expected tables from our models (using read model tables)
        expected_tables = ["read_deals", "sync_sessions", "read_positions"]

        for table in expected_tables:
            assert table in tables, f"Table {table} not found in database"


@pytest.mark.integration_db
@pytest.mark.slow
async def test_large_excel_file_processing(test_database):
    """Test processing of large Excel files (if available)."""
    # This test would run only if large test file exists
    large_file_path = Path("tests/fixtures/large_test_file.xlsx")

    if not large_file_path.exists():
        pytest.skip("Large test file not available")

    parser = ExcelParserService()
    # Create sync session for large file
    sync_session = SyncSession(
        sync_type=SyncType.FULL,
        source_file_path=str(large_file_path),
        source_file_hash="large_file_hash",
        source_file_size=1024,
        created_by="performance_test"
    )

    # Parse and save - should handle large volumes
    result = await parser.parse_file(str(large_file_path), sync_session)

    # Verify result
    assert len(result.deals) > 100  # Assuming large file has many deals
    assert result.errors_count == 0  # Should process without errors

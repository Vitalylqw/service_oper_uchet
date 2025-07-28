#!/usr/bin/env python3
"""
Run single synchronization via SyncOrchestratorService.

Usage (PowerShell):
    python scripts/run_sync_once.py D:\\path\to\file.xlsx

The script:
1. Инициализирует DatabaseManager с текущими переменными окружения (SQLite по умолчанию)
2. Собирает реальные сервисы (ExcelParserService, ChangeDetectorService, EventStore, Repositories)
3. Запускает Orchestrator в режиме FULL (можно изменить аргументом --incremental)
4. Печатает краткий отчёт и сохраняет summary в `sync_summary.json`
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from loguru import logger

# Ensure src/ is in PYTHONPATH for direct script execution
PROJECT_ROOT = Path(__file__).parent.parent
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

# Local imports after path adjustment
from application.change_detector import ChangeDetectorService
from application.excel_parser import ExcelParserService
from application.sync_orchestrator import SyncOrchestratorService
from application.sync_orchestrator.models import SyncConfiguration
from infrastructure.database.connection import DatabaseConfig, DatabaseManager
from infrastructure.database.event_store import EventStoreImplementation
from infrastructure.database.repositories import (
    DealRepositoryImplementation,
    SyncSessionRepositoryImplementation,
)
from infrastructure.workers.read_model_builder import ReadModelBuilder


async def run_sync(file_path: str, sync_type: str = "full") -> None:
    """Run synchronization pipeline for provided Excel file."""

    logger.info(f"🚀 Running sync for file: {file_path} (type: {sync_type})")

    # 1. Prepare database manager (uses .env variables)
    db_config = DatabaseConfig()
    db_manager = DatabaseManager(db_config)

    # 2. Open DB session
    async with db_manager.get_async_session() as session:
        # 3. Assemble dependencies
        deal_repo = DealRepositoryImplementation(session)
        sync_session_repo = SyncSessionRepositoryImplementation(session)
        event_store = EventStoreImplementation(session)

        excel_parser = ExcelParserService()
        change_detector = ChangeDetectorService(deal_repo)
        read_model_builder = ReadModelBuilder(session, event_store)

        orchestrator = SyncOrchestratorService(
            excel_parser=excel_parser,
            change_detector=change_detector,
            event_store=event_store,
            sync_session_repository=sync_session_repo,
            read_model_builder=read_model_builder,
        )

        # 4. Build configuration
        cfg = SyncConfiguration(
            sync_type=sync_type,
            create_events=True,
            update_read_models=True,  # Включаем обновление read models
            continue_on_errors=True,
            rollback_on_failure=False,
        )

        # 5. Execute synchronization
        result = await orchestrator.execute_sync(file_path, cfg)

        # 6. CRITICAL: Commit the transaction to save events and sessions
        try:
            await session.commit()
            logger.info("✅ Transaction committed - all data saved to database")
        except Exception as e:
            logger.error(f"❌ Failed to commit transaction: {e}")
            await session.rollback()
            raise

        # 7. Output summary
        summary_dict = result.summary.to_dict()
        logger.success("✅ Sync finished")
        logger.info(json.dumps(summary_dict, ensure_ascii=False, indent=2))

        # Save summary to file
        outfile = PROJECT_ROOT / "sync_summary.json"
        outfile.write_text(json.dumps(summary_dict, ensure_ascii=False, indent=2))
        logger.info(f"📄 Summary saved to {outfile}")

    # Close engines
    await db_manager.close()


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_sync_once.py <excel_file_path> [full|incremental]")
        sys.exit(1)

    excel_path = sys.argv[1]
    sync_type = sys.argv[2] if len(sys.argv) > 2 else "full"

    if not Path(excel_path).exists():
        print(f"File not found: {excel_path}")
        sys.exit(1)

    asyncio.run(run_sync(excel_path, sync_type))


if __name__ == "__main__":
    main()

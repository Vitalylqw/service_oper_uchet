#!/usr/bin/env python3
"""
Создание новой базы данных с нуля.

Скрипт создает базу данных с учетом всех новых изменений структуры,
включая новое поле position_number и удаление position_key.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from loguru import logger


async def create_new_database():
    """Создать новую базу данных с нуля."""
    
    logger.info("🚀 Создание новой базы данных...")
    
    try:
        # Set environment for SQLite
        os.environ["DB_TYPE"] = "sqlite"
        db_path = Path("data/service_oper_uchet.sqlite")
        os.environ["DB_SQLITE_DB_PATH"] = str(db_path)
        
        # Remove existing database file if exists
        if db_path.exists():
            db_path.unlink()
            logger.info(f"🗑️ Удален существующий файл: {db_path}")
        
        # Ensure data directory exists
        db_path.parent.mkdir(exist_ok=True)
        
        # Import after setting environment
        from src.infrastructure.database.connection import DatabaseManager, DatabaseConfig
        from src.infrastructure.database.models import Base
        
        # Create database config
        config = DatabaseConfig()
        db_manager = DatabaseManager(config)
        
        # Step 1: Create all tables with new structure
        logger.info("📋 Шаг 1: Создание таблиц...")
        
        # Create tables using the updated models (includes position_number, no position_key)
        Base.metadata.create_all(db_manager.sync_engine)
        logger.info("✅ Таблицы созданы с новой структурой")
        
        # Step 2: Test connection
        logger.info("🔌 Шаг 2: Проверка подключения...")
        
        connection_ok = await db_manager.test_connection()
        if not connection_ok:
            raise RuntimeError("Не удалось подключиться к базе данных")
        
        logger.info("✅ Подключение работает")
        
        # Step 3: Verify table structure
        logger.info("🔍 Шаг 3: Проверка структуры таблиц...")
        
        async with db_manager.get_async_session() as session:
            from sqlalchemy import text
            
            # Check read_positions table structure
            result = await session.execute(text("PRAGMA table_info(read_positions)"))
            columns = result.fetchall()
            
            column_names = [col[1] for col in columns]
            
            # Verify new structure
            required_columns = [
                'id', 'deal_id', 'deal_key', 'position_number', 'hash_key',
                'product_name', 'supplier_name', 'pickup_date'
            ]
            
            missing_columns = [col for col in required_columns if col not in column_names]
            if missing_columns:
                raise RuntimeError(f"Отсутствуют столбцы: {missing_columns}")
            
            # Verify position_key is NOT present
            if 'position_key' in column_names:
                logger.warning("⚠️ Столбец position_key все еще присутствует")
            else:
                logger.info("✅ Столбец position_key успешно удален")
            
            # Verify position_number is present
            if 'position_number' in column_names:
                logger.info("✅ Столбец position_number добавлен")
            else:
                raise RuntimeError("Столбец position_number отсутствует")
        
        # Step 4: Create sample sync session (optional)
        logger.info("📝 Шаг 4: Создание тестовой сессии...")
        
        async with db_manager.get_async_session() as session:
            from src.domain.models import SyncSession
            from src.infrastructure.database.models import EventStore
            from sqlalchemy import insert
            import json
            import uuid
            from datetime import datetime
            
            # Create a test sync session event
            session_id = str(uuid.uuid4())
            event_data = {
                "id": session_id,
                "status": "COMPLETED",
                "file_path": "test_structure.xlsx",
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "stats": {
                    "total_deals": 0,
                    "processed_deals": 0,
                    "failed_deals": 0,
                    "total_items": 0,
                    "processed_items": 0,
                    "failed_items": 0,
                    "errors": [],
                    "warnings": []
                }
            }
            
            # Insert test event
            stmt = insert(EventStore).values(
                event_id=str(uuid.uuid4()),
                aggregate_id=session_id,
                aggregate_type="SyncSession",
                event_type="SyncSessionCompleted",
                event_version=1,
                event_data=json.dumps(event_data),
                sequence_number=1,
                created_at=datetime.now()
            )
            
            await session.execute(stmt)
            await session.commit()
            
        logger.info("✅ Тестовая сессия создана")
        
        # Final success message
        logger.info("🎉 БАЗА ДАННЫХ УСПЕШНО СОЗДАНА!")
        logger.info(f"📂 Путь к файлу: {db_path}")
        logger.info("📊 Структура:")
        logger.info("   - Event Store (события)")
        logger.info("   - Read Models (оптимизированные представления)")
        logger.info("   - Audit Trail (аудит изменений)")
        logger.info("✨ Новая структура с position_number готова к использованию!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания базы данных: {e}")
        return False


if __name__ == "__main__":
    # Add the project root to Python path
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Run the database creation
    success = asyncio.run(create_new_database())
    
    if success:
        print("\n🎯 База данных готова к работе!")
        print("   Теперь можно запускать синхронизацию Excel файлов")
    else:
        print("\n💥 Создание базы данных не удалось!")
        sys.exit(1)
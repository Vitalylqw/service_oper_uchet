#!/usr/bin/env python3
"""
Test script for the new database schema.

This script verifies that the new migration works correctly
and all tables are accessible.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select


async def test_new_schema():
    """Test the new database schema."""
    engine = create_async_engine('postgresql+asyncpg://so_user:so_pass@so_pg:5432/so_uchet')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            print("🔍 Тестирование новой схемы БД...")
            
            # 1. Проверяем все таблицы
            print("\n1. Проверка существования таблиц:")
            tables = [
                'event_store', 'read_deals', 'read_positions', 
                'read_audit', 'read_stats', 'sync_sessions', 'alembic_version'
            ]
            
            for table in tables:
                result = await session.execute(text(f"""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = '{table}'
                """))
                count = result.scalar()
                status = "✅" if count > 0 else "❌"
                print(f"  {status} {table}")
            
            # 2. Проверяем версию миграции
            print("\n2. Версия миграции:")
            result = await session.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            print(f"  Текущая версия: {version}")
            
            # 3. Проверяем server defaults в read_deals
            print("\n3. Проверка server defaults:")
            result = await session.execute(text("""
                SELECT 
                    column_name, 
                    column_default 
                FROM information_schema.columns 
                WHERE table_name = 'read_deals' 
                AND column_default IS NOT NULL
                ORDER BY column_name
            """))
            defaults = result.fetchall()
            for col_name, col_default in defaults:
                if col_name in ['calc_revenue_amount', 'calc_margin_amount', 'calc_cost_amount', 'has_totals_error', 'items_count']:
                    print(f"  ✅ {col_name}: {col_default}")
            
            # 4. Проверяем индексы
            print("\n4. Проверка ключевых индексов:")
            key_indexes = [
                'ix_read_positions_hash_key',
                'ix_read_positions_deal_hash',
                'ix_read_deals_client_name'
            ]
            
            for index in key_indexes:
                result = await session.execute(text(f"""
                    SELECT COUNT(*) FROM pg_indexes 
                    WHERE indexname = '{index}'
                """))
                count = result.scalar()
                status = "✅" if count > 0 else "❌"
                print(f"  {status} {index}")
            
            # 5. Проверяем уникальность индекса hash_key
            result = await session.execute(text("""
                SELECT indisunique FROM pg_index 
                JOIN pg_class ON pg_index.indexrelid = pg_class.oid 
                WHERE pg_class.relname = 'ix_read_positions_hash_key'
            """))
            is_unique = result.scalar()
            status = "✅" if is_unique else "❌"
            print(f"  {status} ix_read_positions_hash_key is unique: {is_unique}")
            
            # 6. Проверяем foreign key constraint
            print("\n5. Проверка foreign key constraints:")
            result = await session.execute(text("""
                SELECT COUNT(*) FROM information_schema.referential_constraints 
                WHERE constraint_name LIKE '%read_positions_deal_id_fkey%'
            """))
            fk_count = result.scalar()
            status = "✅" if fk_count > 0 else "❌"
            print(f"  {status} read_positions -> read_deals FK: {fk_count > 0}")
            
            print("\n🎉 Тестирование завершено!")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_new_schema())








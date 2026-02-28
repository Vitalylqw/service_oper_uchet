#!/usr/bin/env python3
"""
Script to fix schema differences after migration cleanup.

This script applies the necessary changes to align the existing database
with the new clean migration structure.
"""
from __future__ import annotations

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def fix_schema_differences():
    """Apply necessary schema fixes."""
    engine = create_async_engine('postgresql+asyncpg://so_user:so_pass@so_pg:5432/so_uchet')
    
    try:
        async with engine.begin() as conn:
            print("Применяю изменения схемы...")
            
            # 1. Добавляем server defaults для read_deals
            print("1. Добавляю server defaults для read_deals...")
            await conn.execute(text("""
                ALTER TABLE read_deals 
                ALTER COLUMN calc_revenue_amount SET DEFAULT 0,
                ALTER COLUMN calc_margin_amount SET DEFAULT 0,
                ALTER COLUMN calc_cost_amount SET DEFAULT 0,
                ALTER COLUMN has_totals_error SET DEFAULT false,
                ALTER COLUMN items_count SET DEFAULT 0
            """))
            
            # 2. Удаляем старый индекс hash_key
            print("2. Обновляю индекс hash_key...")
            await conn.execute(text("""
                DROP INDEX IF EXISTS ix_read_positions_hash_key
            """))
            
            # 3. Создаем уникальный индекс hash_key
            await conn.execute(text("""
                CREATE UNIQUE INDEX ix_read_positions_hash_key 
                ON read_positions (hash_key)
            """))
            
            # 4. Добавляем недостающий индекс deal_hash
            print("3. Добавляю индекс deal_hash...")
            await conn.execute(text("""
                CREATE INDEX ix_read_positions_deal_hash 
                ON read_positions (deal_id, hash_key)
            """))
            
            print("✅ Все изменения схемы применены успешно!")
            
    except Exception as e:
        print(f"❌ Ошибка при применении изменений: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix_schema_differences())








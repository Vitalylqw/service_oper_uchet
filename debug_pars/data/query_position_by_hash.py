#!/usr/bin/env python3
"""
Скрипт для запроса позиции по hash_key из таблицы read_positions.

Выполняет запрос к БД и показывает детальную информацию о позиции
с указанным hash_key = f555c1114bebd7aa85d2a9c46def52d3
"""

import asyncio
import sys
from pathlib import Path

# Add src to path (для запуска из debug_pars/data/ нужно подняться на 2 уровня)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loguru import logger
from sqlalchemy import text

target_hash_key = "441e17f98d8c963b2d3ab2dc0e3c7116"

async def query_position_by_hash() -> None:
    """Запрос позиции по hash_key."""

    logger.info(f"🔍 Поиск позиции с hash_key = {target_hash_key}")
    
    try:
        # Import database components
        from infrastructure.database.connection import DatabaseConfig, DatabaseManager
        
        # Initialize database manager
        config = DatabaseConfig()
        db_manager = DatabaseManager(config)
        
        # Get async session
        async with db_manager.get_async_session() as session:
            
            # Выполняем запрос
            query = text("""
                SELECT 
                    id,
                    deal_id,
                    deal_key,
                    position_number,
                    hash_key,
                    product_name,
                    supplier_name,
                    pickup_date,
                    quantity,
                    purchase_price_amount,
                    sale_price_amount,
                    revenue_amount,
                    margin_amount,
                    cost_amount,
                    client_name,
                    period_month,
                    period_year,
                    created_at,
                    updated_at,
                    version
                FROM read_positions 
                WHERE hash_key = :hash_key
            """)

            count_query = text("""
                SELECT 
                    COUNT(DISTINCT deal_id) as count   
                FROM read_positions 
            """)
            
            result = await session.execute(query, {"hash_key": target_hash_key})
            position = result.fetchone()

            count_result = await session.execute(count_query)
            count = count_result.fetchone()
            
            if position:
                logger.success(f"✅ Найдена позиция с hash_key = {target_hash_key}")
                print("\n" + "="*80)
                print("📋 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О ПОЗИЦИИ")
                print("="*80)
                
                # Основная информация
                print(f"🆔 ID позиции:        {position.id}")
                print(f"🆔 ID сделки:         {position.deal_id}")
                print(f"🔑 Ключ сделки:       {position.deal_key}")
                print(f"#️⃣  Номер позиции:     {position.position_number}")
                print(f"🔐 Hash Key:          {position.hash_key}")
                
                print("\n📦 ТОВАРНАЯ ИНФОРМАЦИЯ:")
                print(f"🏷️  Наименование:      {position.product_name}")
                print(f"🏭 Поставщик:         {position.supplier_name or 'Не указан'}")
                print(f"📅 Дата забора:       {position.pickup_date or 'Не указана'}")
                
                print("\n💰 ФИНАНСОВЫЕ ПОКАЗАТЕЛИ:")
                print(f"📊 Количество:        {position.quantity or 'Не указано'}")
                print(f"💵 Цена закупки:      {position.purchase_price_amount or 'Не указана'} ₽")
                print(f"💸 Цена продажи:      {position.sale_price_amount or 'Не указана'} ₽") 
                print(f"💰 Выручка:           {position.revenue_amount or 'Не указана'} ₽")
                print(f"📈 Маржа:             {position.margin_amount or 'Не указана'} ₽")
                print(f"💴 Стоимость:         {position.cost_amount or 'Не указана'} ₽")
                
                print("\n👤 КОНТЕКСТ СДЕЛКИ:")
                print(f"🏢 Клиент:            {position.client_name}")
                print(f"📅 Период:            {position.period_month} {position.period_year}")
                
                print("\n🕒 СИСТЕМНАЯ ИНФОРМАЦИЯ:")
                print(f"📅 Создано:           {position.created_at}")
                print(f"🔄 Обновлено:         {position.updated_at}")
                print(f"🔢 Версия:            {position.version}")
                
                # Вычисляем дополнительные метрики
                if position.revenue_amount and position.cost_amount:
                    margin_percent = ((position.revenue_amount - position.cost_amount) / position.revenue_amount * 100)
                    print(f"\n📊 РАССЧИТАННЫЕ МЕТРИКИ:")
                    print(f"📈 Маржинальность:    {margin_percent:.2f}%")
                
                print("="*80)
                
            else:
                logger.warning(f"❌ Позиция с hash_key = {target_hash_key} не найдена")
                print(f"\n🚫 В таблице read_positions нет записи с hash_key = {target_hash_key}")
                
                # Попробуем найти похожие hash_key для диагностики
                similar_query = text("SELECT hash_key FROM read_positions LIMIT 5")
                similar_result = await session.execute(similar_query)
                similar_hashes = [row.hash_key for row in similar_result.fetchall()]
                
                if similar_hashes:
                    print("\n🔍 Примеры существующих hash_key:")
                    for i, hash_val in enumerate(similar_hashes, 1):
                        print(f"   {i}. {hash_val}")
                else:
                    print("\n📄 Таблица read_positions пуста")
                
                # Проверим общее количество записей
                print(f"\n📊 Всего записей в таблице: {count.count}")
                
    except Exception as e:
        logger.error(f"💥 Ошибка при выполнении запроса: {e}")
        raise


async def main() -> None:
    """Главная функция."""
    logger.info("🚀 Запуск скрипта запроса позиции по hash_key")
    
    try:
        await query_position_by_hash()
        logger.success("✅ Скрипт выполнен успешно")
        
    except Exception as e:
        logger.error(f"💥 Скрипт завершился с ошибкой: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
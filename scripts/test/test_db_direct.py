#!/usr/bin/env python
"""Direct database test to check read models."""

import asyncio

from src.infrastructure.database.connection import get_database_manager, get_database_session
from src.infrastructure.database.repositories import DealRepositoryImplementation


async def test_db_direct():
    print("🔍 Тестирование прямого доступа к базе данных...")
    
    try:
        # Get database session
        async for db in get_database_session():
            repository = DealRepositoryImplementation(db)
            
            print("1️⃣ Проверка количества сделок в БД...")
            result = await repository.find_all_paginated(page=1, limit=10, filters={})
            
            print(f"   Всего сделок: {result.get('total', 0)}")
            print(f"   Получено на странице: {len(result.get('items', []))}")
            
            items = result.get('items', [])
            if items:
                print("2️⃣ Первые сделки:")
                for i, deal in enumerate(items[:3], 1):
                    client_name = getattr(deal, 'client_name', 'N/A')
                    deal_key = getattr(deal, 'deal_key', 'N/A')
                    revenue = getattr(deal, 'total_revenue_amount', 'N/A')
                    print(f"   {i}. {client_name} | {deal_key} | {revenue}")
                    
                # Check if mock data
                first_deal = items[0]
                client_name = getattr(first_deal, 'client_name', '')
                if "ООО Компания" in client_name:
                    print("   ⚠️  ОБНАРУЖЕНЫ MOCK ДАННЫЕ!")
                else:
                    print("   ✅ РЕАЛЬНЫЕ ДАННЫЕ!")
            else:
                print("   📭 Сделок не найдено")
                
            break  # Exit after first iteration
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_db_direct())

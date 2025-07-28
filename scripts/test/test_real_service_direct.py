#!/usr/bin/env python
"""Direct test of RealDealService."""

import asyncio

from src.infrastructure.database.connection import get_database_session
from src.infrastructure.database.repositories import DealRepositoryImplementation
from src.presentation.api.services.real_deal_service import RealDealService


async def test_real_service_direct():
    print("🔧 Тестирование RealDealService напрямую...")
    
    try:
        # Get database session
        async for db in get_database_session():
            # Create repository and service
            repository = DealRepositoryImplementation(db)
            service = RealDealService(repository)
            
            print("1️⃣ Тестирование get_deals_paginated...")
            result = await service.get_deals_paginated(page=1, limit=5, filters={})
            
            print(f"   Total: {result.get('total', 0)}")
            print(f"   Items: {len(result.get('items', []))}")
            print(f"   Pages: {result.get('pages', 0)}")
            
            items = result.get('items', [])
            if items:
                print("2️⃣ Первые сделки:")
                for i, deal in enumerate(items[:3], 1):
                    client_name = deal.get('client_name', 'N/A')
                    invoice_number = deal.get('invoice_number', 'N/A')
                    revenue = deal.get('revenue', 'N/A')
                    print(f"   {i}. {client_name} | {invoice_number} | {revenue}")
                    
                # Check data source
                first_deal = items[0]
                client_name = first_deal.get('client_name', '')
                if "ООО Компания" in client_name:
                    print("   ⚠️  ОБНАРУЖЕНЫ MOCK ДАННЫЕ!")
                elif "DEAL" in client_name:
                    print("   📊 ДАННЫЕ ИЗ READ MODELS (возможно неполные)")
                else:
                    print("   ✅ РЕАЛЬНЫЕ ДАННЫЕ!")
            else:
                print("   📭 Сделок не найдено")
                
            break
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_real_service_direct())

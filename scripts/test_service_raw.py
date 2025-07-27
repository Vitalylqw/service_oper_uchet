#!/usr/bin/env python
"""Test service directly to see raw data."""

import asyncio
from src.infrastructure.database.connection import get_database_session
from src.infrastructure.database.repositories import DealRepositoryImplementation
from src.presentation.api.services.real_deal_service import RealDealService

async def test_raw_service():
    print("🔧 Тестирование raw service...")
    
    try:
        # Get database session
        async for db in get_database_session():
            # Create repository and service
            repository = DealRepositoryImplementation(db)
            service = RealDealService(repository)
            
            print("1️⃣ Тестирование get_deals_paginated...")
            result = await service.get_deals_paginated(page=1, limit=3, filters={})
            
            print(f"   Total: {result.get('total', 0)}")
            print(f"   Items: {len(result.get('items', []))}")
            
            items = result.get('items', [])
            if items:
                print("2️⃣ Анализ первой сделки:")
                first_deal = items[0]
                for key, value in first_deal.items():
                    value_type = type(value).__name__
                    print(f"   {key}: {repr(value)} ({value_type})")
                    
                # Check problematic fields
                print("\n3️⃣ Проблемные поля:")
                invoice_date = first_deal.get('invoice_date')
                updated_at = first_deal.get('updated_at')
                revenue = first_deal.get('revenue')
                margin = first_deal.get('margin')
                
                print(f"   invoice_date: {repr(invoice_date)} - type: {type(invoice_date)}")
                print(f"   updated_at: {repr(updated_at)} - type: {type(updated_at)}")
                print(f"   revenue: {repr(revenue)} - type: {type(revenue)}")
                print(f"   margin: {repr(margin)} - type: {type(margin)}")
                
            break
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_raw_service()) 
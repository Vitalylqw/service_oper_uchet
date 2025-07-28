#!/usr/bin/env python
"""Quick API test to check if real data is returned."""

import asyncio
import json

import httpx


async def test_api():
    base_url = "http://localhost:8000"
    
    print("🔧 Тестирование API...")
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            # 1. Check health
            print("1️⃣ Проверка health endpoint...")
            health_response = await client.get(f"{base_url}/health")
            print(f"   Status: {health_response.status_code}")
            
            # 2. Login
            print("2️⃣ Логин как viewer...")
            login_data = {"username": "viewer", "password": "password"}
            login_response = await client.post(f"{base_url}/auth/login", json=login_data)
            
            if login_response.status_code == 200:
                token_data = login_response.json()
                token = token_data.get("access_token")
                print(f"   Token получен: {token[:20]}...")
                
                # 3. Get deals with auth
                print("3️⃣ Получение сделок...")
                headers = {"Authorization": f"Bearer {token}"}
                deals_response = await client.get(f"{base_url}/api/v1/deals/", headers=headers)
                
                if deals_response.status_code == 200:
                    deals_data = deals_response.json()
                    print(f"   Status: {deals_response.status_code}")
                    print(f"   Количество сделок: {deals_data.get('total', 0)}")
                    
                    # Check if this is mock data
                    items = deals_data.get('items', [])
                    if items:
                        first_deal = items[0]
                        client_name = first_deal.get('client_name', '')
                        deal_key = first_deal.get('deal_key', '')
                        
                        print("   Первая сделка:")
                        print(f"     - Клиент: {client_name}")
                        print(f"     - Deal Key: {deal_key}")
                        
                        # Check if it's mock data (mock has "ООО Компания 1")
                        if "ООО Компания" in client_name:
                            print("   ⚠️  ОБНАРУЖЕНЫ MOCK ДАННЫЕ!")
                        else:
                            print("   ✅ РЕАЛЬНЫЕ ДАННЫЕ!")
                    else:
                        print("   📭 Нет сделок в ответе")
                else:
                    print(f"   ❌ Ошибка получения сделок: {deals_response.status_code}")
            else:
                print(f"   ❌ Ошибка авторизации: {login_response.status_code}")
                
    except Exception as e:
        print(f"❌ Ошибка подключения к API: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())

#!/usr/bin/env python
"""Detailed API test with error handling."""

import asyncio
import httpx
import json

async def test_detailed():
    base_url = "http://localhost:8000"
    
    print("🔧 Детальное тестирование API...")
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            # 1. Health check
            print("1️⃣ Health check...")
            try:
                health_response = await client.get(f"{base_url}/health")
                print(f"   Status: {health_response.status_code}")
                if health_response.status_code == 200:
                    print(f"   Response: {health_response.json()}")
            except Exception as e:
                print(f"   ❌ Health error: {e}")
                
            # 2. Login
            print("\n2️⃣ Авторизация...")
            try:
                login_data = {"username": "viewer", "password": "password"}
                login_response = await client.post(f"{base_url}/auth/login", json=login_data)
                print(f"   Status: {login_response.status_code}")
                
                if login_response.status_code == 200:
                    token_data = login_response.json()
                    token = token_data.get("access_token")
                    print(f"   ✅ Token получен")
                    
                    # 3. Test protected endpoint
                    print("\n3️⃣ Тест защищенного эндпоинта...")
                    headers = {"Authorization": f"Bearer {token}"}
                    
                    try:
                        deals_response = await client.get(f"{base_url}/api/v1/deals/", headers=headers)
                        print(f"   Status: {deals_response.status_code}")
                        
                        if deals_response.status_code == 200:
                            deals_data = deals_response.json()
                            print(f"   ✅ Успешный ответ!")
                            print(f"   Количество сделок: {deals_data.get('total', 0)}")
                            
                            # Check data type
                            items = deals_data.get('items', [])
                            if items:
                                first_deal = items[0]
                                client_name = first_deal.get('client_name', '')
                                print(f"   Первая сделка: {client_name}")
                                
                                if "ООО Компания" in client_name:
                                    print("   ⚠️  ОБНАРУЖЕНЫ MOCK ДАННЫЕ!")
                                else:
                                    print("   ✅ РЕАЛЬНЫЕ ДАННЫЕ!")
                            else:
                                print("   📭 Сделок не найдено")
                                
                        else:
                            # Get error details
                            try:
                                error_data = deals_response.json()
                                print(f"   ❌ Ошибка: {error_data}")
                            except:
                                print(f"   ❌ Ошибка: {deals_response.text}")
                                
                    except Exception as e:
                        print(f"   ❌ Exception при запросе deals: {e}")
                        
                else:
                    print(f"   ❌ Ошибка авторизации: {login_response.text}")
                    
            except Exception as e:
                print(f"   ❌ Login exception: {e}")
                
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(test_detailed()) 
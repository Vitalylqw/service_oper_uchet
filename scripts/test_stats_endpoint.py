#!/usr/bin/env python
"""Test stats endpoint specifically."""

import asyncio
import httpx

async def test_stats():
    base_url = "http://localhost:8000"
    
    print("🔧 Тестирование stats endpoint...")
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            # 1. Test new code endpoint
            print("1️⃣ Тест нового кода...")
            try:
                test_response = await client.get(f"{base_url}/api/v1/deals/test-new-code")
                print(f"   Status: {test_response.status_code}")
                if test_response.status_code == 200:
                    print(f"   Response: {test_response.json()}")
            except Exception as e:
                print(f"   ❌ Test error: {e}")

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
                    
                    # 3. Test stats endpoint
                    print("\n3️⃣ Тест stats endpoint...")
                    headers = {"Authorization": f"Bearer {token}"}
                    
                    try:
                        stats_response = await client.get(f"{base_url}/api/v1/deals/stats", headers=headers)
                        print(f"   Status: {stats_response.status_code}")
                        
                        if stats_response.status_code == 200:
                            stats_data = stats_response.json()
                            print(f"   ✅ Stats успешно получены!")
                            print(f"   Total deals: {stats_data.get('total_deals', 0)}")
                            print(f"   Total revenue: {stats_data.get('total_revenue', 0)}")
                        else:
                            try:
                                error_data = stats_response.json()
                                print(f"   ❌ Stats ошибка: {error_data}")
                            except:
                                print(f"   ❌ Stats ошибка: {stats_response.text}")
                                
                    except Exception as e:
                        print(f"   ❌ Exception при запросе stats: {e}")
                        
                    # 4. Test deals endpoint
                    print("\n4️⃣ Тест deals endpoint...")
                    try:
                        deals_response = await client.get(f"{base_url}/api/v1/deals/?page=1&limit=5", headers=headers)
                        print(f"   Status: {deals_response.status_code}")
                        
                        if deals_response.status_code == 200:
                            deals_data = deals_response.json()
                            print(f"   ✅ Deals успешно получены!")
                            print(f"   Total deals: {deals_data.get('total', 0)}")
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
                            try:
                                error_data = deals_response.json()
                                print(f"   ❌ Deals ошибка: {error_data}")
                            except:
                                print(f"   ❌ Deals ошибка: {deals_response.text}")
                                
                    except Exception as e:
                        print(f"   ❌ Exception при запросе deals: {e}")
                        
                else:
                    print(f"   ❌ Ошибка авторизации: {login_response.text}")
                    
            except Exception as e:
                print(f"   ❌ Login exception: {e}")
                
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(test_stats()) 
#!/usr/bin/env python
"""Check available endpoints via OpenAPI spec."""

import asyncio
import httpx
import json

async def check_swagger():
    base_url = "http://localhost:8000"
    
    print("🔍 Проверка доступных эндпоинтов...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Get OpenAPI spec
            print("1️⃣ Получение OpenAPI спецификации...")
            openapi_response = await client.get(f"{base_url}/openapi.json")
            
            if openapi_response.status_code == 200:
                openapi_data = openapi_response.json()
                paths = openapi_data.get("paths", {})
                
                print(f"   ✅ Найдено {len(paths)} эндпоинтов:")
                for path, methods in paths.items():
                    method_list = list(methods.keys())
                    print(f"     {path} [{', '.join(method_list).upper()}]")
                    
            else:
                print(f"   ❌ Ошибка получения OpenAPI: {openapi_response.status_code}")
                
            # Also check main page
            print("\n2️⃣ Проверка главной страницы...")
            root_response = await client.get(f"{base_url}/")
            if root_response.status_code == 200:
                print(f"   ✅ Корневой endpoint доступен: {root_response.json()}")
            else:
                print(f"   ❌ Корневой endpoint недоступен: {root_response.status_code}")
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(check_swagger()) 
#!/usr/bin/env python3
"""
Quick API testing script.
"""

import asyncio
import sys
import httpx
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loguru import logger


async def test_health_endpoint():
    """Test health endpoint."""
    
    try:
        logger.info("🔧 Тестирование API...")
        logger.info("1️⃣ Проверка health endpoint...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health/", timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                logger.info("✅ Health endpoint работает")
                logger.info(f"📊 Статус: {health_data.get('status', 'unknown')}")
                logger.info(f"📊 Версия: {health_data.get('version', 'unknown')}")
                return True
            else:
                logger.error(f"❌ Health endpoint вернул статус {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к API: {e}")
        return False


async def test_auth_endpoint():
    """Test authentication endpoint."""
    
    try:
        logger.info("2️⃣ Проверка аутентификации...")
        
        async with httpx.AsyncClient() as client:
            # Test login with test credentials
            login_data = {"username": "viewer", "password": "password"}
            response = await client.post("http://localhost:8000/auth/login", json=login_data, timeout=10)
            
            if response.status_code == 200:
                tokens = response.json()
                access_token = tokens.get("access_token")
                if access_token:
                    logger.info("✅ Аутентификация работает")
                    logger.info(f"📊 Получен токен доступа")
                    return access_token
                else:
                    logger.error("❌ Токен доступа не найден в ответе")
                    return None
            else:
                logger.error(f"❌ Аутентификация не удалась: {response.status_code}")
                return None
                
    except Exception as e:
        logger.error(f"❌ Ошибка аутентификации: {e}")
        return None


async def test_deals_endpoint(access_token):
    """Test deals endpoint."""
    
    try:
        logger.info("3️⃣ Проверка deals endpoint...")
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get("http://localhost:8000/api/v1/deals/", headers=headers, timeout=10)
            
            if response.status_code == 200:
                deals_data = response.json()
                items = deals_data.get("items", [])
                logger.info("✅ Deals endpoint работает")
                logger.info(f"📊 Получено сделок: {len(items)}")
                
                if items:
                    logger.info("📋 Примеры сделок:")
                    for i, deal in enumerate(items[:3]):
                        logger.info(f"  {i+1}. {deal.get('client_name', 'N/A')} - {deal.get('invoice_number', 'N/A')}")
                
                return True
            else:
                logger.error(f"❌ Deals endpoint вернул статус {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Ошибка deals endpoint: {e}")
        return False


async def test_sessions_endpoint(access_token):
    """Test sessions endpoint."""
    
    try:
        logger.info("4️⃣ Проверка sessions endpoint...")
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get("http://localhost:8000/api/v1/sessions/", headers=headers, timeout=10)
            
            if response.status_code == 200:
                sessions_data = response.json()
                items = sessions_data.get("items", [])
                logger.info("✅ Sessions endpoint работает")
                logger.info(f"📊 Получено сессий: {len(items)}")
                
                if items:
                    logger.info("📋 Примеры сессий:")
                    for i, session in enumerate(items[:3]):
                        logger.info(f"  {i+1}. {session.get('status', 'N/A')} - {session.get('created_at', 'N/A')}")
                
                return True
            else:
                logger.error(f"❌ Sessions endpoint вернул статус {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Ошибка sessions endpoint: {e}")
        return False


async def main():
    """Main test function."""
    
    # Test 1: Health endpoint
    health_ok = await test_health_endpoint()
    if not health_ok:
        logger.error("💥 API сервер недоступен!")
        return 1
    
    # Test 2: Authentication
    access_token = await test_auth_endpoint()
    if not access_token:
        logger.error("💥 Аутентификация не работает!")
        return 1
    
    # Test 3: Deals endpoint
    deals_ok = await test_deals_endpoint(access_token)
    
    # Test 4: Sessions endpoint
    sessions_ok = await test_sessions_endpoint(access_token)
    
    if deals_ok and sessions_ok:
        logger.info("🎉 Все API тесты прошли успешно!")
        logger.info("📋 API Summary:")
        logger.info("  ✅ Health endpoint работает")
        logger.info("  ✅ Аутентификация работает")
        logger.info("  ✅ Deals endpoint работает")
        logger.info("  ✅ Sessions endpoint работает")
    else:
        logger.error("💥 Некоторые API тесты не прошли!")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 
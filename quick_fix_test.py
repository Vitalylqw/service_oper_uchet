#!/usr/bin/env python3
"""Quick test to check if API is working after fixes."""

import requests
import time

def test_api_health():
    """Test if API is responding."""
    try:
        print("🔍 Проверяю health endpoint...")
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint работает")
            return True
        else:
            print(f"❌ Health endpoint: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка health: {e}")
        return False

def test_auth():
    """Test authentication."""
    try:
        print("🔍 Проверяю авторизацию...")
        login_data = {"username": "viewer", "password": "password"}
        response = requests.post("http://localhost:8000/auth/login", json=login_data, timeout=5)
        if response.status_code == 200:
            print("✅ Авторизация работает")
            return response.json().get("access_token")
        else:
            print(f"❌ Авторизация: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Ошибка авторизации: {e}")
        return None

def test_deals_endpoint(token):
    """Test deals endpoint."""
    try:
        print("🔍 Проверяю /api/v1/deals/ endpoint...")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get("http://localhost:8000/api/v1/deals/", headers=headers, timeout=10)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Deals endpoint работает! Найдено сделок: {data.get('total', 0)}")
            
            # Check if we have items and period fields
            items = data.get('items', [])
            if items:
                first_item = items[0]
                period_fields = ['period_month', 'period_year', 'period_full_name']
                print("\n📊 Проверка полей периода в первой сделке:")
                for field in period_fields:
                    value = first_item.get(field, 'ОТСУТСТВУЕТ')
                    print(f"   {field}: {value}")
            
            return True
        else:
            print(f"❌ Deals endpoint: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
    except Exception as e:
        print(f"❌ Ошибка deals endpoint: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🛠️ БЫСТРЫЙ ТЕСТ ИСПРАВЛЕНИЙ")
    print("=" * 50)
    
    # Wait a bit for server to start
    print("⏳ Жду 3 секунды для запуска сервера...")
    time.sleep(3)
    
    # Test sequence
    health_ok = test_api_health()
    if not health_ok:
        print("\n❌ API сервер не отвечает. Проверьте запуск.")
        exit(1)
    
    token = test_auth()
    if not token:
        print("\n❌ Проблемы с авторизацией.")
        exit(1)
    
    deals_ok = test_deals_endpoint(token)
    
    print("\n" + "=" * 50)
    if health_ok and token and deals_ok:
        print("🎉 ВСЕ РАБОТАЕТ! API исправлен.")
        print("✅ Можно проверять UI на http://localhost:3000/deals")
    else:
        print("❌ Еще есть проблемы, требуется дополнительная диагностика.")
    print("=" * 50)
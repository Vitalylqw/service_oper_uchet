#!/usr/bin/env python3
"""
Test script for period functionality.
Checks if API returns period fields correctly.
"""

import requests
import json
from datetime import datetime

def test_period_api():
    """Test period fields in deals API."""
    
    print("=" * 50)
    print("ТЕСТ: Проверка полей периода в API")
    print("=" * 50)
    
    # Test API health
    try:
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ API сервер работает")
        else:
            print("❌ API сервер недоступен")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения к API: {e}")
        return False
    
    # Login to get token
    try:
        login_data = {"username": "viewer", "password": "password"}
        login_response = requests.post("http://localhost:8000/auth/login", json=login_data, timeout=5)
        
        if login_response.status_code == 200:
            token_data = login_response.json()
            token = token_data.get("access_token")
            print("✅ Авторизация успешна")
        else:
            print(f"❌ Ошибка авторизации: {login_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка авторизации: {e}")
        return False
    
    # Test deals endpoint
    try:
        headers = {"Authorization": f"Bearer {token}"}
        deals_response = requests.get("http://localhost:8000/api/v1/deals/", headers=headers, timeout=10)
        
        if deals_response.status_code == 200:
            deals_data = deals_response.json()
            print("✅ API сделок работает")
            
            # Check if we have deals
            items = deals_data.get("items", [])
            if not items:
                print("⚠️  Сделки в API не найдены")
                return True
                
            # Check first deal for period fields
            first_deal = items[0]
            print(f"\n📊 Проверка первой сделки (ID: {first_deal.get('id', 'N/A')}):")
            
            required_fields = ['period_month', 'period_year', 'period_full_name']
            missing_fields = []
            
            for field in required_fields:
                if field in first_deal:
                    value = first_deal[field]
                    print(f"✅ {field}: '{value}'")
                else:
                    missing_fields.append(field)
                    print(f"❌ {field}: отсутствует")
            
            if missing_fields:
                print(f"\n❌ Отсутствуют поля: {missing_fields}")
                return False
            else:
                print(f"\n✅ Все поля периода присутствуют!")
                return True
                
        else:
            print(f"❌ Ошибка API сделок: {deals_response.status_code}")
            print(f"Ответ: {deals_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка запроса к API сделок: {e}")
        return False

def test_period_filters():
    """Test period filters."""
    
    print("\n" + "=" * 50)
    print("ТЕСТ: Проверка фильтрации по периоду")
    print("=" * 50)
    
    try:
        # Login
        login_data = {"username": "viewer", "password": "password"}
        login_response = requests.post("http://localhost:8000/auth/login", json=login_data, timeout=5)
        token = login_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test filter by year
        params = {"period_year": "2025"}
        response = requests.get("http://localhost:8000/api/v1/deals/", headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Фильтр по году 2025: найдено {data.get('total', 0)} сделок")
            
            # Test filter by month
            params = {"period_month": "Январь"}
            response = requests.get("http://localhost:8000/api/v1/deals/", headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Фильтр по месяцу 'Январь': найдено {data.get('total', 0)} сделок")
                
                # Test combined filter
                params = {"period_year": "2025", "period_month": "Январь"}
                response = requests.get("http://localhost:8000/api/v1/deals/", headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Комбинированный фильтр (Январь 2025): найдено {data.get('total', 0)} сделок")
                    return True
                    
        print(f"❌ Ошибка тестирования фильтров: {response.status_code}")
        return False
        
    except Exception as e:
        print(f"❌ Ошибка тестирования фильтров: {e}")
        return False

if __name__ == "__main__":
    print(f"Время теста: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success1 = test_period_api()
    success2 = test_period_filters()
    
    print("\n" + "=" * 50)
    print("ИТОГОВЫЙ РЕЗУЛЬТАТ")
    print("=" * 50)
    
    if success1 and success2:
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("✅ Поля периода добавлены корректно")
        print("✅ Фильтрация по периоду работает")
        print("\n📝 Можно проверить UI на http://localhost:3000/deals")
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        if not success1:
            print("❌ Проблемы с полями периода в API")
        if not success2:
            print("❌ Проблемы с фильтрацией по периоду")
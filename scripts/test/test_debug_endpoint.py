#!/usr/bin/env python3
import json
import sys
import time

import requests

print("🔍 DEBUG: Testing /api/v1/sessions/stats endpoint with detailed logging...")
print("=" * 60)

# Подождем для запуска сервера
time.sleep(5)

try:
    # Тест 1: Проверим что сервер запущен
    print("🔧 Step 1: Checking if server is running...")
    try:
        health_response = requests.get("http://localhost:8000/health/", timeout=5)
        print(f"   Health check: {health_response.status_code}")
        if health_response.status_code == 200:
            print("   ✅ Server is running")
        else:
            print(f"   ❌ Server responded with {health_response.status_code}")
    except Exception as e:
        print(f"   ❌ Server not responding: {e}")
        sys.exit(1)

    # Тест 2: Попробуем без авторизации
    print("\n🔧 Step 2: Testing /stats without auth...")
    try:
        no_auth_response = requests.get("http://localhost:8000/api/v1/sessions/stats", timeout=5)
        print(f"   Status: {no_auth_response.status_code}")
        print(f"   Response: {no_auth_response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ Request failed: {e}")

    # Тест 3: Логин
    print("\n🔧 Step 3: Login...")
    try:
        login_response = requests.post(
            "http://localhost:8000/auth/login",
            json={"username": "viewer", "password": "password"},
            timeout=10
        )
        print(f"   Status: {login_response.status_code}")
        
        if login_response.status_code == 200:
            token_data = login_response.json()
            access_token = token_data["access_token"]
            print("   ✅ Login successful")
            print(f"   Token: {access_token[:50]}...")
        else:
            print(f"   ❌ Login failed: {login_response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"   ❌ Login request failed: {e}")
        sys.exit(1)

    # Тест 4: Тестируем /stats с авторизацией
    print("\n🔧 Step 4: Testing /stats WITH auth...")
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        stats_response = requests.get(
            "http://localhost:8000/api/v1/sessions/stats",
            headers=headers,
            timeout=10
        )
        
        print(f"   Status: {stats_response.status_code}")
        print(f"   Headers: {dict(stats_response.headers)}")
        
        if stats_response.status_code == 200:
            stats_data = stats_response.json()
            print("   ✅ SUCCESS! /stats endpoint works!")
            print("   📊 Response data:")
            print(json.dumps(stats_data, indent=4, default=str))
        else:
            print(f"   ❌ FAILED! Status: {stats_response.status_code}")
            print(f"   📝 Response body: {stats_response.text}")
            print(f"   📝 Response headers: {dict(stats_response.headers)}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {e}")

    # Тест 5: Проверим что другие endpoints работают
    print("\n🔧 Step 5: Testing other endpoints for comparison...")
    try:
        deals_response = requests.get(
            "http://localhost:8000/api/v1/deals/",
            headers=headers,
            timeout=10
        )
        print(f"   /deals status: {deals_response.status_code}")
        
        sessions_response = requests.get(
            "http://localhost:8000/api/v1/sessions/",
            headers=headers,
            timeout=10
        )
        print(f"   /sessions status: {sessions_response.status_code}")
        
    except Exception as e:
        print(f"   ❌ Other endpoints test failed: {e}")

    print("\n" + "=" * 60)
    print("🔍 DEBUG TEST COMPLETED")
        
except KeyboardInterrupt:
    print("\n🛑 Test interrupted by user")
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()

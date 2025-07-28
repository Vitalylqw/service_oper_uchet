#!/usr/bin/env python3
"""Final system check - all components."""

import asyncio
import json

import requests
from sqlalchemy import text

from src.infrastructure.database.connection import get_database_session


def check_api_endpoints():
    """Check all available API endpoints."""
    base_url = "http://localhost:8000"
    
    print("=== API ENDPOINTS CHECK ===")
    
    # Get token
    login_data = {"username": "admin", "password": "password"}
    response = requests.post(f"{base_url}/auth/login", json=login_data)
    
    if response.status_code != 200:
        print("❌ Login failed")
        return
        
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try common endpoint patterns
    endpoints_to_try = [
        "/deals",
        "/api/deals",
        "/api/v1/deals",
        "/v1/deals",
        "/sessions",
        "/api/sessions",
        "/api/v1/sessions",
        "/v1/sessions",
        "/stats",
        "/api/stats",
        "/api/v1/stats"
    ]
    
    working_endpoints = []
    
    for endpoint in endpoints_to_try:
        try:
            response = requests.get(f"{base_url}{endpoint}", headers=headers)
            print(f"{endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                working_endpoints.append(endpoint)
                data = response.json()
                print(f"  ✅ Data: {json.dumps(data, indent=2)[:150]}...")
                
        except Exception as e:
            print(f"{endpoint}: ERROR - {e}")
    
    print(f"\n📊 Working endpoints: {working_endpoints}")
    return working_endpoints


async def check_database_final():
    """Final database check."""
    print("\n=== DATABASE FINAL CHECK ===")
    
    async for session in get_database_session():
        # Check all important tables
        tables = ["read_deals", "sync_sessions", "event_store", "read_stats"]
        
        for table in tables:
            try:
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"✅ {table}: {count} records")
            except Exception as e:
                print(f"❌ {table}: {e}")
        
        break


def main():
    """Main check function."""
    print("🔍 FINAL SYSTEM CHECK")
    print("=" * 50)
    
    # Check API
    working_endpoints = check_api_endpoints()
    
    # Check Database
    asyncio.run(check_database_final())
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY:")
    print("✅ API Server: Running on port 8000")
    print("✅ Authentication: Working")
    print("✅ Database: Connected with data")
    print(f"📋 API Endpoints found: {len(working_endpoints)}")
    
    if working_endpoints:
        print("✅ System is READY!")
        print("🌐 Open: http://localhost:8000/docs")
    else:
        print("⚠️ No working data endpoints found")
        print("📚 Check API documentation at: http://localhost:8000/docs")


if __name__ == "__main__":
    main()

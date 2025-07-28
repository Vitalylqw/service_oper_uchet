#!/usr/bin/env python3
"""Debug API deals endpoint in detail."""

import json

import requests


def debug_api_deals():
    """Debug deals API endpoint."""
    base_url = "http://localhost:8000"
    
    print("=== DEBUGGING API DEALS ===")
    
    # Login
    login_data = {"username": "admin", "password": "password"}
    response = requests.post(f"{base_url}/auth/login", json=login_data)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
        
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login successful")
    
    # Test deals endpoint with different parameters
    test_cases = [
        {"url": "/api/v1/deals", "params": {}},
        {"url": "/api/v1/deals", "params": {"page": 1, "limit": 10}},
        {"url": "/api/v1/deals", "params": {"page": 1, "limit": 50}},
        {"url": "/api/v1/deals", "params": {"page": 1, "limit": 100}},
        {"url": "/api/v1/deals", "params": {"client_name": "ЛЕНТЕХСТРОЙ"}},
        {"url": "/api/v1/deals", "params": {"period_month": "Май"}},
        {"url": "/api/v1/deals", "params": {"period_year": "2025"}},
    ]
    
    for test_case in test_cases:
        url = test_case["url"]
        params = test_case["params"]
        
        try:
            response = requests.get(f"{base_url}{url}", headers=headers, params=params)
            print(f"\n📋 Test: {url} with params {params}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Total: {data.get('total', 'N/A')}")
                print(f"Items count: {len(data.get('items', []))}")
                print(f"Page: {data.get('page', 'N/A')}")
                print(f"Limit: {data.get('limit', 'N/A')}")
                print(f"Pages: {data.get('pages', 'N/A')}")
                
                # Show first item if exists
                items = data.get('items', [])
                if items:
                    first_item = items[0]
                    print(f"First item client: {first_item.get('client_name', 'N/A')}")
                    print(f"First item ID: {first_item.get('id', 'N/A')}")
                else:
                    print("No items returned")
            else:
                print(f"Error: {response.text[:200]}")
                
        except Exception as e:
            print(f"Request failed: {e}")
    
    # Test individual deal by ID if we can find one
    print("\n🔍 Testing individual deal access...")
    try:
        # First get any deal ID from database check
        response = requests.get(f"{base_url}/api/v1/deals", headers=headers, params={"limit": 1})
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            if items:
                deal_id = items[0].get('id')
                if deal_id:
                    individual_response = requests.get(f"{base_url}/api/v1/deals/{deal_id}", headers=headers)
                    print(f"Individual deal access: {individual_response.status_code}")
                    if individual_response.status_code == 200:
                        deal_data = individual_response.json()
                        print(f"Individual deal client: {deal_data.get('client_name', 'N/A')}")
    except Exception as e:
        print(f"Individual deal test failed: {e}")


if __name__ == "__main__":
    debug_api_deals()

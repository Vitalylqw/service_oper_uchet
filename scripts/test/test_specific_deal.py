#!/usr/bin/env python3
"""
Test specific deal endpoint with detailed diagnostics.
"""

import json
import sys
from datetime import datetime

import requests


def test_specific_deal():
    """Test specific deal endpoint with detailed diagnostics."""
    
    # Configuration
    base_url = "http://127.0.0.1:8000"
    deal_id = "fde6e5fb-9076-4198-93c1-3127b688323b"
    
    print(f"🔍 Testing deal endpoint: {base_url}/api/v1/deals/{deal_id}")
    print(f"⏰ Time: {datetime.now()}")
    print("-" * 80)
    
    # Step 1: Check if API server is running
    print("1. Checking API server health...")
    try:
        health_response = requests.get(f"{base_url}/health", timeout=5)
        print(f"   Health status: {health_response.status_code}")
        if health_response.status_code == 200:
            print("   ✅ API server is running")
        else:
            print(f"   ⚠️  API server returned: {health_response.text}")
    except Exception as e:
        print(f"   ❌ Cannot connect to API server: {e}")
        return False
    
    # Step 2: Authenticate
    print("\n2. Authenticating...")
    try:
        auth_response = requests.post(
            f"{base_url}/auth/login",
            json={"username": "viewer", "password": "password"},
            timeout=10
        )
        
        if auth_response.status_code == 200:
            tokens = auth_response.json()
            access_token = tokens["access_token"]
            print("   ✅ Authentication successful")
            print(f"   Token expires in: {tokens.get('expires_in', 'unknown')} seconds")
        else:
            print(f"   ❌ Authentication failed: {auth_response.status_code}")
            print(f"   Response: {auth_response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Authentication error: {e}")
        return False
    
    # Step 3: Test deals list endpoint first
    print("\n3. Testing deals list endpoint...")
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        deals_response = requests.get(
            f"{base_url}/api/v1/deals/",
            headers=headers,
            params={"limit": 5},
            timeout=10
        )
        
        print(f"   Deals list status: {deals_response.status_code}")
        
        if deals_response.status_code == 200:
            deals_data = deals_response.json()
            print(f"   Total deals: {deals_data.get('total', 0)}")
            print(f"   Items returned: {len(deals_data.get('items', []))}")
            
            # Show available deal IDs
            items = deals_data.get('items', [])
            if items:
                print("   Available deal IDs:")
                for i, item in enumerate(items[:3]):  # Show first 3
                    print(f"     {i+1}. {item.get('id', 'N/A')} - {item.get('client_name', 'N/A')}")
        else:
            print(f"   ❌ Deals list failed: {deals_response.text}")
            
    except Exception as e:
        print(f"   ❌ Deals list error: {e}")
    
    # Step 4: Test specific deal endpoint
    print(f"\n4. Testing specific deal: {deal_id}")
    
    try:
        deal_response = requests.get(
            f"{base_url}/api/v1/deals/{deal_id}",
            headers=headers,
            timeout=10
        )
        
        print(f"   Status: {deal_response.status_code}")
        
        if deal_response.status_code == 200:
            deal_data = deal_response.json()
            print("   ✅ Deal found successfully!")
            print(f"   Client: {deal_data.get('client_name', 'N/A')}")
            print(f"   Invoice: {deal_data.get('invoice_number', 'N/A')}")
            print(f"   Revenue: {deal_data.get('revenue', 'N/A')}")
            print(f"   Items count: {deal_data.get('items_count', 'N/A')}")
            
        elif deal_response.status_code == 404:
            print("   ❌ Deal not found (404)")
            print("   This means the deal ID doesn't exist in the database")
            
        elif deal_response.status_code == 500:
            print("   ❌ Internal Server Error (500)")
            print("   This indicates a server-side error")
            print(f"   Response: {deal_response.text}")
            
        else:
            print(f"   ❌ Unexpected status: {deal_response.status_code}")
            print(f"   Response: {deal_response.text}")
            
    except Exception as e:
        print(f"   ❌ Request error: {e}")
    
    # Step 5: Test with a known valid UUID format
    print("\n5. Testing with a different UUID format...")
    
    # Try with a different UUID that might exist
    try:
        # First get a valid UUID from the deals list
        if 'items' in locals() and items:
            valid_deal_id = items[0].get('id')
            if valid_deal_id:
                print(f"   Testing with valid UUID: {valid_deal_id}")
                
                valid_deal_response = requests.get(
                    f"{base_url}/api/v1/deals/{valid_deal_id}",
                    headers=headers,
                    timeout=10
                )
                
                print(f"   Status: {valid_deal_response.status_code}")
                
                if valid_deal_response.status_code == 200:
                    print("   ✅ Valid UUID works correctly")
                else:
                    print(f"   ❌ Even valid UUID failed: {valid_deal_response.text}")
        
    except Exception as e:
        print(f"   ❌ Valid UUID test error: {e}")
    
    print("\n" + "=" * 80)
    print("🏁 Test completed")
    
    return True


if __name__ == "__main__":
    success = test_specific_deal()
    sys.exit(0 if success else 1)

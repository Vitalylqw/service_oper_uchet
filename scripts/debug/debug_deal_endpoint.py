#!/usr/bin/env python3
"""
Debug deal endpoint with detailed error reporting.
"""

import json
import sys

import requests


def debug_deal_endpoint():
    """Debug deal endpoint with detailed error reporting."""
    
    # Configuration
    base_url = "http://127.0.0.1:8000"
    deal_id = "fde6e5fb-9076-4198-93c1-3127b688323b"
    
    print(f"🔍 Debugging deal endpoint: {base_url}/api/v1/deals/{deal_id}")
    print("-" * 80)
    
    # Step 1: Authenticate
    print("1. Authenticating...")
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
        else:
            print(f"   ❌ Authentication failed: {auth_response.status_code}")
            print(f"   Response: {auth_response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Authentication error: {e}")
        return False
    
    # Step 2: Test specific deal endpoint with detailed error reporting
    print(f"\n2. Testing specific deal: {deal_id}")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        deal_response = requests.get(
            f"{base_url}/api/v1/deals/{deal_id}",
            headers=headers,
            timeout=30  # Longer timeout for debugging
        )
        
        print(f"   Status: {deal_response.status_code}")
        print(f"   Headers: {dict(deal_response.headers)}")
        
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
            print("   Full response text:")
            print("   " + "="*60)
            print(f"   {deal_response.text}")
            print("   " + "="*60)
            
            # Try to parse JSON error if possible
            try:
                error_data = deal_response.json()
                print("   Parsed error data:")
                print(f"   {json.dumps(error_data, indent=2)}")
            except:
                print("   Could not parse error as JSON")
            
        else:
            print(f"   ❌ Unexpected status: {deal_response.status_code}")
            print(f"   Response: {deal_response.text}")
            
    except requests.exceptions.Timeout:
        print("   ❌ Request timed out")
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection error - server may be down")
    except Exception as e:
        print(f"   ❌ Request error: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
    
    print("\n" + "=" * 80)
    print("🏁 Debug completed")
    
    return True


if __name__ == "__main__":
    success = debug_deal_endpoint()
    sys.exit(0 if success else 1)

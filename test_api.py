import requests
import json

# Test API endpoint with authentication
base_url = "http://localhost:8001"

# First get token
login_data = {
    "username": "viewer",
    "password": "password"
}

print("=== Testing API ===")

# Login
print("1. Login...")
response = requests.post(f"{base_url}/auth/login", json=login_data)
if response.status_code == 200:
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "accept": "application/json"}
    print("   ✅ Login successful")
else:
    print(f"   ❌ Login failed: {response.status_code}")
    print(f"   Response: {response.text}")
    exit(1)

# Test stats endpoint
print("\n2. Testing /api/v1/deals/stats...")
response = requests.get(f"{base_url}/api/v1/deals/stats", headers=headers)
if response.status_code == 200:
    stats = response.json()
    print("   ✅ Stats endpoint successful")
    print(f"   Total deals: {stats.get('total_deals', 'N/A')}")
    print(f"   Paid deals: {stats.get('paid_deals', 'N/A')}")
    print(f"   Unpaid deals: {stats.get('unpaid_deals', 'N/A')}")
    print(f"   Shipped deals: {stats.get('shipped_deals', 'N/A')}")
    print(f"   Unshipped deals: {stats.get('unshipped_deals', 'N/A')}")
    
    # Check if unpaid/unshipped are now calculated correctly
    print(f"\n   📊 Analysis:")
    print(f"   - Unpaid deals should include 'pending' + 'partial': {stats.get('unpaid_deals', 0)}")
    print(f"   - Unshipped deals should include 'pending' + 'partial': {stats.get('unshipped_deals', 0)}")
    
else:
    print(f"   ❌ Stats endpoint failed: {response.status_code}")
    print(f"   Response: {response.text}")

# Test deals list
print("\n3. Testing /api/v1/deals/...")
response = requests.get(f"{base_url}/api/v1/deals/", headers=headers)
if response.status_code == 200:
    deals = response.json()
    print("   ✅ Deals endpoint successful")
    print(f"   Total deals returned: {len(deals.get('items', []))}")
    if deals.get('items'):
        first_deal = deals['items'][0]
        print(f"   First deal - is_paid: {first_deal.get('is_paid')}, is_shipped: {first_deal.get('is_shipped')}")
else:
    print(f"   ❌ Deals endpoint failed: {response.status_code}")
    print(f"   Response: {response.text}") 
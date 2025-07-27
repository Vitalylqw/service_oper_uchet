#!/usr/bin/env python3
"""Check API endpoints with authentication."""

import requests
import json


def test_api():
    """Test API endpoints."""
    base_url = "http://localhost:8000"
    
    print("=== TESTING API ===")
    
    # Test root endpoint
    try:
        response = requests.get(f"{base_url}/")
        print(f"Root endpoint: {response.status_code}")
        if response.status_code == 200:
            print(f"Root response: {response.json()}")
    except Exception as e:
        print(f"Root check failed: {e}")
        return
    
    # Test health endpoint (no auth required)
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            print(f"Health response: {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return
    
    # Login to get token - try different paths
    login_paths = ["/auth/login", "/api/v1/auth/login", "/login"]
    token = None
    
    for login_path in login_paths:
        try:
            login_data = {
                "username": "admin",
                "password": "password"
            }
            response = requests.post(f"{base_url}{login_path}", json=login_data)
            print(f"Login {login_path}: {response.status_code}")
            
            if response.status_code == 200:
                token_response = response.json()
                token = token_response.get("access_token")
                if token:
                    print(f"✅ Login successful via {login_path}")
                    break
            else:
                print(f"Login {login_path} failed: {response.text[:100]}")
                
        except Exception as e:
            print(f"Login {login_path} error: {e}")
    
    if not token:
        print("❌ All login attempts failed")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test deals endpoints
    deals_paths = ["/deals/stats", "/api/v1/deals/stats", "/deals"]
    
    for deals_path in deals_paths:
        try:
            response = requests.get(f"{base_url}{deals_path}", headers=headers)
            print(f"Deals {deals_path}: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Deals data: {json.dumps(data, indent=2)[:200]}...")
                break
            else:
                print(f"Deals {deals_path} error: {response.text[:100]}")
        except Exception as e:
            print(f"Deals {deals_path} error: {e}")


if __name__ == "__main__":
    test_api() 
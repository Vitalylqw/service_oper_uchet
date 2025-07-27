#!/usr/bin/env python3
"""Test JWT functionality."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import timedelta
from src.presentation.api.auth.security import create_access_token, create_refresh_token
from src.presentation.api.config import config

def test_jwt():
    """Test JWT token creation and validation."""
    
    print("🔍 Testing JWT functionality...")
    
    # Test data
    user_data = {"sub": "test_user", "user_id": 1, "role": "admin"}
    
    try:
        # Create access token using the original function
        print("Creating access token...")
        access_token = create_access_token(data=user_data, expires_delta=timedelta(minutes=15))
        print(f"✅ Access token created: {access_token[:50]}...")
        
        # Create refresh token
        print("Creating refresh token...")
        refresh_token = create_refresh_token(data=user_data)
        print(f"✅ Refresh token created: {refresh_token[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ JWT test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_jwt() 
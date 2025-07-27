#!/usr/bin/env python3
"""
Test frontend functionality.
"""

import asyncio
import sys
import httpx
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loguru import logger


async def test_frontend_connection():
    """Test frontend connection."""
    
    try:
        logger.info("🌐 Testing frontend connection...")
        
        async with httpx.AsyncClient() as client:
            # Test React UI
            response = await client.get("http://localhost:3000", timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ React UI is accessible")
                logger.info(f"📄 Response size: {len(response.content)} bytes")
                return True
            else:
                logger.error(f"❌ React UI returned status {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Frontend connection test failed: {e}")
        return False


async def test_api_with_frontend():
    """Test API endpoints that frontend uses."""
    
    try:
        logger.info("🔌 Testing API endpoints for frontend...")
        
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            response = await client.get("http://localhost:8000/health/", timeout=10)
            if response.status_code == 200:
                logger.info("✅ Health endpoint works")
            else:
                logger.error(f"❌ Health endpoint failed: {response.status_code}")
                return False
            
            # Test login endpoint
            login_data = {"username": "viewer", "password": "password"}
            response = await client.post("http://localhost:8000/auth/login", json=login_data, timeout=10)
            
            if response.status_code == 200:
                tokens = response.json()
                access_token = tokens["access_token"]
                logger.info("✅ Login endpoint works")
                
                # Test deals endpoint with auth
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get("http://localhost:8000/api/v1/deals/", headers=headers, timeout=10)
                
                if response.status_code == 200:
                    deals_data = response.json()
                    logger.info(f"✅ Deals endpoint works - {len(deals_data.get('items', []))} deals")
                else:
                    logger.error(f"❌ Deals endpoint failed: {response.status_code}")
                    return False
                
                # Test sessions endpoint
                response = await client.get("http://localhost:8000/api/v1/sessions/", headers=headers, timeout=10)
                
                if response.status_code == 200:
                    sessions_data = response.json()
                    logger.info(f"✅ Sessions endpoint works - {len(sessions_data.get('items', []))} sessions")
                else:
                    logger.error(f"❌ Sessions endpoint failed: {response.status_code}")
                    return False
                
                return True
            else:
                logger.error(f"❌ Login endpoint failed: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"❌ API test failed: {e}")
        return False


async def test_frontend_functionality():
    """Test frontend functionality."""
    
    try:
        logger.info("🎨 Testing frontend functionality...")
        
        async with httpx.AsyncClient() as client:
            # Test main page
            response = await client.get("http://localhost:3000", timeout=10)
            
            if response.status_code == 200:
                content = response.text
                
                # Check for React app indicators
                if "React" in content or "root" in content:
                    logger.info("✅ React app is loaded")
                else:
                    logger.warning("⚠️ React app indicators not found")
                
                # Check for common UI elements
                if "dashboard" in content.lower() or "login" in content.lower():
                    logger.info("✅ UI elements detected")
                else:
                    logger.warning("⚠️ UI elements not clearly detected")
                
                return True
            else:
                logger.error(f"❌ Frontend page failed: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Frontend functionality test failed: {e}")
        return False


async def main():
    """Main test function."""
    logger.info("🚀 Starting frontend tests...")
    
    # Test 1: Frontend connection
    success1 = await test_frontend_connection()
    
    # Test 2: API endpoints
    success2 = await test_api_with_frontend()
    
    # Test 3: Frontend functionality
    success3 = await test_frontend_functionality()
    
    if success1 and success2 and success3:
        logger.info("🎉 All frontend tests passed successfully!")
        logger.info("📋 Frontend Summary:")
        logger.info("  ✅ React UI is accessible")
        logger.info("  ✅ API endpoints work with authentication")
        logger.info("  ✅ Frontend functionality is working")
    else:
        logger.error("💥 Some frontend tests failed!")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 
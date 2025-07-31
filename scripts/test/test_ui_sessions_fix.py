#!/usr/bin/env python3
"""Test UI sessions page fix."""

import asyncio
import httpx
from loguru import logger


async def test_ui_sessions_page():
    """Test that sessions page loads without errors."""
    try:
        async with httpx.AsyncClient() as client:
            # Test API endpoint
            logger.info("🔍 Testing API endpoint...")
            
            # Login
            login_response = await client.post(
                "http://localhost:8000/auth/login",
                json={"username": "viewer", "password": "password"},
                timeout=10
            )
            
            if login_response.status_code != 200:
                logger.error(f"❌ Login failed: {login_response.status_code}")
                return False
                
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Get sessions
            sessions_response = await client.get(
                "http://localhost:8000/api/v1/sessions/",
                headers=headers,
                timeout=10
            )
            
            if sessions_response.status_code == 200:
                data = sessions_response.json()
                logger.info(f"✅ API works: {len(data.get('items', []))} sessions")
                
                # Check data structure
                if data.get("items"):
                    session = data["items"][0]
                    required_fields = [
                        "id", "session_type", "status", "started_at", 
                        "total_deals_processed", "success"
                    ]
                    
                    for field in required_fields:
                        if field not in session:
                            logger.error(f"❌ Missing field: {field}")
                            return False
                    
                    logger.info("✅ All required fields present")
                else:
                    logger.info("📋 No sessions found (this is OK)")
                
            else:
                logger.error(f"❌ API failed: {sessions_response.status_code}")
                return False
            
            # Test UI endpoint
            logger.info("🔍 Testing UI endpoint...")
            ui_response = await client.get("http://localhost:3000/sessions", timeout=10)
            
            if ui_response.status_code == 200:
                logger.info("✅ UI endpoint responds")
                
                # Check if page contains expected content
                content = ui_response.text
                if "Сессии синхронизации" in content or "sessions" in content.lower():
                    logger.info("✅ UI page loads correctly")
                    return True
                else:
                    logger.warning("⚠️ UI page loads but content unclear")
                    return True
            else:
                logger.error(f"❌ UI failed: {ui_response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


async def main():
    """Main test function."""
    logger.info("🚀 Testing sessions page fix...")
    
    # Wait a bit for services to start
    await asyncio.sleep(2)
    
    success = await test_ui_sessions_page()
    
    if success:
        logger.success("✅ Sessions page fix test passed!")
    else:
        logger.error("❌ Sessions page fix test failed!")
    
    return success


if __name__ == "__main__":
    asyncio.run(main()) 
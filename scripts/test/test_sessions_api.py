#!/usr/bin/env python3
"""Test sessions API to check response structure."""

import asyncio
import json
import httpx
from loguru import logger


async def test_sessions_api():
    """Test sessions API endpoint."""
    try:
        async with httpx.AsyncClient() as client:
            # Login
            login_response = await client.post(
                "http://localhost:8000/auth/login",
                json={"username": "viewer", "password": "password"},
                timeout=10
            )
            
            if login_response.status_code != 200:
                logger.error(f"Login failed: {login_response.status_code}")
                return
                
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
                logger.info("✅ Sessions API response structure:")
                logger.info(json.dumps(data, indent=2, ensure_ascii=False))
                
                if data.get("items"):
                    first_session = data["items"][0]
                    logger.info("📋 First session fields:")
                    for key, value in first_session.items():
                        logger.info(f"  {key}: {value} ({type(value).__name__})")
                else:
                    logger.info("📋 No sessions found")
                    
            else:
                logger.error(f"Sessions API failed: {sessions_response.status_code}")
                logger.error(sessions_response.text)
                
    except Exception as e:
        logger.error(f"Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_sessions_api()) 
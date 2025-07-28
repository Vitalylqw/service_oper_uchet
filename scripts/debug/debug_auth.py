#!/usr/bin/env python3
"""Debug authentication issues."""

import asyncio
import json

import httpx
from loguru import logger


async def debug_auth():
    """Debug authentication step by step."""
    
    logger.info("🔍 Debugging authentication...")
    
    # Test 1: Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health/", timeout=5)
            logger.info(f"✅ Health check: {response.status_code}")
            if response.status_code == 200:
                logger.info(f"Health response: {response.json()}")
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return
    
    # Test 2: Try login with different credentials
    test_credentials = [
        {"username": "viewer", "password": "password"},
        {"username": "admin", "password": "password"},
        {"username": "analyst", "password": "password"},
    ]
    
    for creds in test_credentials:
        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"🔐 Testing login with {creds['username']}...")
                response = await client.post(
                    "http://localhost:8000/auth/login",
                    json=creds,
                    timeout=10
                )
                logger.info(f"Status: {response.status_code}")
                logger.info(f"Headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✅ Login successful: {data}")
                else:
                    logger.error(f"❌ Login failed: {response.text}")
                    
        except Exception as e:
            logger.error(f"❌ Login request failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_auth())

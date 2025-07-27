#!/usr/bin/env python3
"""
Test FastAPI endpoints with real services.
Uses HTTP requests to test the API without complex imports.
"""

import asyncio
import os
import time
from pathlib import Path

import requests
from loguru import logger


def setup_environment():
    """Setup environment variables for testing."""
    os.environ["DB_TYPE"] = "sqlite"
    os.environ["DB_SQLITE_DB_PATH"] = "data/service_oper_uchet.sqlite"


async def start_api_server():
    """Start FastAPI server in background."""
    try:
        import subprocess
        import sys

        # Change to project directory
        project_dir = Path(__file__).parent.parent

        # Start uvicorn server
        cmd = [
            sys.executable, "-m", "uvicorn",
            "src.presentation.api.main:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--reload"
        ]

        logger.info("🚀 Starting FastAPI server...")
        process = subprocess.Popen(
            cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Wait for server to start
        time.sleep(5)

        return process

    except Exception as e:
        logger.error(f"❌ Failed to start API server: {e}")
        return None


def test_health_endpoint():
    """Test health check endpoint."""
    try:
        logger.info("🏥 Testing health endpoint...")

        response = requests.get("http://127.0.0.1:8000/health/", timeout=10)

        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Health check passed: {data.get('status')}")
            logger.info(f"Components: {list(data.get('components', {}).keys())}")
            return True
        else:
            logger.error(f"❌ Health check failed: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ Health endpoint test failed: {e}")
        return False


def test_root_endpoint():
    """Test root endpoint."""
    try:
        logger.info("🌐 Testing root endpoint...")

        response = requests.get("http://127.0.0.1:8000/", timeout=10)

        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Root endpoint: {data.get('name')}")
            return True
        else:
            logger.error(f"❌ Root endpoint failed: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ Root endpoint test failed: {e}")
        return False


def test_deals_endpoint():
    """Test deals endpoint."""
    try:
        logger.info("💼 Testing deals endpoint...")

        response = requests.get(
            "http://127.0.0.1:8000/api/v1/deals/",
            params={"page": 1, "page_size": 10},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Deals endpoint: {data.get('total', 0)} deals found")
            logger.info(f"Items returned: {len(data.get('items', []))}")
            return True
        else:
            logger.error(f"❌ Deals endpoint failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ Deals endpoint test failed: {e}")
        return False


def test_sessions_endpoint():
    """Test sync sessions endpoint."""
    try:
        logger.info("🔄 Testing sessions endpoint...")

        response = requests.get(
            "http://127.0.0.1:8000/api/v1/sessions/",
            params={"page": 1, "page_size": 10},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Sessions endpoint: {data.get('total', 0)} sessions found")
            logger.info(f"Items returned: {len(data.get('items', []))}")
            return True
        else:
            logger.error(f"❌ Sessions endpoint failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ Sessions endpoint test failed: {e}")
        return False


def test_docs_endpoint():
    """Test API documentation endpoint."""
    try:
        logger.info("📚 Testing docs endpoint...")

        response = requests.get("http://127.0.0.1:8000/docs", timeout=10)

        if response.status_code == 200:
            logger.info("✅ API docs are accessible")
            return True
        else:
            logger.error(f"❌ Docs endpoint failed: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ Docs endpoint test failed: {e}")
        return False


def wait_for_server():
    """Wait for server to be ready."""
    logger.info("⏳ Waiting for server to be ready...")

    for i in range(30):  # Wait up to 30 seconds
        try:
            response = requests.get("http://127.0.0.1:8000/health/", timeout=2)
            if response.status_code == 200:
                logger.info("✅ Server is ready!")
                return True
        except:
            time.sleep(1)

    logger.error("❌ Server failed to start within 30 seconds")
    return False


async def main():
    """Main test function."""
    logger.info("🚀 Starting FastAPI endpoints testing...")

    # Setup environment
    setup_environment()

    success = True

    # Check if server is already running
    logger.info("🔍 Checking if server is already running...")
    try:
        response = requests.get("http://127.0.0.1:8000/health/", timeout=2)
        if response.status_code == 200:
            logger.info("✅ Server is already running!")
            server_process = None
        else:
            raise Exception("Server not responding")
    except:
        logger.info("📡 Starting new server instance...")
        server_process = await start_api_server()

        if not server_process:
            logger.error("❌ Failed to start server")
            return False

        # Wait for server to be ready
        if not wait_for_server():
            if server_process:
                server_process.terminate()
            return False

    try:
        # Run tests
        tests = [
            ("Root Endpoint", test_root_endpoint),
            ("Health Check", test_health_endpoint),
            ("Deals Endpoint", test_deals_endpoint),
            ("Sessions Endpoint", test_sessions_endpoint),
            ("API Docs", test_docs_endpoint),
        ]

        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"TEST: {test_name}")
            logger.info('='*50)

            test_success = test_func()
            if not test_success:
                success = False

        # Summary
        logger.info(f"\n{'='*50}")
        logger.info("TEST SUMMARY")
        logger.info('='*50)

        if success:
            logger.info("🎉 All API tests passed!")
        else:
            logger.error("💥 Some API tests failed!")

    finally:
        # Clean up - terminate server if we started it
        if server_process:
            logger.info("🛑 Stopping server...")
            server_process.terminate()
            server_process.wait()

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        exit(1)

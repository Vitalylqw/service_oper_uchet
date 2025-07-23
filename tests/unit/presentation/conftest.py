"""
Test fixtures for presentation layer tests.

Contains shared fixtures for FastAPI testing, authentication mocks, and test data.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.presentation.api.auth.models import User, UserRole
from src.presentation.api.main import create_app


@pytest.fixture
def app():
    """Create FastAPI application for testing."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_admin_user():
    """Mock admin user for testing."""
    return User(
        id=1,
        username="admin",
        email="admin@example.com",
        full_name="Test Admin",
        role=UserRole.ADMIN,
        is_active=True,
        created_at=datetime(2024, 1, 1, 0, 0, 0)
    )


@pytest.fixture
def mock_analyst_user():
    """Mock analyst user for testing."""
    return User(
        id=2,
        username="analyst",
        email="analyst@example.com",
        full_name="Test Analyst",
        role=UserRole.ANALYST,
        is_active=True,
        created_at=datetime(2024, 1, 1, 0, 0, 0)
    )


@pytest.fixture
def mock_viewer_user():
    """Mock viewer user for testing."""
    return User(
        id=3,
        username="viewer",
        email="viewer@example.com",
        full_name="Test Viewer",
        role=UserRole.VIEWER,
        is_active=True,
        created_at=datetime(2024, 1, 1, 0, 0, 0)
    )


@pytest.fixture
def admin_token():
    """JWT token for admin user."""
    # This is a test token - in real implementation this would be generated properly
    from src.presentation.api.auth.security import create_access_token

    token_data = {"sub": "admin", "user_id": 1, "role": "admin"}
    return create_access_token(token_data)


@pytest.fixture
def analyst_token():
    """JWT token for analyst user."""
    from src.presentation.api.auth.security import create_access_token

    token_data = {"sub": "analyst", "user_id": 2, "role": "analyst"}
    return create_access_token(token_data)


@pytest.fixture
def viewer_token():
    """JWT token for viewer user."""
    from src.presentation.api.auth.security import create_access_token

    token_data = {"sub": "viewer", "user_id": 3, "role": "viewer"}
    return create_access_token(token_data)


@pytest.fixture
def auth_headers_admin(admin_token):
    """Authorization headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def auth_headers_analyst(analyst_token):
    """Authorization headers for analyst user."""
    return {"Authorization": f"Bearer {analyst_token}"}


@pytest.fixture
def auth_headers_viewer(viewer_token):
    """Authorization headers for viewer user."""
    return {"Authorization": f"Bearer {viewer_token}"}

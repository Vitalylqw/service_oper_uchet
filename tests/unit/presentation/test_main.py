"""
Tests for main FastAPI application.

Tests application configuration, middleware, and root endpoints.
"""

from __future__ import annotations

from fastapi import status


class TestMainApplication:
    """Test main FastAPI application."""

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["name"] == "Service Oper Uchet API"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"

    def test_docs_available(self, client):
        """Test that OpenAPI docs are available."""
        response = client.get("/docs")
        assert response.status_code == status.HTTP_200_OK

    def test_openapi_schema(self, client):
        """Test OpenAPI schema endpoint."""
        response = client.get("/openapi.json")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Service Oper Uchet API"

    def test_cors_headers(self, client):
        """Test CORS middleware."""
        # Test preflight request
        response = client.options(
            "/api/v1/deals/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )

        # CORS should be configured to allow the request
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]

    def test_application_lifespan(self, app):
        """Test application lifespan configuration."""
        # Test that the app has lifespan configured
        assert app.router.lifespan_context is not None


class TestApplicationStructure:
    """Test application router structure."""

    def test_health_routes_included(self, client):
        """Test that health routes are properly included."""
        response = client.get("/health/")
        assert response.status_code == status.HTTP_200_OK

    def test_auth_routes_included(self, client):
        """Test that auth routes are properly included."""
        # Test login endpoint
        response = client.post("/auth/login", json={"username": "test", "password": "test"})
        # Should get 401 for invalid credentials, not 404 for missing route
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_deals_routes_included(self, client):
        """Test that deals routes are properly included."""
        response = client.get("/api/v1/deals/")
        # Should get 403 for missing auth, not 404 for missing route
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_sessions_routes_included(self, client):
        """Test that sessions routes are properly included."""
        response = client.get("/api/v1/sessions/")
        # Should get 403 for missing auth, not 404 for missing route
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_route_not_found(self, client):
        """Test 404 for non-existent routes."""
        response = client.get("/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND

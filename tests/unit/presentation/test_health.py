"""
Tests for health check endpoints.

Tests system health monitoring and status endpoints.
"""

from __future__ import annotations

from fastapi import status


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, client):
        """Test basic health check endpoint."""
        response = client.get("/health/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "components" in data

        # Check components structure
        components = data["components"]
        assert "api" in components
        assert "database" in components
        assert "auth" in components

    def test_readiness_check(self, client):
        """Test readiness check endpoint."""
        response = client.get("/health/ready")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "ready"

    def test_liveness_check(self, client):
        """Test liveness check endpoint."""
        response = client.get("/health/live")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "alive"

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/health/metrics")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check metrics structure
        expected_metrics = [
            "requests_total",
            "requests_duration_seconds",
            "database_connections",
            "active_sessions"
        ]

        for metric in expected_metrics:
            assert metric in data
            assert isinstance(data[metric], (int, float))

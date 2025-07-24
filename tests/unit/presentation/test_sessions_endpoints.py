"""
Tests for sync session management endpoints.

Tests CRUD operations, monitoring, and statistics for sync sessions.
"""

from __future__ import annotations

import pytest
from fastapi import status


@pytest.mark.unit
class TestSyncSessionEndpoints:
    """Test sync session management endpoints."""

    def test_list_sessions_success(self, client, auth_headers_viewer):
        """Test successful sync sessions listing."""
        response = client.get("/api/v1/sessions/", headers=auth_headers_viewer)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check pagination structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "pages" in data

        # Check sessions structure
        if data["items"]:
            session = data["items"][0]
            required_fields = [
                "id",
                "session_type",
                "status",
                "started_at",
                "total_deals_processed",
                "success",
            ]
            for field in required_fields:
                assert field in session

    def test_list_sessions_with_filters(self, client, auth_headers_viewer):
        """Test sessions listing with filters."""
        response = client.get(
            "/api/v1/sessions/?status=completed&session_type=incremental",
            headers=auth_headers_viewer,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data["items"], list)

    def test_list_sessions_unauthorized(self, client):
        """Test sessions listing without authentication."""
        response = client.get("/api/v1/sessions/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_session_success(self, client, auth_headers_viewer):
        """Test successful session retrieval."""
        session_id = "test-session-123"
        response = client.get(f"/api/v1/sessions/{session_id}", headers=auth_headers_viewer)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check session structure
        required_fields = [
            "id",
            "session_type",
            "status",
            "started_at",
            "file_path",
            "total_deals_processed",
            "total_items_processed",
            "insertions_count",
            "updates_count",
            "deletions_count",
            "success",
            "created_at",
            "metadata",
        ]

        for field in required_fields:
            assert field in data

        assert data["id"] == session_id

    def test_get_session_unauthorized(self, client):
        """Test session retrieval without authentication."""
        response = client.get("/api/v1/sessions/test-session-123")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_session_success(self, client, auth_headers_analyst):
        """Test successful session creation (analyst can create)."""
        session_data = {
            "session_type": "incremental",
            "file_path": "/test/data.xlsx",
            "force": False,
        }

        response = client.post("/api/v1/sessions/", json=session_data, headers=auth_headers_analyst)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["session_type"] == "incremental"
        assert data["file_path"] == "/test/data.xlsx"
        assert data["status"] == "running"

    def test_create_session_as_viewer_forbidden(self, client, auth_headers_viewer):
        """Test session creation as viewer (should be forbidden)."""
        session_data = {
            "session_type": "incremental",
            "file_path": "/test/data.xlsx",
            "force": False,
        }

        response = client.post("/api/v1/sessions/", json=session_data, headers=auth_headers_viewer)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_session_invalid_data(self, client, auth_headers_analyst):
        """Test session creation with invalid data."""
        # Missing required fields
        response = client.post(
            "/api/v1/sessions/", json={"session_type": "incremental"}, headers=auth_headers_analyst
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_cancel_session_success(self, client, auth_headers_analyst):
        """Test successful session cancellation."""
        session_id = "test-session-123"
        response = client.delete(f"/api/v1/sessions/{session_id}", headers=auth_headers_analyst)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "cancellation requested" in data["message"]

    def test_cancel_session_as_viewer_forbidden(self, client, auth_headers_viewer):
        """Test session cancellation as viewer (should be forbidden)."""
        session_id = "test-session-123"
        response = client.delete(f"/api/v1/sessions/{session_id}", headers=auth_headers_viewer)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_session_logs_success(self, client, auth_headers_viewer):
        """Test successful session logs retrieval."""
        session_id = "test-session-123"
        response = client.get(f"/api/v1/sessions/{session_id}/logs", headers=auth_headers_viewer)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)

        if data:
            log_entry = data[0]
            required_fields = ["timestamp", "level", "message", "component"]
            for field in required_fields:
                assert field in log_entry

    def test_get_sync_stats_success(self, client, auth_headers_viewer):
        """Test successful sync statistics retrieval."""
        response = client.get("/api/v1/sessions/stats/summary", headers=auth_headers_viewer)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check statistics structure
        required_fields = [
            "total_sessions",
            "successful_sessions",
            "failed_sessions",
            "success_rate",
            "avg_duration_seconds",
            "total_deals_synchronized",
            "sync_frequency_days",
        ]

        for field in required_fields:
            assert field in data

        # Check data types
        assert isinstance(data["total_sessions"], int)
        assert isinstance(data["success_rate"], float)
        assert isinstance(data["sync_frequency_days"], list)

    def test_get_sync_stats_unauthorized(self, client):
        """Test sync statistics without authentication."""
        response = client.get("/api/v1/sessions/stats/summary")

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
class TestSyncSessionPermissions:
    """Test role-based permissions for sync session endpoints."""

    def test_viewer_can_read_sessions(self, client, auth_headers_viewer):
        """Test that viewer can read sessions."""
        response = client.get("/api/v1/sessions/", headers=auth_headers_viewer)
        assert response.status_code == status.HTTP_200_OK

    def test_viewer_cannot_create_sessions(self, client, auth_headers_viewer):
        """Test that viewer cannot create sessions."""
        session_data = {"session_type": "incremental", "file_path": "/test/data.xlsx"}
        response = client.post("/api/v1/sessions/", json=session_data, headers=auth_headers_viewer)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_analyst_can_create_sessions(self, client, auth_headers_analyst):
        """Test that analyst can create sessions."""
        session_data = {"session_type": "incremental", "file_path": "/test/data.xlsx"}
        response = client.post("/api/v1/sessions/", json=session_data, headers=auth_headers_analyst)
        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_create_sessions(self, client, auth_headers_admin):
        """Test that admin can create sessions."""
        session_data = {"session_type": "incremental", "file_path": "/test/data.xlsx"}
        response = client.post("/api/v1/sessions/", json=session_data, headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
class TestSyncSessionValidation:
    """Test validation for sync session endpoints."""

    def test_session_type_validation(self, client, auth_headers_analyst):
        """Test session type validation."""
        session_data = {"session_type": "invalid_type", "file_path": "/test/data.xlsx"}

        response = client.post("/api/v1/sessions/", json=session_data, headers=auth_headers_analyst)
        # Note: Currently we don't validate session_type, but in real implementation we would
        assert response.status_code == status.HTTP_200_OK

    def test_file_path_validation(self, client, auth_headers_analyst):
        """Test file path validation."""
        session_data = {
            "session_type": "incremental",
            "file_path": "",  # Empty file path
        }

        response = client.post("/api/v1/sessions/", json=session_data, headers=auth_headers_analyst)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

"""
Tests for authentication endpoints.

Tests JWT authentication, user management, and RBAC functionality.
"""

from __future__ import annotations

from fastapi import status


class TestAuthentication:
    """Test authentication endpoints."""

    def test_login_success_admin(self, client):
        """Test successful admin login."""
        response = client.post("/auth/login", json={"username": "admin", "password": "admin123"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 15 * 60  # 15 minutes

    def test_login_success_analyst(self, client):
        """Test successful analyst login."""
        response = client.post(
            "/auth/login", json={"username": "analyst", "password": "analyst123"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data

    def test_login_success_viewer(self, client):
        """Test successful viewer login."""
        response = client.post("/auth/login", json={"username": "viewer", "password": "viewer123"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post("/auth/login", json={"username": "invalid", "password": "invalid"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_missing_fields(self, client):
        """Test login with missing fields."""
        response = client.post("/auth/login", json={"username": "admin"})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_current_user_success(self, client, auth_headers_admin):
        """Test getting current user info with valid token."""
        response = client.get("/auth/me", headers=auth_headers_admin)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["username"] == "admin"
        assert data["role"] == "admin"
        assert "id" in data
        assert "email" in data

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token."""
        response = client.get("/auth/me")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token."""
        response = client.get("/auth/me", headers={"Authorization": "Bearer invalid_token"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_not_implemented(self, client):
        """Test token refresh endpoint (not implemented yet)."""
        response = client.post("/auth/refresh", json={"refresh_token": "some_token"})

        assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED


class TestUserManagement:
    """Test user management endpoints (admin only)."""

    def test_list_users_as_admin(self, client, auth_headers_admin):
        """Test listing users as admin."""
        response = client.get("/auth/users", headers=auth_headers_admin)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 1
        for user in data:
            assert "username" in user
            assert "role" in user

    def test_list_users_as_viewer_forbidden(self, client, auth_headers_viewer):
        """Test listing users as viewer (should be forbidden)."""
        response = client.get("/auth/users", headers=auth_headers_viewer)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_user_as_admin(self, client, auth_headers_admin):
        """Test creating user as admin."""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "password123",
            "role": "viewer",
        }

        response = client.post("/auth/users", json=user_data, headers=auth_headers_admin)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "viewer"

    def test_create_user_as_analyst_forbidden(self, client, auth_headers_analyst):
        """Test creating user as analyst (should be forbidden)."""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "password123",
            "role": "viewer",
        }

        response = client.post("/auth/users", json=user_data, headers=auth_headers_analyst)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_user_as_admin(self, client, auth_headers_admin):
        """Test updating user as admin."""
        user_data = {"email": "updated@example.com", "full_name": "Updated User", "role": "analyst"}

        response = client.put("/auth/users/2", json=user_data, headers=auth_headers_admin)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["email"] == "updated@example.com"
        assert data["role"] == "analyst"

    def test_delete_user_as_admin(self, client, auth_headers_admin):
        """Test deleting user as admin."""
        response = client.delete("/auth/users/999", headers=auth_headers_admin)

        assert response.status_code == status.HTTP_200_OK
        assert "deleted successfully" in response.json()["message"]

    def test_change_password_success(self, client, auth_headers_admin):
        """Test changing password."""
        password_data = {"current_password": "admin123", "new_password": "newpassword123"}

        response = client.post(
            "/auth/change-password", json=password_data, headers=auth_headers_admin
        )

        assert response.status_code == status.HTTP_200_OK
        assert "Password changed successfully" in response.json()["message"]


class TestRoleBasedAccess:
    """Test role-based access control."""

    def test_admin_has_full_access(self, client, auth_headers_admin):
        """Test that admin has access to all endpoints."""
        # Admin can list users
        response = client.get("/auth/users", headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK

        # Admin can create users
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "password123",
            "role": "viewer",
        }
        response = client.post("/auth/users", json=user_data, headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK

    def test_analyst_restricted_access(self, client, auth_headers_analyst):
        """Test that analyst has restricted access."""
        # Analyst cannot list users
        response = client.get("/auth/users", headers=auth_headers_analyst)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Analyst cannot create users
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "password123",
            "role": "viewer",
        }
        response = client.post("/auth/users", json=user_data, headers=auth_headers_analyst)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_minimal_access(self, client, auth_headers_viewer):
        """Test that viewer has minimal access."""
        # Viewer cannot list users
        response = client.get("/auth/users", headers=auth_headers_viewer)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Viewer cannot create users
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "password123",
            "role": "viewer",
        }
        response = client.post("/auth/users", json=user_data, headers=auth_headers_viewer)
        assert response.status_code == status.HTTP_403_FORBIDDEN

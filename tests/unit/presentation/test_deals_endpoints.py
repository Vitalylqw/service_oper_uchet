"""
Tests for deal management endpoints.

Tests CRUD operations, filtering, pagination, and analytics for deals.
"""

from __future__ import annotations

import pytest
from fastapi import status


@pytest.mark.unit
class TestDealEndpoints:
    """Test deal management endpoints."""

    def test_list_deals_success(self, client, auth_headers_viewer):
        """Test successful deals listing."""
        response = client.get("/api/v1/deals/", headers=auth_headers_viewer)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check pagination structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "pages" in data

        # Check deals structure
        if data["items"]:
            deal = data["items"][0]
            required_fields = [
                "id",
                "deal_key",
                "client_name",
                "saller",
                "invoice_number",
                "invoice_date",
                "revenue",
                "margin",
                "is_shipped",
                "is_paid",
                "items_count",
            ]
            for field in required_fields:
                assert field in deal

    def test_list_deals_with_pagination(self, client, auth_headers_viewer):
        """Test deals listing with pagination parameters."""
        response = client.get("/api/v1/deals/?page=1&limit=10", headers=auth_headers_viewer)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["page"] == 1
        assert data["limit"] == 10

    def test_list_deals_with_filters(self, client, auth_headers_viewer):
        """Test deals listing with filters."""
        response = client.get(
            "/api/v1/deals/?client_name=Компания&is_shipped=true", headers=auth_headers_viewer
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check that filtering works (mock data should be filtered)
        assert isinstance(data["items"], list)

    def test_list_deals_unauthorized(self, client):
        """Test deals listing without authentication."""
        response = client.get("/api/v1/deals/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_deal_success(self, client, auth_headers_viewer):
        """Test successful deal retrieval."""
        import uuid
        deal_id = str(uuid.uuid4())  # Используем правильный UUID
        response = client.get(f"/api/v1/deals/{deal_id}", headers=auth_headers_viewer)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check deal structure
        required_fields = [
            "id",
            "deal_key",
            "client_name",
            "saller",
            "invoice_number",
            "invoice_date",
            "revenue",
            "margin",
            "cost",
            "is_shipped",
            "is_paid",
            "period_month",
            "period_year",
            "created_at",
            "updated_at",
            "items",
        ]

        for field in required_fields:
            assert field in data

        assert data["id"] == deal_id

    def test_get_deal_unauthorized(self, client):
        """Test deal retrieval without authentication."""
        response = client.get("/api/v1/deals/test-deal-123")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_deal_history_success(self, client, auth_headers_viewer):
        """Test successful deal history retrieval."""
        deal_id = "test-deal-123"
        response = client.get(f"/api/v1/deals/{deal_id}/history", headers=auth_headers_viewer)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)

        if data:
            event = data[0]
            required_fields = ["event_id", "event_type", "timestamp", "user", "changes"]
            for field in required_fields:
                assert field in event

    def test_get_deals_stats_success(self, client, auth_headers_viewer):
        """Test successful deals statistics retrieval."""
        response = client.get("/api/v1/deals/stats/summary", headers=auth_headers_viewer)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check statistics structure
        required_fields = [
            "total_deals",
            "total_revenue",
            "total_margin",
            "shipped_deals",
            "paid_deals",
            "unpaid_deals",
            "unshipped_deals",
            "avg_revenue",
            "top_clients",
            "revenue_by_month",
        ]

        for field in required_fields:
            assert field in data

        # Check data types
        assert isinstance(data["total_deals"], int)
        assert isinstance(data["top_clients"], list)
        assert isinstance(data["revenue_by_month"], list)

    def test_get_deals_stats_with_filters(self, client, auth_headers_viewer):
        """Test deals statistics with period filters."""
        response = client.get(
            "/api/v1/deals/stats/summary?period_month=01&period_year=2024",
            headers=auth_headers_viewer,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "total_deals" in data

    def test_get_deals_stats_unauthorized(self, client):
        """Test deals statistics without authentication."""
        response = client.get("/api/v1/deals/stats/summary")

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
class TestDealPermissions:
    """Test role-based permissions for deal endpoints."""

    def test_viewer_can_read_deals(self, client, auth_headers_viewer):
        """Test that viewer can read deals."""
        response = client.get("/api/v1/deals/", headers=auth_headers_viewer)
        assert response.status_code == status.HTTP_200_OK

    def test_analyst_can_read_deals(self, client, auth_headers_analyst):
        """Test that analyst can read deals."""
        response = client.get("/api/v1/deals/", headers=auth_headers_analyst)
        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_read_deals(self, client, auth_headers_admin):
        """Test that admin can read deals."""
        response = client.get("/api/v1/deals/", headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
class TestDealPagination:
    """Test pagination functionality for deals."""

    def test_pagination_params_validation(self, client, auth_headers_viewer):
        """Test pagination parameter validation."""
        # Test invalid page number
        response = client.get("/api/v1/deals/?page=0", headers=auth_headers_viewer)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test invalid limit
        response = client.get("/api/v1/deals/?limit=0", headers=auth_headers_viewer)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test limit too large
        response = client.get("/api/v1/deals/?limit=1000", headers=auth_headers_viewer)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_pagination_response_structure(self, client, auth_headers_viewer):
        """Test pagination response structure."""
        response = client.get("/api/v1/deals/?page=1&limit=5", headers=auth_headers_viewer)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check pagination metadata
        assert data["page"] == 1
        assert data["limit"] == 5
        assert isinstance(data["total"], int)
        assert isinstance(data["pages"], int)
        assert len(data["items"]) <= 5

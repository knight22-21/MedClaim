"""
MedClaim — Health Endpoint Tests

Verifies the /health endpoint returns correct status, version,
and service connectivity placeholders.
"""

import pytest


@pytest.mark.unit
class TestHealthEndpoint:
    """Tests for the system health check endpoint."""

    def test_health_returns_200(self, client):
        """Health endpoint should return HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client):
        """Health response should contain all required fields."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "environment" in data
        assert "market" in data
        assert "services" in data

    def test_health_status_is_healthy(self, client):
        """Health status should be 'healthy' when app starts correctly."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_version_format(self, client):
        """Version should follow semver format."""
        response = client.get("/health")
        data = response.json()
        parts = data["version"].split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_health_services_listed(self, client):
        """All external service statuses should be present."""
        response = client.get("/health")
        services = response.json()["services"]

        expected_services = ["groq", "qdrant", "supabase", "hapi_fhir"]
        for service in expected_services:
            assert service in services

    def test_health_market_default(self, client):
        """Default market should be US."""
        response = client.get("/health")
        data = response.json()
        assert data["market"] == "US"

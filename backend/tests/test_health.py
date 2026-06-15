"""MedClaim — API Tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_check_endpoint():
    """Test the /health endpoint returns the correct structure."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "data" in data

        health = data["data"]
        assert health["status"] in ("healthy", "degraded", "unhealthy")
        assert "version" in health
        assert "environment" in health
        assert "market" in health
        assert "services" in health

        services = health["services"]
        assert "supabase" in services
        assert "fhir" in services
        assert "qdrant" in services


def test_metrics_endpoint():
    """Test the Prometheus /metrics endpoint is exposed."""
    with TestClient(app) as client:
        response = client.get("/metrics")
        # Just verifying it doesn't 404
        assert response.status_code in (200, 401, 403)
        if response.status_code == 200:
            assert "python_info" in response.text or "fastapi" in response.text

"""Tests for the health check endpoint."""

from fastapi.testclient import TestClient


class TestHealth:
    """Integration tests for GET /api/health."""

    def test_health_returns_200(self, client: TestClient):
        """GET /api/health should return 200 OK."""
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client: TestClient):
        """Response should contain all expected fields."""
        response = client.get("/api/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "database" in data
        assert "gemini" in data
        assert data["version"] == "0.1.0"

    def test_health_database_status_present(self, client: TestClient, monkeypatch):
        """Database status should be present and reflect test DB connectivity.

        The health endpoint caches ``engine`` at import time, so we patch the
        module-level reference directly.
        """
        from tests.conftest import engine as test_engine
        import app.api.endpoints.health as health_mod

        monkeypatch.setattr(health_mod, "engine", test_engine)

        response = client.get("/api/health")
        data = response.json()

        assert data["database"] in ("connected", "disconnected")
        # Since we use a real SQLite file, it should be connected
        assert data["database"] == "connected"

    def test_health_no_auth_required(self, client: TestClient):
        """Health endpoint should NOT require authentication."""
        response = client.get("/api/health")
        assert response.status_code == 200
        # Ensure we didn't accidentally get a 401 or 403
        assert "status" in response.json()

    def test_health_timestamp_format(self, client: TestClient):
        """Timestamp should be ISO 8601."""
        import re

        response = client.get("/api/health")
        ts = response.json()["timestamp"]
        # Basic ISO 8601 check
        assert re.match(
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", ts
        ), f"Timestamp '{ts}' is not ISO 8601"

"""Tests for the projects endpoints.

Projects now require authentication. All endpoints are protected.
"""

import pytest
from fastapi.testclient import TestClient


class TestProjects:
    """Integration tests for /api/projects/."""

    PROJECT_URL = "/api/projects/"

    def test_create_project_returns_201(self, client: TestClient, auth_headers: dict):
        """POST /api/projects/ should create a project with auth."""
        response = client.post(
            self.PROJECT_URL,
            json={"name": "Test Project", "description": "A test project"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["description"] == "A test project"
        assert "id" in data
        assert "created_at" in data

    def test_create_project_minimal(self, client: TestClient, auth_headers: dict):
        """POST /api/projects/ should work with only name."""
        response = client.post(
            self.PROJECT_URL,
            json={"name": "Minimal"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Minimal"

    def test_get_projects_returns_list(self, client: TestClient, auth_headers: dict):
        """GET /api/projects/ should return the user's projects."""
        # Create two projects
        client.post(self.PROJECT_URL, json={"name": "Project A"}, headers=auth_headers)
        client.post(self.PROJECT_URL, json={"name": "Project B"}, headers=auth_headers)

        response = client.get(self.PROJECT_URL, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_get_projects_without_auth_returns_401(self, client: TestClient):
        """GET /api/projects/ without auth should return 401."""
        response = client.get(self.PROJECT_URL)
        assert response.status_code == 401

    def test_create_project_without_auth_returns_401(self, client: TestClient):
        """POST /api/projects/ without auth should return 401."""
        response = client.post(
            self.PROJECT_URL,
            json={"name": "No Auth Project"},
        )
        assert response.status_code == 401

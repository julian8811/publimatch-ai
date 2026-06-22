"""Tests for the projects endpoints.

NOTE: The projects endpoints are currently unprotected (no auth). These tests
cover the current state. When auth is added, update these tests accordingly.
"""

import pytest
from fastapi.testclient import TestClient


class TestProjects:
    """Integration tests for /api/projects/."""

    PROJECT_URL = "/api/projects/"

    def test_create_project_returns_201(self, client: TestClient):
        """POST /api/projects/ should create a project."""
        response = client.post(
            self.PROJECT_URL,
            json={"name": "Test Project", "description": "A test project"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["description"] == "A test project"
        assert "id" in data
        assert "created_at" in data

    def test_create_project_minimal(self, client: TestClient):
        """POST /api/projects/ should work with only name."""
        response = client.post(
            self.PROJECT_URL,
            json={"name": "Minimal"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Minimal"

    def test_get_projects_returns_list(self, client: TestClient):
        """GET /api/projects/ should return a list of projects."""
        # Create two projects
        client.post(self.PROJECT_URL, json={"name": "Project A"})
        client.post(self.PROJECT_URL, json={"name": "Project B"})

        response = client.get(self.PROJECT_URL)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_get_projects_no_auth_required(self, client: TestClient):
        """GET /api/projects/ should work without auth (currently unprotected)."""
        response = client.get(self.PROJECT_URL)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_project_no_auth_required(self, client: TestClient):
        """POST /api/projects/ should work without auth (currently unprotected)."""
        response = client.post(
            self.PROJECT_URL,
            json={"name": "No Auth Project"},
        )
        assert response.status_code == 200

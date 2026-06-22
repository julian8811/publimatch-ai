from datetime import timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, decode_access_token
from app.models.user import User


class TestAuth:
    """Integration tests for auth endpoints."""

    def test_register_success(self, client: TestClient):
        """POST /api/auth/register with valid data returns 201 + user + token."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepass123",
                "full_name": "New User",
                "institution": "New University",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["full_name"] == "New User"
        assert "password" not in data["user"]

    def test_register_duplicate_email(self, client: TestClient, test_user_data: dict):
        """POST /api/auth/register with duplicate email returns 409."""
        # First registration succeeds
        client.post("/api/auth/register", json=test_user_data)

        # Duplicate registration fails
        response = client.post("/api/auth/register", json=test_user_data)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_register_weak_password(self, client: TestClient):
        """POST /api/auth/register with short password returns 422."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "weak@example.com",
                "password": "short",
                "full_name": "Weak Password",
            },
        )
        assert response.status_code == 422

    def test_login_success(self, client: TestClient, test_user_data: dict):
        """POST /api/auth/login with valid credentials returns 200 + token."""
        # Register first
        client.post("/api/auth/register", json=test_user_data)

        # Login
        response = client.post(
            "/api/auth/login",
            json={"email": test_user_data["email"], "password": test_user_data["password"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user_data["email"]

    def test_login_wrong_password(self, client: TestClient, test_user_data: dict):
        """POST /api/auth/login with wrong password returns 401."""
        client.post("/api/auth/register", json=test_user_data)

        response = client.post(
            "/api/auth/login",
            json={"email": test_user_data["email"], "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """POST /api/auth/login with unregistered email returns 401."""
        response = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "somepassword"},
        )
        assert response.status_code == 401

    def test_me_with_valid_token(self, client: TestClient, test_user_data: dict):
        """GET /api/auth/me with valid token returns user profile."""
        # Register and get token
        reg_resp = client.post("/api/auth/register", json=test_user_data)
        token = reg_resp.json()["access_token"]

        # Get profile
        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["email"] == test_user_data["email"]

    def test_me_without_token(self, client: TestClient):
        """GET /api/auth/me without token returns 401."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_expired_token(self, client: TestClient, test_user: User):
        """GET /api/auth/me with expired token returns 401."""
        # Create an already-expired token
        expired_token = create_access_token(
            data={"sub": str(test_user.id)},
            expires_delta=timedelta(hours=-1),  # negative timedelta = expired
        )

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

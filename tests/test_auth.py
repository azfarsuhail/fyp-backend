"""
Tests for /api/v1/auth — Registration & Login
"""

import pytest


class TestRegister:
    """POST /api/v1/auth/register"""

    def test_register_success(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@test.com",
            "password": "securepass123",
            "full_name": "New User",
            "role": "patient",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["full_name"] == "New User"
        assert data["role"] == "patient"
        assert "user_id" in data
        assert "created_at" in data

    def test_register_duplicate_email(self, client, seed_patient):
        response = client.post("/api/v1/auth/register", json={
            "email": "patient@test.com",  # Already exists via seed_patient
            "password": "securepass123",
            "full_name": "Duplicate User",
            "role": "patient",
        })
        assert response.status_code == 400
        assert response.json()["detail"] == "Email already registered"

    def test_register_invalid_email(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "securepass123",
            "full_name": "Bad Email User",
        })
        assert response.status_code == 422  # Pydantic validation error

    def test_register_missing_fields(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "incomplete@test.com",
        })
        assert response.status_code == 422

    def test_register_gp_role(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "gp@newtest.com",
            "password": "securepass123",
            "full_name": "GP User",
            "role": "gp",
        })
        assert response.status_code == 201
        assert response.json()["role"] == "gp"

    def test_register_admin_forbidden(self, client):
        """Should NOT allow public registration as admin."""
        response = client.post("/api/v1/auth/register", json={
            "email": "eviladmin@test.com",
            "password": "securepass123",
            "full_name": "Evil Admin",
            "role": "admin",
        })
        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()
        response = client.post("/api/v1/auth/register", json={
            "email": "admin@newtest.com",
            "password": "securepass123",
            "full_name": "Admin User",
            "role": "admin",
        })
        assert response.status_code == 201
        assert response.json()["role"] == "admin"


class TestLogin:
    """POST /api/v1/auth/login"""

    def test_login_success(self, client, seed_patient):
        response = client.post("/api/v1/auth/login", data={
            "username": "patient@test.com",
            "password": "password123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, seed_patient):
        response = client.post("/api/v1/auth/login", data={
            "username": "patient@test.com",
            "password": "wrongpassword",
        })
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"

    def test_login_nonexistent_user(self, client):
        response = client.post("/api/v1/auth/login", data={
            "username": "nobody@test.com",
            "password": "password123",
        })
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        response = client.post("/api/v1/auth/login", data={})
        assert response.status_code == 422

    def test_login_updates_last_login(self, client, seed_patient, db):
        """After login, the user's last_login timestamp should be set."""
        from app.models.user import User

        assert seed_patient.last_login is None

        client.post("/api/v1/auth/login", data={
            "username": "patient@test.com",
            "password": "password123",
        })

        db.refresh(seed_patient)
        assert seed_patient.last_login is not None

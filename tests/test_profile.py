"""
Tests for /api/v1/profile — Profile Management
"""

import pytest


class TestGetProfile:
    """GET /api/v1/profile/me"""

    def test_get_profile_success(self, client, patient_headers, seed_patient):
        response = client.get("/api/v1/profile/me", headers=patient_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "patient@test.com"
        assert data["full_name"] == "Test Patient"
        assert data["role"] == "patient"
        assert "user_id" in data
        assert "created_at" in data

    def test_get_profile_gp(self, client, gp_headers, seed_gp):
        response = client.get("/api/v1/profile/me", headers=gp_headers)
        assert response.status_code == 200
        assert response.json()["role"] == "gp"

    def test_get_profile_admin(self, client, admin_headers, seed_admin):
        response = client.get("/api/v1/profile/me", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    def test_get_profile_no_auth(self, client):
        response = client.get("/api/v1/profile/me")
        assert response.status_code == 401


class TestUpdateProfile:
    """PUT /api/v1/profile/me"""

    def test_update_name(self, client, patient_headers, seed_patient):
        response = client.put(
            "/api/v1/profile/me",
            json={"full_name": "Updated Name"},
            headers=patient_headers,
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated Name"
        assert response.json()["email"] == "patient@test.com"  # Unchanged

    def test_update_email(self, client, patient_headers, seed_patient):
        response = client.put(
            "/api/v1/profile/me",
            json={"email": "newemail@test.com"},
            headers=patient_headers,
        )
        assert response.status_code == 200
        assert response.json()["email"] == "newemail@test.com"

    def test_update_email_duplicate(self, client, patient_headers, seed_patient, seed_gp):
        """Should reject if the new email is already taken by another user."""
        response = client.put(
            "/api/v1/profile/me",
            json={"email": "gp@test.com"},  # Already taken by seed_gp
            headers=patient_headers,
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Email already in use"

    def test_update_both_fields(self, client, patient_headers, seed_patient):
        response = client.put(
            "/api/v1/profile/me",
            json={"full_name": "New Name", "email": "brand_new@test.com"},
            headers=patient_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "New Name"
        assert data["email"] == "brand_new@test.com"

    def test_update_no_auth(self, client):
        response = client.put("/api/v1/profile/me", json={"full_name": "Hacker"})
        assert response.status_code == 401

    def test_update_empty_body(self, client, patient_headers, seed_patient):
        """Empty update should succeed without changing anything."""
        response = client.put(
            "/api/v1/profile/me",
            json={},
            headers=patient_headers,
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Test Patient"


class TestChangePassword:
    """POST /api/v1/profile/me/change-password"""

    def test_change_password_success(self, client, patient_headers, seed_patient):
        response = client.post(
            "/api/v1/profile/me/change-password",
            json={"current_password": "password123", "new_password": "newpass456"},
            headers=patient_headers,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Password updated successfully"

        # Verify new password works for login
        login_resp = client.post("/api/v1/auth/login", data={
            "username": "patient@test.com",
            "password": "newpass456",
        })
        assert login_resp.status_code == 200

    def test_change_password_wrong_current(self, client, patient_headers, seed_patient):
        response = client.post(
            "/api/v1/profile/me/change-password",
            json={"current_password": "wrongpass", "new_password": "newpass456"},
            headers=patient_headers,
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Current password is incorrect"

    def test_change_password_no_auth(self, client):
        response = client.post(
            "/api/v1/profile/me/change-password",
            json={"current_password": "pass", "new_password": "newpass"},
        )
        assert response.status_code == 401

    def test_change_password_missing_fields(self, client, patient_headers, seed_patient):
        response = client.post(
            "/api/v1/profile/me/change-password",
            json={"current_password": "password123"},
            headers=patient_headers,
        )
        assert response.status_code == 422

"""
Tests for /api/v1/profile - Profile Management
"""

import pytest
import uuid
from app.models.profile_log import ProfileLog


class TestGetProfile:
    """GET /api/v1/profile/me"""

    def test_get_profile_success(self, client, patient_headers, seed_patient):
        response = client.get("/api/v1/profile/me", headers=patient_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"].startswith("patient_")
        assert data["email"].endswith("@test.com")
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
        email = response.json()["email"]
        assert email.startswith("patient_")
        assert email.endswith("@test.com")  # Unchanged

    def test_update_email(self, client, patient_headers, seed_patient):
        unique_email = f"newemail_{uuid.uuid4().hex[:8]}@test.com"
        response = client.put(
            "/api/v1/profile/me",
            json={"email": unique_email},
            headers=patient_headers,
        )
        assert response.status_code == 200
        assert response.json()["email"] == unique_email

    def test_update_email_duplicate(self, client, patient_headers, seed_patient, seed_gp):
        """Should reject if the new email is already taken by another user."""
        # Get the actual email of seed_gp
        gp_email = seed_gp.email
        response = client.put(
            "/api/v1/profile/me",
            json={"email": gp_email},  # Already taken by seed_gp
            headers=patient_headers,
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Email already in use"

    def test_update_both_fields(self, client, patient_headers, seed_patient):
        unique_email = f"brand_new_{uuid.uuid4().hex[:8]}@test.com"
        response = client.put(
            "/api/v1/profile/me",
            json={"full_name": "New Name", "email": unique_email},
            headers=patient_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "New Name"
        assert data["email"] == unique_email

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

    def test_change_password_success(self, client, patient_headers, seed_patient, db):
        # Reset rate limiter to avoid blocking the login after password change
        from app.core.security_middleware import auth_rate_limiter
        auth_rate_limiter.attempts.clear()
        
        response = client.post(
            "/api/v1/profile/me/change-password",
            json={"current_password": "SecurePass123!@#", "new_password": "NewPass456!@#"},
            headers=patient_headers,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Password updated successfully"

        # Verify new password works for login (use actual patient email from fixture)
        login_resp = client.post("/api/v1/auth/login", data={
            "username": seed_patient.email,
            "password": "NewPass456!@#",
        })
        assert login_resp.status_code == 200

    def test_change_password_wrong_current(self, client, patient_headers, seed_patient):
        response = client.post(
            "/api/v1/profile/me/change-password",
            json={"current_password": "WrongPass123!@#", "new_password": "NewPass456!@#"},
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
            json={"current_password": "SecurePass123!@#"},
            headers=patient_headers,
        )
        assert response.status_code == 422


class TestProfileHistory:
    """GET /api/v1/profile/me/history"""

    def test_get_history_empty(self, client, patient_headers, seed_patient):
        """Should return empty history for new user."""
        response = client.get("/api/v1/profile/me/history", headers=patient_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == seed_patient.user_id
        assert data["full_name"] == "Test Patient"
        assert data["total_changes"] == 0
        assert data["history"] == []

    def test_get_history_with_logs(self, client, patient_headers, seed_patient, db):
        """Should return all logged changes."""
        from app.models.profile_log import ProfileLog
        
        # Create some log entries
        log1 = ProfileLog(
            user_id=seed_patient.user_id,
            field_name="pain_level",
            old_value="3",
            new_value="5",
        )
        log2 = ProfileLog(
            user_id=seed_patient.user_id,
            field_name="mobility_level",
            old_value="good",
            new_value="moderate",
        )
        db.add(log1)
        db.add(log2)
        # Use flush() instead of commit() to preserve parallel test isolation
        db.flush()

        response = client.get("/api/v1/profile/me/history", headers=patient_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_changes"] == 2
        assert len(data["history"]) == 2
        # Should contain both fields regardless of order
        field_names = {log["field_name"] for log in data["history"]}
        assert field_names == {"pain_level", "mobility_level"}

    def test_get_history_no_auth(self, client):
        """Should require authentication."""
        response = client.get("/api/v1/profile/me/history")
        assert response.status_code == 401

    def test_get_history_gp(self, client, gp_headers, seed_gp):
        """GP should be able to view their own history."""
        response = client.get("/api/v1/profile/me/history", headers=gp_headers)
        assert response.status_code == 200
        assert response.json()["user_id"] == seed_gp.user_id

    def test_get_patient_history_gp_and_admin_access(self, client, gp_headers, admin_headers, seed_patient, db):
        """GP and admin can fetch another patient's history."""
        # Create a log entry for the patient
        from app.models.profile_log import ProfileLog

        log = ProfileLog(
            user_id=seed_patient.user_id,
            field_name="pain_level",
            old_value="2",
            new_value="4",
        )
        db.add(log)
        db.commit()  # Commit within transaction so API can see it
        db.refresh(log)  # Ensure log has ID

        # GP access
        gp_resp = client.get(f"/api/v1/profile/patients/{seed_patient.user_id}/history", headers=gp_headers)
        assert gp_resp.status_code == 200
        assert gp_resp.json()["user_id"] == seed_patient.user_id
        assert gp_resp.json()["total_changes"] == 1

        # Admin access
        admin_resp = client.get(f"/api/v1/profile/patients/{seed_patient.user_id}/history", headers=admin_headers)
        assert admin_resp.status_code == 200
        assert admin_resp.json()["user_id"] == seed_patient.user_id
        assert admin_resp.json()["total_changes"] == 1

    def test_get_patient_history_patient_forbidden(self, client, patient_headers, seed_patient):
        """A patient must not access the /patients/{id}/history route."""
        response = client.get(f"/api/v1/profile/patients/{seed_patient.user_id}/history", headers=patient_headers)
        assert response.status_code == 403


class TestProfileLogging:
    """Test that profile changes are properly logged."""

    def test_log_full_name_change(self, client, patient_headers, seed_patient, db):
        """Changing full_name should create a log entry."""
        response = client.put(
            "/api/v1/profile/me",
            json={"full_name": "New Name"},
            headers=patient_headers,
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "New Name"

        # Verify log was created
        log = db.query(ProfileLog).filter(
            ProfileLog.user_id == seed_patient.user_id,
            ProfileLog.field_name == "full_name"
        ).first()
        assert log is not None
        assert log.old_value == "Test Patient"
        assert log.new_value == "New Name"

    def test_log_age_change(self, client, patient_headers, seed_patient, db):
        """Changing age should create a log entry."""
        response = client.put(
            "/api/v1/profile/me",
            json={"age": 35},
            headers=patient_headers,
        )
        assert response.status_code == 200
        assert response.json()["age"] == 35

        log = db.query(ProfileLog).filter(
            ProfileLog.user_id == seed_patient.user_id,
            ProfileLog.field_name == "age"
        ).first()
        assert log is not None
        assert log.old_value is None
        assert log.new_value == "35"

    def test_log_pain_level_change(self, client, patient_headers, seed_patient, db):
        """Changing pain_level should create a log entry."""
        response = client.put(
            "/api/v1/profile/me",
            json={"pain_level": 7},
            headers=patient_headers,
        )
        assert response.status_code == 200
        assert response.json()["pain_level"] == 7

        log = db.query(ProfileLog).filter(
            ProfileLog.user_id == seed_patient.user_id,
            ProfileLog.field_name == "pain_level"
        ).first()
        assert log is not None
        assert log.old_value is None
        assert log.new_value == "7"

    def test_log_mobility_level_change(self, client, patient_headers, seed_patient, db):
        """Changing mobility_level should create a log entry."""
        response = client.put(
            "/api/v1/profile/me",
            json={"mobility_level": "limited"},
            headers=patient_headers,
        )
        assert response.status_code == 200
        assert response.json()["mobility_level"] == "limited"

        log = db.query(ProfileLog).filter(
            ProfileLog.user_id == seed_patient.user_id,
            ProfileLog.field_name == "mobility_level"
        ).first()
        assert log is not None
        assert log.old_value is None
        assert log.new_value == "limited"

    def test_log_has_support_change(self, client, patient_headers, seed_patient, db):
        """Changing has_support should create a log entry."""
        response = client.put(
            "/api/v1/profile/me",
            json={"has_support": True},
            headers=patient_headers,
        )
        assert response.status_code == 200
        assert response.json()["has_support"] is True

        log = db.query(ProfileLog).filter(
            ProfileLog.user_id == seed_patient.user_id,
            ProfileLog.field_name == "has_support"
        ).first()
        assert log is not None
        assert log.old_value is None
        assert log.new_value == "True"

    def test_no_log_for_same_value(self, client, patient_headers, seed_patient, db):
        """Setting same value should not create duplicate log."""
        # First update
        client.put(
            "/api/v1/profile/me",
            json={"pain_level": 5},
            headers=patient_headers,
        )
        
        # Update with same value
        client.put(
            "/api/v1/profile/me",
            json={"pain_level": 5},
            headers=patient_headers,
        )

        # Should only have one log entry
        logs = db.query(ProfileLog).filter(
            ProfileLog.user_id == seed_patient.user_id,
            ProfileLog.field_name == "pain_level"
        ).all()
        assert len(logs) == 1

    def test_log_multiple_fields_single_request(self, client, patient_headers, seed_patient, db):
        """Updating multiple fields should create multiple log entries."""
        response = client.put(
            "/api/v1/profile/me",
            json={
                "age": 40,
                "pain_level": 6,
                "mobility_level": "moderate",
            },
            headers=patient_headers,
        )
        assert response.status_code == 200

        # Should have 3 log entries
        logs = db.query(ProfileLog).filter(
            ProfileLog.user_id == seed_patient.user_id
        ).all()
        assert len(logs) == 3
        field_names = {log.field_name for log in logs}
        assert field_names == {"age", "pain_level", "mobility_level"}

    def test_log_email_change(self, client, patient_headers, seed_patient, db):
        """Changing email should create a log entry."""
        old_email = seed_patient.email
        new_email = f"newemail_{uuid.uuid4().hex[:8]}@test.com"  # Guaranteed Unique
        response = client.put(
            "/api/v1/profile/me",
            json={"email": new_email},
            headers=patient_headers,
        )
        assert response.status_code == 200
        assert response.json()["email"] == new_email

        log = db.query(ProfileLog).filter(
            ProfileLog.user_id == seed_patient.user_id,
            ProfileLog.field_name == "email"
        ).first()
        assert log is not None
        assert log.old_value == old_email
        assert log.new_value == new_email

    def test_update_with_all_fields(self, client, patient_headers, seed_patient, db):
        """Updating all patient context fields should log each one."""
        response = client.put(
            "/api/v1/profile/me",
            json={
                "full_name": "Complete Name",
                "age": 45,
                "pain_level": 8,
                "mobility_level": "limited",
                "has_support": False,
            },
            headers=patient_headers,
        )
        assert response.status_code == 200

        # Should have 5 log entries (one for each field)
        logs = db.query(ProfileLog).filter(
            ProfileLog.user_id == seed_patient.user_id
        ).all()
        assert len(logs) == 5
        field_names = {log.field_name for log in logs}
        assert field_names == {"full_name", "age", "pain_level", "mobility_level", "has_support"}

    def test_gp_can_update_patient_context(self, client, gp_headers, seed_gp, db):
        """GP should be able to update their own patient context fields."""
        response = client.put(
            "/api/v1/profile/me",
            json={"pain_level": 4, "mobility_level": "good"},
            headers=gp_headers,
        )
        assert response.status_code == 200
        assert response.json()["pain_level"] == 4
        assert response.json()["mobility_level"] == "good"

        # Verify logs were created
        logs = db.query(ProfileLog).filter(
            ProfileLog.user_id == seed_gp.user_id
        ).all()
        assert len(logs) == 2
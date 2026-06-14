"""
Tests for Mobile Sync API
--------------------------
Tests for /api/v1/mobile sync endpoints.
"""

import pytest
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

# Mock S3 presigned URL generation to avoid credential errors in tests
MOCK_S3_URL = "https://fake-s3-url.com/image.jpg"

@pytest.fixture(autouse=True)
def mock_s3_presigned_url():
    """
    Automatically patch generate_presigned_url in mobile_sync service
    to return a dummy URL instead of calling real AWS S3.
    
    This prevents botocore.exceptions.NoCredentialsError in test environment.
    """
    with patch('app.services.mobile_sync.generate_presigned_url', return_value=MOCK_S3_URL) as mock_url:
        yield mock_url


class TestSyncDataEndpoint:
    """GET /api/v1/mobile/sync/data"""

    def test_sync_data_success(self, client, patient_headers, seed_patient, seed_image, seed_report, db):
        """Should return all user-specific data."""
        response = client.get("/api/v1/mobile/sync/data", headers=patient_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "user" in data
        assert "images" in data
        assert "reports" in data
        assert "history" in data
        assert "synced_at" in data
        
        # Check user data
        assert data["user"]["user_id"] == seed_patient.user_id
        assert data["user"]["email"] == "patient@test.com"
        assert data["user"]["full_name"] == "Test Patient"
        
        # Check images
        assert len(data["images"]) >= 1
        assert data["images"][0]["image_id"] == seed_image.image_id
        assert "s3_url" in data["images"][0]
        
        # Check reports
        assert len(data["reports"]) >= 1
        assert data["reports"][0]["report_id"] == seed_report.report_id
        assert data["reports"][0]["kl_grade"] == seed_report.kl_grade

    def test_sync_data_no_auth(self, client):
        """Should require authentication."""
        response = client.get("/api/v1/mobile/sync/data")
        assert response.status_code == 401


class TestSyncSummaryEndpoint:
    """GET /api/v1/mobile/sync/summary"""

    def test_sync_summary_success(self, client, patient_headers, seed_patient, seed_image, seed_report, db):
        """Should return data counts."""
        response = client.get("/api/v1/mobile/sync/summary", headers=patient_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_id"] == seed_patient.user_id
        assert "images_count" in data
        assert "reports_count" in data
        assert "history_count" in data
        assert "total_records" in data
        assert data["total_records"] >= 2

    def test_sync_summary_no_auth(self, client):
        """Should require authentication."""
        response = client.get("/api/v1/mobile/sync/summary")
        assert response.status_code == 401


class TestExportUserDataEndpoint:
    """POST /api/v1/mobile/sync/export"""

    def test_export_user_data_success(self, client, patient_headers, seed_patient, seed_image, seed_report, db):
        """Should return JSON file with user data."""
        response = client.post("/api/v1/mobile/sync/export", headers=patient_headers)
        
        assert response.status_code == 200
        assert response.headers["Content-Disposition"] == "attachment; filename=user_data.json"
        assert response.headers["Content-Type"] == "application/json"
        
        # Verify JSON is valid
        data = response.json()
        assert "user" in data
        assert "images" in data
        assert "reports" in data

    def test_export_user_data_no_auth(self, client):
        """Should require authentication."""
        response = client.post("/api/v1/mobile/sync/export")
        assert response.status_code == 401


class TestSyncStatusEndpoint:
    """GET /api/v1/mobile/sync/status"""

    def test_sync_status_success(self, client, patient_headers, seed_patient, seed_image, seed_report, db):
        """Should return sync status."""
        response = client.get("/api/v1/mobile/sync/status", headers=patient_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_id"] == seed_patient.user_id
        assert data["available"] is True
        assert "images_count" in data
        assert "reports_count" in data

    def test_sync_status_no_auth(self, client):
        """Should require authentication."""
        response = client.get("/api/v1/mobile/sync/status")
        assert response.status_code == 401


class TestMobileSyncService:
    """Tests for MobileSyncService class"""

    def test_get_user_data(self, client, patient_headers, seed_patient, seed_image, seed_report, db):
        """Service should gather all user data correctly."""
        from app.services.mobile_sync import MobileSyncService
        
        service = MobileSyncService(db, seed_patient.user_id)
        user_data = service.get_user_data()
        
        # Check all sections present
        assert "user" in user_data
        assert "images" in user_data
        assert "reports" in user_data
        assert "history" in user_data
        assert "synced_at" in user_data
        
        # Check user data
        assert user_data["user"]["user_id"] == seed_patient.user_id
        assert user_data["user"]["email"] == "patient@test.com"
        
        # Check images
        assert len(user_data["images"]) >= 1
        assert user_data["images"][0]["image_id"] == seed_image.image_id
        
        # Check reports
        assert len(user_data["reports"]) >= 1
        assert user_data["reports"][0]["report_id"] == seed_report.report_id

    def test_get_user_data_user_not_found(self, db):
        """Service should raise error if user not found."""
        from app.services.mobile_sync import MobileSyncService
        
        service = MobileSyncService(db, 99999)
        
        with pytest.raises(ValueError, match="User 99999 not found"):
            service.get_user_data()

    def test_get_sync_summary(self, client, patient_headers, seed_patient, seed_image, seed_report, db):
        """Service should return correct counts."""
        from app.services.mobile_sync import MobileSyncService
        
        service = MobileSyncService(db, seed_patient.user_id)
        summary = service.get_sync_summary()
        
        assert summary["user_id"] == seed_patient.user_id
        assert summary["images_count"] >= 1
        assert summary["reports_count"] >= 1
        assert summary["total_records"] >= 2

    def test_export_to_json(self, client, patient_headers, seed_patient, seed_image, seed_report, db):
        """Service should export valid JSON."""
        from app.services.mobile_sync import MobileSyncService
        
        service = MobileSyncService(db, seed_patient.user_id)
        json_str = service.export_to_json()
        
        # Should be valid JSON
        data = json.loads(json_str)
        assert "user" in data
        assert "images" in data
        assert "reports" in data

    def test_export_to_json_with_path(self, tmp_path, client, patient_headers, seed_patient, seed_image, seed_report, db):
        """Service should save JSON to file if path provided."""
        from app.services.mobile_sync import MobileSyncService
        
        service = MobileSyncService(db, seed_patient.user_id)
        output_path = tmp_path / "user_data.json"
        
        result = service.export_to_json(str(output_path))
        
        # File should be created
        assert output_path.exists()
        
        # Should return JSON string
        assert isinstance(result, str)
        assert len(result) > 0

    def test_create_mobile_db(self, tmp_path, client, patient_headers, seed_patient, seed_image, seed_report, db):
        """Service should create SQLite database with user data."""
        from app.services.mobile_sync import MobileSyncService
        
        service = MobileSyncService(db, seed_patient.user_id)
        db_path = str(tmp_path / "mobile.db")
        
        service.create_mobile_db(db_path)
        
        # Database file should exist
        assert Path(db_path).exists()
        
        # Connect and verify tables
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        assert "user_profile" in tables
        assert "images" in tables
        assert "reports" in tables
        assert "profile_history" in tables
        
        # Check data
        cursor.execute("SELECT COUNT(*) FROM user_profile")
        assert cursor.fetchone()[0] == 1
        
        cursor.execute("SELECT COUNT(*) FROM images")
        assert cursor.fetchone()[0] >= 1
        
        cursor.execute("SELECT COUNT(*) FROM reports")
        assert cursor.fetchone()[0] >= 1
        
        conn.close()

    def test_sync_user_data_function(self, client, patient_headers, seed_patient, seed_image, seed_report, db):
        """Convenience function should work correctly."""
        from app.services.mobile_sync import sync_user_data
        
        json_str = sync_user_data(db, seed_patient.user_id)
        
        # Should return JSON string
        data = json.loads(json_str)
        assert "user" in data
        assert "images" in data


class TestMobileSyncWithProfileHistory:
    """Test mobile sync with profile change history."""

    def test_sync_includes_profile_history(self, client, patient_headers, seed_patient, db):
        """Sync should include profile change history."""
        from app.models.profile_log import ProfileLog
        
        # Create some profile history
        log1 = ProfileLog(
            user_id=seed_patient.user_id,
            field_name="pain_level",
            old_value="3",
            new_value="6",
        )
        log2 = ProfileLog(
            user_id=seed_patient.user_id,
            field_name="mobility_level",
            old_value="good",
            new_value="moderate",
        )
        db.add(log1)
        db.add(log2)
        db.commit()
        
        # Sync data
        response = client.get("/api/v1/mobile/sync/data", headers=patient_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Should have history entries
        assert len(data["history"]) >= 2
        
        # Check history data
        field_names = {log["field_name"] for log in data["history"]}
        assert "pain_level" in field_names
        assert "mobility_level" in field_names


class TestMobileSyncRBAC:
    """Test RBAC for mobile sync endpoints."""

    def test_patient_can_sync_own_data(self, client, patient_headers, seed_patient, seed_image, seed_report, db):
        """Patients should be able to sync their own data."""
        response = client.get("/api/v1/mobile/sync/data", headers=patient_headers)
        assert response.status_code == 200

    def test_gp_can_sync_own_data(self, client, gp_headers, seed_gp, db):
        """GPs should be able to sync their own data."""
        response = client.get("/api/v1/mobile/sync/data", headers=gp_headers)
        assert response.status_code == 200

    def test_admin_cannot_sync(self, client, admin_headers, seed_admin, db):
        """Admins should NOT be able to sync (only patient/gp)."""
        response = client.get("/api/v1/mobile/sync/data", headers=admin_headers)
        assert response.status_code == 403

    def test_patient_cannot_sync_others_data(self, client, patient_headers, seed_patient, seed_gp, seed_image, seed_report, db):
        """Patients should only see their own data."""
        # Get data as patient
        response = client.get("/api/v1/mobile/sync/data", headers=patient_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Should only contain patient's data
        assert data["user"]["user_id"] == seed_patient.user_id
        assert data["user"]["email"] == "patient@test.com"

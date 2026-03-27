"""
Tests for /api/v1/diagnostic — Analyze, Reports
"""

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestAnalyzeXray:
    """POST /api/v1/diagnostic/analyze"""

    @patch("app.api.v1.diagnostic.upload_bytes_to_s3", new_callable=AsyncMock)
    @patch("app.api.v1.diagnostic.generate_recommendation")
    @patch("app.api.v1.diagnostic.predict_kl_grade")
    @patch("app.api.v1.diagnostic.get_processed_image_bytes")
    @patch("app.api.v1.diagnostic.requests")
    def test_analyze_success(
        self, mock_requests, mock_proc, mock_predict, mock_rec, mock_s3,
        client, patient_headers, seed_image,
    ):
        # Mock S3 download
        mock_response = MagicMock()
        mock_response.content = b"\x89PNG" + b"\x00" * 100
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        # Mock CNN prediction
        mock_predict.return_value = (2, 0.87, "Grade 2 — Minimal OA")

        # Mock image processor
        mock_proc.return_value = b"\x89PNG_processed"

        # Mock S3 upload of processed image
        mock_s3.return_value = "https://bucket.s3.amazonaws.com/processed/1_processed.png"

        # Mock recommendation agent
        mock_rec.return_value = {
            "recommendation": "Stay active with low-impact exercises.",
            "exercise_video_urls": ["https://s3.amazonaws.com/videos/v1.mp4"],
        }

        response = client.post(
            "/api/v1/diagnostic/analyze",
            json={"image_id": seed_image.image_id, "pain_level": 5, "mobility_level": "moderate"},
            headers=patient_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["kl_grade"] == 2
        assert data["confidence"] == 0.87
        assert "Grade 2" in data["diagnosis_summary"]
        assert "Stay active" in data["recommendation"]
        assert len(data["exercise_video_urls"]) == 1
        assert data["image_id"] == seed_image.image_id

    def test_analyze_image_not_found(self, client, patient_headers, seed_patient):
        response = client.post(
            "/api/v1/diagnostic/analyze",
            json={"image_id": 9999},
            headers=patient_headers,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Image not found"

    def test_analyze_no_auth(self, client, seed_image):
        response = client.post(
            "/api/v1/diagnostic/analyze",
            json={"image_id": seed_image.image_id},
        )
        assert response.status_code == 401

    def test_analyze_admin_forbidden(self, client, admin_headers, seed_image, seed_admin):
        response = client.post(
            "/api/v1/diagnostic/analyze",
            json={"image_id": seed_image.image_id},
            headers=admin_headers,
        )
        assert response.status_code == 403

    def test_analyze_duplicate_report(self, client, patient_headers, seed_report, seed_image):
        """Should reject if a report already exists for this image."""
        response = client.post(
            "/api/v1/diagnostic/analyze",
            json={"image_id": seed_image.image_id},
            headers=patient_headers,
        )
        assert response.status_code == 400
        assert "report already exists" in response.json()["detail"]

    def test_analyze_patient_cannot_access_others_image(
        self, client, gp_headers, seed_gp, db
    ):
        """A patient should not be able to analyze another user's image."""
        from app.models.image import Image
        from app.models.user import User
        from app.core.security import get_password_hash, create_access_token

        # Create a second patient
        other = User(
            email="other@test.com",
            full_name="Other Patient",
            password_hash=get_password_hash("pass"),
            role="patient",
        )
        db.add(other)
        db.commit()
        db.refresh(other)

        # Image belongs to the GP
        img = Image(
            user_id=seed_gp.user_id,
            s3_url="https://bucket.s3.amazonaws.com/xrays/gp.png",
            file_name="gp.png",
        )
        db.add(img)
        db.commit()
        db.refresh(img)

        # Other patient tries to analyze GP's image
        other_token = create_access_token(data={"sub": other.email, "role": other.role})
        other_headers = {"Authorization": f"Bearer {other_token}"}

        response = client.post(
            "/api/v1/diagnostic/analyze",
            json={"image_id": img.image_id},
            headers=other_headers,
        )
        assert response.status_code == 403


class TestGetReports:
    """GET /api/v1/diagnostic/reports"""

    def test_get_reports_empty(self, client, patient_headers, seed_patient):
        response = client.get("/api/v1/diagnostic/reports", headers=patient_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_get_reports_with_data(self, client, patient_headers, seed_report):
        response = client.get("/api/v1/diagnostic/reports", headers=patient_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["kl_grade"] == 2
        assert data[0]["confidence"] == 0.87

    def test_get_reports_no_auth(self, client):
        response = client.get("/api/v1/diagnostic/reports")
        assert response.status_code == 401


class TestGetReportById:
    """GET /api/v1/diagnostic/reports/{report_id}"""

    def test_get_report_success(self, client, patient_headers, seed_report):
        response = client.get(
            f"/api/v1/diagnostic/reports/{seed_report.report_id}",
            headers=patient_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["report_id"] == seed_report.report_id
        assert data["kl_grade"] == 2

    def test_get_report_not_found(self, client, patient_headers, seed_patient):
        response = client.get(
            "/api/v1/diagnostic/reports/9999",
            headers=patient_headers,
        )
        assert response.status_code == 404

    def test_get_report_access_denied(self, client, seed_report, db):
        """Another patient should not see someone else's report."""
        from app.models.user import User
        from app.core.security import get_password_hash, create_access_token

        other = User(
            email="other2@test.com",
            full_name="Other",
            password_hash=get_password_hash("pass"),
            role="patient",
        )
        db.add(other)
        db.commit()

        token = create_access_token(data={"sub": other.email, "role": "patient"})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            f"/api/v1/diagnostic/reports/{seed_report.report_id}",
            headers=headers,
        )
        assert response.status_code == 403

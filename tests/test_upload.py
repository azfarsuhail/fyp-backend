"""
Tests for /api/v1/upload — X-ray Image Upload
"""

import io
import pytest
from unittest.mock import patch, AsyncMock


class TestUploadXray:
    """POST /api/v1/upload/"""

    @patch("app.api.v1.upload.upload_file_to_s3", new_callable=AsyncMock)
    def test_upload_success(self, mock_s3, client, patient_headers, seed_patient):
        mock_s3.return_value = "https://test-bucket.s3.amazonaws.com/xrays/abc123.png"

        file_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # Fake PNG bytes
        response = client.post(
            "/api/v1/upload/",
            files={"file": ("test_xray.png", io.BytesIO(file_content), "image/png")},
            headers=patient_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["file_name"] == "test_xray.png"
        assert data["s3_url"] == "https://test-bucket.s3.amazonaws.com/xrays/abc123.png"
        assert data["user_id"] == seed_patient.user_id
        mock_s3.assert_called_once()

    @patch("app.api.v1.upload.upload_file_to_s3", new_callable=AsyncMock)
    def test_upload_jpeg(self, mock_s3, client, patient_headers, seed_patient):
        mock_s3.return_value = "https://test-bucket.s3.amazonaws.com/xrays/abc.jpg"

        response = client.post(
            "/api/v1/upload/",
            files={"file": ("xray.jpg", io.BytesIO(b"\xff\xd8\xff" + b"\x00" * 100), "image/jpeg")},
            headers=patient_headers,
        )
        assert response.status_code == 201

    def test_upload_invalid_file_type(self, client, patient_headers, seed_patient):
        response = client.post(
            "/api/v1/upload/",
            files={"file": ("doc.pdf", io.BytesIO(b"fake pdf"), "application/pdf")},
            headers=patient_headers,
        )
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_upload_no_auth(self, client):
        response = client.post(
            "/api/v1/upload/",
            files={"file": ("test.png", io.BytesIO(b"\x00" * 10), "image/png")},
        )
        assert response.status_code == 401

    def test_upload_admin_forbidden(self, client, admin_headers, seed_admin):
        """Admins should NOT be able to upload X-rays (only patient/gp)."""
        response = client.post(
            "/api/v1/upload/",
            files={"file": ("test.png", io.BytesIO(b"\x00" * 10), "image/png")},
            headers=admin_headers,
        )
        assert response.status_code == 403

    @patch("app.api.v1.upload.upload_file_to_s3", new_callable=AsyncMock)
    def test_upload_gp_allowed(self, mock_s3, client, gp_headers, seed_gp):
        mock_s3.return_value = "https://test-bucket.s3.amazonaws.com/xrays/gp.png"

        response = client.post(
            "/api/v1/upload/",
            files={"file": ("gp_xray.png", io.BytesIO(b"\x89PNG" + b"\x00" * 100), "image/png")},
            headers=gp_headers,
        )
        assert response.status_code == 201

    @patch("app.api.v1.upload.upload_file_to_s3", new_callable=AsyncMock)
    def test_upload_s3_failure(self, mock_s3, client, patient_headers, seed_patient):
        mock_s3.side_effect = RuntimeError("S3 connection failed")

        response = client.post(
            "/api/v1/upload/",
            files={"file": ("test.png", io.BytesIO(b"\x89PNG" + b"\x00" * 100), "image/png")},
            headers=patient_headers,
        )
        assert response.status_code == 500
        assert "S3 connection failed" in response.json()["detail"]

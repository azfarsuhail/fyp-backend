"""
Tests for app/services/s3_service.py — endpoint selection for presigned URLs
"""

from app.services import s3_service


def _fake_creds(monkeypatch):
    monkeypatch.setattr(s3_service, "AWS_ACCESS_KEY_ID", "test-key")
    monkeypatch.setattr(s3_service, "AWS_SECRET_ACCESS_KEY", "test-secret")


def test_presigned_url_uses_public_endpoint(monkeypatch):
    """Offline/MinIO: URLs must point at the host clients can reach, path-style."""
    _fake_creds(monkeypatch)
    monkeypatch.setattr(s3_service, "S3_PUBLIC_ENDPOINT_URL", "http://localhost:9000")

    url = s3_service.generate_presigned_url("xrays/a.png")

    assert url.startswith(f"http://localhost:9000/{s3_service.S3_BUCKET_NAME}/xrays/a.png?")
    assert "X-Amz-Signature=" in url


def test_presigned_url_defaults_to_aws(monkeypatch):
    """No endpoint configured: unchanged AWS S3 behaviour."""
    _fake_creds(monkeypatch)
    monkeypatch.setattr(s3_service, "S3_PUBLIC_ENDPOINT_URL", None)

    url = s3_service.generate_presigned_url("xrays/a.png")

    assert url.startswith("https://") and "amazonaws.com" in url

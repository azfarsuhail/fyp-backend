"""
Tests for /api/v1/recommendation — Standalone Recommendation Endpoint
"""

import pytest
from unittest.mock import patch


class TestGetRecommendation:
    """GET /api/v1/recommendation/"""

    @patch("app.api.v1.recommendation.generate_recommendation")
    def test_recommendation_success(self, mock_rec, client, patient_headers, seed_patient):
        mock_rec.return_value = {
            "recommendation": "Stay active with low-impact exercises.",
            "exercise_video_urls": ["https://s3.amazonaws.com/videos/v1.mp4"],
        }

        response = client.get(
            "/api/v1/recommendation/?kl_grade=2&pain_level=5&mobility_level=moderate",
            headers=patient_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "Stay active" in data["recommendation"]
        assert len(data["exercise_video_urls"]) == 1

    @patch("app.api.v1.recommendation.generate_recommendation")
    def test_recommendation_minimal_params(self, mock_rec, client, patient_headers, seed_patient):
        """Only kl_grade is required."""
        mock_rec.return_value = {
            "recommendation": "General advice for grade 0.",
            "exercise_video_urls": [],
        }

        response = client.get(
            "/api/v1/recommendation/?kl_grade=0",
            headers=patient_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "General advice" in data["recommendation"]

    def test_recommendation_missing_kl_grade(self, client, patient_headers, seed_patient):
        response = client.get(
            "/api/v1/recommendation/",
            headers=patient_headers,
        )
        assert response.status_code == 422  # kl_grade is required

    @patch("app.api.v1.recommendation.generate_recommendation")
    def test_recommendation_invalid_kl_grade(self, mock_rec, client, patient_headers, seed_patient):
        response = client.get(
            "/api/v1/recommendation/?kl_grade=7",
            headers=patient_headers,
        )
        assert response.status_code == 400
        assert "KL grade must be between 0 and 4" in response.json()["detail"]

    def test_recommendation_no_auth(self, client):
        response = client.get("/api/v1/recommendation/?kl_grade=2")
        assert response.status_code == 401

    def test_recommendation_admin_forbidden(self, client, admin_headers, seed_admin):
        response = client.get(
            "/api/v1/recommendation/?kl_grade=2",
            headers=admin_headers,
        )
        assert response.status_code == 403

    @patch("app.api.v1.recommendation.generate_recommendation")
    def test_recommendation_gp_allowed(self, mock_rec, client, gp_headers, seed_gp):
        mock_rec.return_value = {
            "recommendation": "GP advice.",
            "exercise_video_urls": [],
        }

        response = client.get(
            "/api/v1/recommendation/?kl_grade=3",
            headers=gp_headers,
        )
        assert response.status_code == 200

    @patch("app.api.v1.recommendation.generate_recommendation")
    def test_recommendation_agent_failure(self, mock_rec, client, patient_headers, seed_patient):
        mock_rec.side_effect = Exception("Model loading failed")

        response = client.get(
            "/api/v1/recommendation/?kl_grade=2",
            headers=patient_headers,
        )
        assert response.status_code == 500
        assert "Recommendation generation failed" in response.json()["detail"]

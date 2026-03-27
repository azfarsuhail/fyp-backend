"""
Tests for /api/v1/videos — Exercise Video Library CRUD
"""

import pytest


class TestListVideos:
    """GET /api/v1/videos/"""

    def test_list_videos_empty(self, client, patient_headers, seed_patient):
        response = client.get("/api/v1/videos/", headers=patient_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_videos_with_data(self, client, patient_headers, seed_video, seed_patient):
        response = client.get("/api/v1/videos/", headers=patient_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Gentle Knee Stretches"
        assert data[0]["category"] == "flexibility"

    def test_list_videos_filter_by_kl_grade(self, client, patient_headers, seed_video, seed_patient):
        # kl_grade=1 should match (video covers 0-2)
        response = client.get("/api/v1/videos/?kl_grade=1", headers=patient_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

        # kl_grade=4 should NOT match (video covers 0-2)
        response = client.get("/api/v1/videos/?kl_grade=4", headers=patient_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_list_videos_filter_by_category(self, client, patient_headers, seed_video, seed_patient):
        response = client.get("/api/v1/videos/?category=flexibility", headers=patient_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = client.get("/api/v1/videos/?category=strengthening", headers=patient_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_list_videos_no_auth(self, client):
        response = client.get("/api/v1/videos/")
        assert response.status_code == 401


class TestGetVideo:
    """GET /api/v1/videos/{video_id}"""

    def test_get_video_success(self, client, patient_headers, seed_video, seed_patient):
        response = client.get(
            f"/api/v1/videos/{seed_video.video_id}",
            headers=patient_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Gentle Knee Stretches"
        assert data["duration_seconds"] == 300

    def test_get_video_not_found(self, client, patient_headers, seed_patient):
        response = client.get("/api/v1/videos/9999", headers=patient_headers)
        assert response.status_code == 404


class TestCreateVideo:
    """POST /api/v1/videos/ (Admin only)"""

    def test_create_video_admin(self, client, admin_headers, seed_admin):
        response = client.post(
            "/api/v1/videos/",
            json={
                "title": "Quad Strengthening",
                "description": "Build quad strength for knee support",
                "s3_url": "https://bucket.s3.amazonaws.com/videos/quads.mp4",
                "kl_grade_min": 1,
                "kl_grade_max": 3,
                "category": "strengthening",
                "difficulty": "intermediate",
                "duration_seconds": 600,
            },
            headers=admin_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Quad Strengthening"
        assert data["category"] == "strengthening"
        assert data["difficulty"] == "intermediate"
        assert "video_id" in data

    def test_create_video_patient_forbidden(self, client, patient_headers, seed_patient):
        response = client.post(
            "/api/v1/videos/",
            json={
                "title": "Hack Video",
                "s3_url": "https://evil.com/hack.mp4",
                "kl_grade_min": 0,
                "kl_grade_max": 4,
                "category": "hacking",
            },
            headers=patient_headers,
        )
        assert response.status_code == 403

    def test_create_video_gp_forbidden(self, client, gp_headers, seed_gp):
        response = client.post(
            "/api/v1/videos/",
            json={
                "title": "GP Video",
                "s3_url": "https://bucket.s3.amazonaws.com/gp.mp4",
                "kl_grade_min": 0,
                "kl_grade_max": 2,
                "category": "flexibility",
            },
            headers=gp_headers,
        )
        assert response.status_code == 403

    def test_create_video_missing_fields(self, client, admin_headers, seed_admin):
        response = client.post(
            "/api/v1/videos/",
            json={"title": "Incomplete"},
            headers=admin_headers,
        )
        assert response.status_code == 422


class TestUpdateVideo:
    """PUT /api/v1/videos/{video_id} (Admin only)"""

    def test_update_video_admin(self, client, admin_headers, seed_video, seed_admin):
        response = client.put(
            f"/api/v1/videos/{seed_video.video_id}",
            json={
                "title": "Updated Stretches",
                "s3_url": seed_video.s3_url,
                "kl_grade_min": 0,
                "kl_grade_max": 3,
                "category": "flexibility",
                "difficulty": "intermediate",
            },
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Stretches"
        assert data["kl_grade_max"] == 3
        assert data["difficulty"] == "intermediate"

    def test_update_video_not_found(self, client, admin_headers, seed_admin):
        response = client.put(
            "/api/v1/videos/9999",
            json={
                "title": "Ghost",
                "s3_url": "https://x.com/x.mp4",
                "kl_grade_min": 0,
                "kl_grade_max": 4,
                "category": "none",
            },
            headers=admin_headers,
        )
        assert response.status_code == 404

    def test_update_video_patient_forbidden(self, client, patient_headers, seed_video, seed_patient):
        response = client.put(
            f"/api/v1/videos/{seed_video.video_id}",
            json={
                "title": "Hacked",
                "s3_url": "https://evil.com/x.mp4",
                "kl_grade_min": 0,
                "kl_grade_max": 4,
                "category": "hack",
            },
            headers=patient_headers,
        )
        assert response.status_code == 403


class TestDeleteVideo:
    """DELETE /api/v1/videos/{video_id} (Admin only)"""

    def test_delete_video_admin(self, client, admin_headers, seed_video, seed_admin):
        response = client.delete(
            f"/api/v1/videos/{seed_video.video_id}",
            headers=admin_headers,
        )
        assert response.status_code == 204

        # Verify it's gone
        get_resp = client.get(
            f"/api/v1/videos/{seed_video.video_id}",
            headers=admin_headers,
        )
        assert get_resp.status_code == 404

    def test_delete_video_not_found(self, client, admin_headers, seed_admin):
        response = client.delete("/api/v1/videos/9999", headers=admin_headers)
        assert response.status_code == 404

    def test_delete_video_patient_forbidden(self, client, patient_headers, seed_video, seed_patient):
        response = client.delete(
            f"/api/v1/videos/{seed_video.video_id}",
            headers=patient_headers,
        )
        assert response.status_code == 403

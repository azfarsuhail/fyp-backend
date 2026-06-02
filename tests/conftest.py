"""
Test Configuration & Fixtures
------------------------------
Sets up an in-memory SQLite database for testing so we never touch Neon DB.
Provides reusable fixtures for the test client, DB sessions, and authenticated users.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Base
from app.core.dependencies import get_db, get_current_user
from app.core.security import get_password_hash, create_access_token
from app.main import app

# ── In-memory SQLite for tests ───────────────────────────────────────────────
SQLALCHEMY_TEST_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Override the DB dependency ───────────────────────────────────────────────
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test, drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Provide a clean DB session for direct model manipulation in tests."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """FastAPI TestClient with DB override."""
    return TestClient(app)


@pytest.fixture
def seed_patient(db):
    """Create a patient user in the test DB and return their data."""
    from app.models.user import User

    user = User(
        email="patient@test.com",
        full_name="Test Patient",
        password_hash=get_password_hash("SecurePass123!@#"),
        role="patient",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def seed_gp(db):
    """Create a GP user in the test DB."""
    from app.models.user import User

    user = User(
        email="gp@test.com",
        full_name="Test GP",
        password_hash=get_password_hash("SecurePass123!@#"),
        role="gp",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def seed_admin(db):
    """Create an admin user in the test DB."""
    from app.models.user import User

    user = User(
        email="admin@test.com",
        full_name="Test Admin",
        password_hash=get_password_hash("SecurePass123!@#"),
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def seed_admin(db):
    """Create an admin user in the test DB."""
    from app.models.user import User

    user = User(
        email="admin@test.com",
        full_name="Test Admin",
        password_hash=get_password_hash("SecurePass123!@#"),
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_header(email: str, role: str) -> dict:
    """Generate a Bearer token header for a given user."""
    token = create_access_token(data={"sub": email, "role": role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def patient_headers(seed_patient):
    """Auth headers for the patient user."""
    return _auth_header(seed_patient.email, seed_patient.role)


@pytest.fixture
def gp_headers(seed_gp):
    """Auth headers for the GP user."""
    return _auth_header(seed_gp.email, seed_gp.role)


@pytest.fixture
def admin_headers(seed_admin):
    """Auth headers for the admin user."""
    return _auth_header(seed_admin.email, seed_admin.role)


@pytest.fixture
def seed_image(db, seed_patient):
    """Create a test image record in the DB."""
    from app.models.image import Image
    image = Image(
        user_id=seed_patient.user_id,
        s3_url="xrays/test.png",
        file_name="test_xray.png",
        content_type="image/png",
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@pytest.fixture
def seed_report(db, seed_image, seed_patient):
    """Create a test report record in the DB."""
    import json
    from app.models.report import Report

    report = Report(
        image_id=seed_image.image_id,
        user_id=seed_patient.user_id,
        kl_grade=2,
        confidence=0.87,
        diagnosis_summary="Grade 2 — Minimal OA",
        recommendation="Test recommendation text",
        lifestyle_plan=json.dumps([
            {"id": "EX-001", "category": "exercise", "action": "Walk daily",
             "evidence_level": "strong", "source": "OARSI 2019"}
        ]),
        warnings=json.dumps([
            {"level": "caution", "message": "Avoid high-impact activities."}
        ]),
        exercise_video_urls=json.dumps(["https://s3.amazonaws.com/videos/v1.mp4"]),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@pytest.fixture
def seed_video(db):
    """Create a test exercise video in the DB."""
    from app.models.library import ExerciseVideo

    video = ExerciseVideo(
        title="Gentle Knee Stretches",
        description="Low-impact stretching for KL Grade 1-2",
        s3_url="videos/stretch.mp4",
        thumbnail_url="thumbs/stretch.jpg",
        kl_grade_min=0,
        kl_grade_max=2,
        category="flexibility",
        difficulty="beginner",
        duration_seconds=300,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video

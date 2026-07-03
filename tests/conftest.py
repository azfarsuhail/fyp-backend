"""
Test Configuration & Fixtures
------------------------------
Uses Nested Transaction (Savepoint) pattern for complete database isolation.
Each test runs in a connection-level transaction with nested savepoints.
FastAPI TestClient and fixtures share the exact same session.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# ── Import ALL models BEFORE creating engine to ensure they're registered ────
# This is critical for SQLite in-memory databases to recognize all tables
# Import each model individually to ensure they're all registered with Base
from app.models.user import User
from app.models.image import Image
from app.models.report import Report
from app.models.library import ExerciseVideo
from app.models.medication import MedicationModel
from app.models.profile_log import ProfileLog
from app.models.otp_verification import OTPVerification
from app.core.config import Base
from app.core.dependencies import get_db
from app.core.security import get_password_hash, create_access_token
from app.main import app

# ── Test Database Engine ─────────────────────────────────────────────────────
SQLALCHEMY_TEST_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# ── Create tables at module level (runs once when conftest is loaded) ─────────
# This ensures all tables exist before any tests run
Base.metadata.create_all(bind=engine)


# ── Session-scoped fixture to ensure tables are created once per test session ─
@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Create all tables once at the start of the test session.
    This is critical for SQLite in-memory databases which are connection-specific.
    """
    # Ensure all models are imported before creating tables
    # (Already done at module level above)
    Base.metadata.create_all(bind=engine)
    yield

# ── Global fixture to reset rate limiter state between tests ──────────────────
@pytest.fixture(autouse=True, scope="function")
def reset_rate_limiter():
    """
    Reset rate limiter state before every test to prevent state bleed.
    This clears all attempt tracking data across all endpoints.
    """
    from app.core.security_middleware import auth_rate_limiter
    
    # Clear all attempt tracking data
    with auth_rate_limiter._lock:
        auth_rate_limiter.attempts.clear()
    
    yield
    
    # Cleanup after test (clear again to ensure clean state)
    with auth_rate_limiter._lock:
        auth_rate_limiter.attempts.clear()

# ── Database Session Fixture with Nested Transaction (Savepoint) ──────────────
@pytest.fixture(scope="function")
def db():
    """
    Create a database session with connection-level transaction and nested savepoint.
    
    This pattern allows:
    1. FastAPI and fixtures to share the EXACT same session
    2. Application code to call commit() safely (commits to savepoint)
    3. Automatic rollback of all changes after each test
    4. No database state leakage between tests
    
    The event listener restarts the savepoint if the app calls commit().
    """
    # Create connection and outer transaction
    connection = engine.connect()
    transaction = connection.begin()
    
    # Create session bound to the connection
    session = Session(bind=connection)
    
    # Begin nested transaction (savepoint)
    session.begin_nested()
    
    # Event listener to restart savepoint if app calls commit()
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        # Only restart if this is a nested transaction and parent is not nested
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()
    
    try:
        yield session
        
        # Commit the savepoint (will be rolled back when test ends)
        session.commit()
        
    finally:
        # Clean up: rollback outer transaction (discards everything)
        transaction.rollback()
        session.close()
        connection.close()


# ── Client Fixture with Dependency Override ───────────────────────────────────
@pytest.fixture(scope="function")
def client(db):
    """
    Create FastAPI TestClient that uses the SAME session as the db fixture.
    
    This ensures that when fixtures create data, the API can see it immediately,
    and when the test ends, everything is rolled back together.
    """
    def override_get_db():
        yield db
    
    # Override FastAPI's get_db dependency
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client
    with TestClient(app) as c:
        yield c
    
    # Clean up overrides
    app.dependency_overrides.clear()


# ── User Seed Fixtures ────────────────────────────────────────────────────────
@pytest.fixture
def seed_patient(db, request):
    """
    Create a patient user in the test DB and return their data.
    Function-scoped to ensure each test gets its own isolated user.
    
    Always uses unique email based on test function name to prevent
    duplicate creation errors when multiple tests use this fixture.
    """
    from app.models.user import User

    # Always use test function name for uniqueness (works for both sequential and parallel)
    test_name = request.node.name if hasattr(request, 'node') else 'test'
    worker_id = getattr(pytest, 'workerid', '') if hasattr(pytest, 'workerid') else ''
    suffix = f"{test_name}_{worker_id}" if worker_id else test_name
    
    user = User(
        email=f"patient_{suffix}@test.com",
        full_name="Test Patient",
        password_hash=get_password_hash("SecurePass123!@#"),
        role="patient",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def seed_gp(db, request):
    """
    Create a GP user in the test DB.
    Function-scoped to ensure each test gets its own isolated user.
    
    Always uses unique email based on test function name to prevent
    duplicate creation errors when multiple tests use this fixture.
    """
    from app.models.user import User

    # Always use test function name for uniqueness
    test_name = request.node.name if hasattr(request, 'node') else 'test'
    worker_id = getattr(pytest, 'workerid', '') if hasattr(pytest, 'workerid') else ''
    suffix = f"{test_name}_{worker_id}" if worker_id else test_name
    
    user = User(
        email=f"gp_{suffix}@test.com",
        full_name="Test GP",
        password_hash=get_password_hash("SecurePass123!@#"),
        role="gp",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def seed_admin(db, request):
    """
    Create an admin user in the test DB.
    Function-scoped to ensure each test gets its own isolated user.
    
    Always uses unique email based on test function name to prevent
    duplicate creation errors when multiple tests use this fixture.
    """
    from app.models.user import User

    # Always use test function name for uniqueness
    test_name = request.node.name if hasattr(request, 'node') else 'test'
    worker_id = getattr(pytest, 'workerid', '') if hasattr(pytest, 'workerid') else ''
    suffix = f"{test_name}_{worker_id}" if worker_id else test_name
    
    user = User(
        email=f"admin_{suffix}@test.com",
        full_name="Test Admin",
        password_hash=get_password_hash("SecurePass123!@#"),
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── Authentication Header Fixtures ────────────────────────────────────────────
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


# ── Image and Report Seed Fixtures ───────────────────────────────────────────
@pytest.fixture
def seed_image(db, seed_patient, request):
    """
    Create a test image record in the DB.
    Function-scoped to ensure isolation between parallel tests.
    """
    from app.models.image import Image

    # Use test function name + worker ID for unique filename
    test_name = request.node.name if hasattr(request, 'node') else 'test'
    worker_id = getattr(pytest, 'workerid', 'gw0') if hasattr(pytest, 'workerid') else 'gw0'
    unique_suffix = f"{test_name}_{worker_id}"
    
    image = Image(
        user_id=seed_patient.user_id,
        s3_url=f"xrays/test_{unique_suffix}.png",
        file_name=f"test_xray_{unique_suffix}.png",
        content_type="image/png",
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@pytest.fixture
def seed_report(db, seed_image, seed_patient, request):
    """
    Create a test report record in the DB.
    Function-scoped to ensure isolation between parallel tests.
    """
    import json
    from app.models.report import Report

    # Use test function name + worker ID for unique URL
    test_name = request.node.name if hasattr(request, 'node') else 'test'
    worker_id = getattr(pytest, 'workerid', 'gw0') if hasattr(pytest, 'workerid') else 'gw0'
    unique_suffix = f"{test_name}_{worker_id}"
    
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
        exercise_video_urls=json.dumps([f"https://s3.amazonaws.com/videos/v1_{unique_suffix}.mp4"]),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


# ── Video Seed Fixture ────────────────────────────────────────────────────────
@pytest.fixture
def seed_video(db, request):
    """
    Create a test exercise video in the DB.
    Function-scoped to ensure isolation between parallel tests.
    Uses flush() instead of commit() for transactional rollback.
    """
    import uuid
    from app.models.library import ExerciseVideo

    # Use test function name + worker ID + UUID for maximum uniqueness
    test_name = request.node.name if hasattr(request, 'node') else 'test'
    worker_id = getattr(pytest, 'workerid', 'gw0') if hasattr(pytest, 'workerid') else 'gw0'
    unique_suffix = f"{test_name}_{worker_id}_{uuid.uuid4().hex[:8]}"
    
    video = ExerciseVideo(
        title=f"Gentle Knee Stretches_{unique_suffix}",
        description="Low-impact stretching for KL Grade 1-2",
        s3_url=f"videos/stretch_{unique_suffix}.mp4",
        thumbnail_url=f"thumbs/stretch_{unique_suffix}.jpg",
        kl_grade_min=0,
        kl_grade_max=2,
        category="flexibility",
        difficulty="beginner",
        duration_seconds=300,
    )
    db.add(video)
    db.flush()  # Use flush() instead of commit() for transactional isolation
    db.refresh(video)
    return video

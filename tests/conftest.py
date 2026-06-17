"""
Test Configuration & Fixtures
------------------------------
Sets up transactional isolation for pytest-xdist parallel test execution.
Each test runs in a nested transaction with automatic rollback to prevent
database state leakage between concurrent workers.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, event
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


# ── Transaction Stack for Nested Rollbacks ───────────────────────────────────
# Each thread gets its own stack of transaction/savepoint objects
_transaction_stack = {}


def get_transaction_stack():
    """Get or create a transaction stack for the current thread."""
    import threading
    if threading.current_thread() not in _transaction_stack:
        _transaction_stack[threading.current_thread()] = []
    return _transaction_stack[threading.current_thread()]


# ── Override the DB dependency with Transactional Isolation ──────────────────
@pytest.fixture(autouse=True)
def transactional_db(db):
    """
    Wrap each test in a nested transaction that rolls back after the test.
    This ensures complete isolation between parallel test executions.
    """
    # Begin a transaction
    trans = db.begin_nested()
    
    # Yield control to test
    yield db
    
    # Rollback the transaction (discards all changes)
    db.rollback()


# ── Module-level override for tests that don't use fixtures ──────────────────
# This ensures the override is set even before any fixtures run
def override_get_db():
    """Override for FastAPI dependency injection."""
    stack = get_transaction_stack()
    if stack:
        yield stack[-1]
    else:
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

app.dependency_overrides[get_db] = override_get_db


# ── Session Setup ────────────────────────────────────────────────────────────
@pytest.fixture(scope="session", autouse=True)
def setup_test_app():
    """Set up test app overrides once per session."""
    yield
    # Clean up overrides after all tests
    app.dependency_overrides.clear()


# ── Core Database Fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db():
    """
    Provide a database session bound to a nested transaction.
    The transaction automatically rolls back after each test, ensuring
    complete isolation between concurrent pytest-xdist workers.
    """
    import threading
    session = TestingSessionLocal()
    
    # Create tables if they don't exist (first time setup)
    Base.metadata.create_all(bind=engine)
    
    # Begin a nested transaction (savepoint) for this test
    trans = session.begin_nested()
    
    # Push transaction onto thread-local stack
    stack = get_transaction_stack()
    stack.append(session)
    
    try:
        yield session
    finally:
        # Pop from stack
        if stack:
            stack.pop()
        
        # Rollback to discard all changes (critical for isolation)
        session.rollback()
        session.close()


@pytest.fixture(scope="module", autouse=True)
def module_teardown():
    """Final cleanup after each test module."""
    yield
    # Clear transaction stacks for this thread
    import threading
    if threading.current_thread() in _transaction_stack:
        _transaction_stack[threading.current_thread()].clear()
    # Clean up engine
    session = TestingSessionLocal()
    session.close()


@pytest.fixture
def client():
    """FastAPI TestClient with DB override."""
    return TestClient(app)


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


@pytest.fixture
def seed_video(db, request):
    """
    Create a test exercise video in the DB.
    Function-scoped to ensure isolation between parallel tests.
    """
    from app.models.library import ExerciseVideo

    # Use test function name + worker ID for unique title
    test_name = request.node.name if hasattr(request, 'node') else 'test'
    worker_id = getattr(pytest, 'workerid', 'gw0') if hasattr(pytest, 'workerid') else 'gw0'
    unique_suffix = f"{test_name}_{worker_id}"
    
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
    db.commit()
    db.refresh(video)
    return video

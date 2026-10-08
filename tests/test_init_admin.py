"""
Tests for scripts/init_admin.py — default admin + demo GP/patient seeding
"""

from app.models.user import User
from app.core.security import verify_password
from scripts import init_admin


def _run(monkeypatch, db, seed_demo: str):
    monkeypatch.setenv("SEED_DEMO_USERS", seed_demo)
    # Fixture's connection, not the shared engine: create_all on the engine would
    # commit the outer transaction and leak rows into later tests.
    monkeypatch.setattr(init_admin, "engine", db.get_bind())
    monkeypatch.setattr(init_admin, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)  # the db fixture owns the session
    init_admin.init_default_users()


def _get(db, email):
    return db.query(User).filter(User.email == email).one_or_none()


def test_seeds_admin_gp_and_assigned_patient(monkeypatch, db):
    _run(monkeypatch, db, "1")

    admin, gp, patient = (_get(db, u["email"]) for u in (init_admin.ADMIN, init_admin.DEMO_GP, init_admin.DEMO_PATIENT))
    assert (admin.role, gp.role, patient.role) == ("admin", "gp", "patient")
    assert verify_password("gp123456", gp.password_hash)
    assert verify_password("patient123", patient.password_hash)
    assert patient.primary_gp_id == gp.user_id

    _run(monkeypatch, db, "1")  # idempotent: no duplicates, no errors
    assert db.query(User).filter(User.email.in_(["admin", gp.email, patient.email])).count() == 3


def test_demo_users_only_when_enabled(monkeypatch, db):
    _run(monkeypatch, db, "0")

    assert _get(db, "admin") is not None
    assert _get(db, init_admin.DEMO_GP["email"]) is None
    assert _get(db, init_admin.DEMO_PATIENT["email"]) is None

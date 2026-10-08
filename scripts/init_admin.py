"""
Initialize Default Accounts
---------------------------
Creates the initial admin user (admin/admin) in the database. With
SEED_DEMO_USERS=1 (set by docker-compose.offline.yml) it also creates a demo GP
and a demo patient assigned to that GP. Credentials: docs/docker/OFFLINE_SETUP.md.
Idempotent: existing accounts are left untouched.

Usage:
    python scripts/init_admin.py
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import Base, engine, SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

ADMIN = dict(email="admin", password="admin", full_name="System Administrator", role="admin")

# Demo accounts with published passwords: offline/local stack only, never production.
DEMO_GP = dict(email="gp@kneeoa.online", password="gp123456", full_name="Dr. Demo GP", role="gp")
DEMO_PATIENT = dict(
    email="patient@kneeoa.online", password="patient123", full_name="Demo Patient", role="patient",
    age=58, pain_level=5, mobility_level="moderate", has_support=True, kinesiophobia="moderate",
    occupation_type="sedentary", has_stairs=True, sleep_quality="fair",
)


def ensure_user(db, password: str, **fields) -> User:
    """Return the user with this email, creating it if missing."""
    user = db.query(User).filter(User.email == fields["email"]).first()
    if user:
        print(f"✓ {fields['role']:<7} already exists: {user.email} (user_id: {user.user_id})")
        return user
    user = User(password_hash=get_password_hash(password), **fields)
    db.add(user)
    db.commit()
    print(f"✓ {fields['role']:<7} created: {user.email} / {password} (user_id: {user.user_id})")
    return user


def init_default_users():
    """Create the default admin (and demo GP/patient if enabled) if they don't exist."""

    # Create any missing tables (fresh/offline DB; alembic/versions is not tracked).
    # No-op for tables that already exist. app.models registers every model on Base.
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        ensure_user(db, **ADMIN)
        if os.getenv("SEED_DEMO_USERS", "0") == "1":
            gp = ensure_user(db, **DEMO_GP)
            ensure_user(db, primary_gp_id=gp.user_id, **DEMO_PATIENT)
        print("\n⚠️  These are default passwords: change them on any shared deployment!")
    except Exception as e:
        db.rollback()
        print(f"✗ Error creating default accounts: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Initializing Default Accounts")
    print("=" * 60)
    init_default_users()

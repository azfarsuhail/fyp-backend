"""
Initialize Default Admin Account
---------------------------------
Creates the initial admin user (admin/admin) in the database.
Run this once after setting up the database.

Usage:
    python scripts/init_admin.py
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.config import engine, SessionLocal
from app.models.user import User
from app.core.security import get_password_hash


def init_default_admin():
    """Create default admin account if it doesn't exist."""
    
    # Database setup
    db = SessionLocal()
    
    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.email == "admin").first()
        if existing_admin:
            print(f"✓ Admin account already exists (user_id: {existing_admin.user_id})")
            return
        
        # Create default admin
        default_admin = User(
            email="admin",
            full_name="System Administrator",
            password_hash=get_password_hash("admin"),
            role="admin",
        )
        
        db.add(default_admin)
        db.commit()
        
        print("✓ Default admin account created successfully!")
        print(f"  Email: admin")
        print(f"  Password: admin")
        print(f"  User ID: {default_admin.user_id}")
        print("\n⚠️  IMPORTANT: Change the default password immediately after first login!")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error creating admin account: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Initializing Default Admin Account")
    print("=" * 60)
    init_default_admin()

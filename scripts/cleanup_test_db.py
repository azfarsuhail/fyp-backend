"""
Database Cleanup Script
-----------------------
Drops all tables and recreates them to wipe out leaked test data.
Run this once before running the test suite.
"""

from sqlalchemy import create_engine, text
from app.core.config import Base

# Test database URL
SQLALCHEMY_TEST_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
)

print("🧹 Cleaning test database...")

# Drop all tables
Base.metadata.drop_all(bind=engine)
print("✅ All tables dropped")

# Recreate all tables
Base.metadata.create_all(bind=engine)
print("✅ All tables recreated")

print("\n✨ Database is clean and ready for testing!")

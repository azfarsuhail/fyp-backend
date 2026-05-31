import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Environment flags
DEBUG = os.getenv("DEBUG", "0") in ("1", "true", "True")
TESTING = os.getenv("TESTING", "0") in ("1", "true", "True")

# DATABASE_URL should be set in .env for production (Neon/Postgres)
# Example: DATABASE_URL="postgresql://user:pass@host/dbname?sslmode=require"
DEFAULT_PG = "postgresql://localhost/knee_oa"
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_PG)

# Create engine with sensible defaults for SQLite (tests/local) and Postgres
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
	# sqlite needs connect_args for check_same_thread when used in tests
	engine = create_engine(
		SQLALCHEMY_DATABASE_URL,
		connect_args={"check_same_thread": False},
		echo=DEBUG,
	)
else:
	# For Postgres/Neon, enable pool_pre_ping to avoid stale connections
	engine = create_engine(
		SQLALCHEMY_DATABASE_URL,
		pool_pre_ping=True,
		echo=DEBUG,
	)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
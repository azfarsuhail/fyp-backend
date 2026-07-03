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
# For containerized tests, DB_HOST should be set to 'db' (docker-compose service name)
# For production with Neon, set DATABASE_URL directly in .env
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "knee_oa")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")

# Build DATABASE_URL from environment variables
DEFAULT_PG = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
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
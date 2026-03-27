import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Add this to your .env file: 
# DATABASE_URL="postgresql://your_neon_user:your_password@your_neon_host/your_db_name?sslmode=require"
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/knee_oa")

# Neon DB requires SSL, which is usually handled by the connection string
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
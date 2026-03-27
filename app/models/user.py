from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.core.config import Base

class User(Base):
    __tablename__ = "USER" # Matches your ERD [cite: 393, 394]

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="patient") # 'patient', 'gp', or 'admin'
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
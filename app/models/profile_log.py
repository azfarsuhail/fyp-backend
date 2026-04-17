"""
ProfileLog Model
----------------
Audit trail that records every change to a user's profile fields.
This allows GPs to see a patient's history over time — e.g. how their
pain level or mobility has changed between visits.

Each row captures:
  - WHO changed (user_id)
  - WHAT changed (field_name)
  - FROM what value (old_value)
  - TO what value (new_value)
  - WHEN it changed (changed_at)
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.config import Base


class ProfileLog(Base):
    __tablename__ = "PROFILE_LOG"

    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("USER.user_id"), nullable=False, index=True)
    field_name = Column(String, nullable=False)       # e.g. "pain_level", "mobility_level", "age"
    old_value = Column(Text, nullable=True)            # Previous value (as string)
    new_value = Column(Text, nullable=True)            # New value (as string)
    changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationship
    user = relationship("User", back_populates="profile_logs")

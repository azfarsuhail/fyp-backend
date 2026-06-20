from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.config import Base


class User(Base):
    __tablename__ = "USER"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="patient")  # 'patient', 'gp', or 'admin'

    # ── Patient Context Fields ────────────────────────────────────────────
    age = Column(Integer, nullable=True)
    pain_level = Column(Integer, nullable=True)          # 0-10 self-reported
    mobility_level = Column(String, nullable=True)       # 'limited', 'moderate', 'good'
    has_support = Column(Boolean, nullable=True)          # Is there someone to help them?
    
    # Additional patient context fields (April 2026)
    kinesiophobia = Column(String, nullable=True)        # 'low', 'moderate', 'high'
    occupation_type = Column(String, nullable=True)      # 'sedentary', 'light_manual', 'heavy_manual'
    has_stairs = Column(Boolean, nullable=True)           # Access to stairs at home/work
    current_meds = Column(String, nullable=True)          # JSON array of medication names
    sleep_quality = Column(String, nullable=True)        # 'poor', 'fair', 'good'

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True)


# Configure relationships after all models are loaded
def _configure_relationships():
    """Post-import configuration to avoid circular import issues."""
    from app.models import image, report, profile_log, otp_verification
    
    # Image.user already has backref="images"
    # Report.user already has backref="reports"
    # Configure ProfileLog relationship
    User.profile_logs = relationship(
        "ProfileLog", 
        back_populates="user", 
        lazy="dynamic"
    )
    
    # Configure OTPVerification relationship with cascade delete
    User.otp_verifications = relationship(
        "OTPVerification", 
        back_populates="user", 
        cascade="all, delete-orphan",
        lazy="dynamic"
    )


# Run configuration after module load
_configure_relationships()

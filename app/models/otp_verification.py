"""
OTPVerification Model
---------------------
Stores one-time password (OTP) records for password reset verification.
Each OTP is a 6-digit numeric code that expires after 5 minutes.

Security Features:
- OTP codes are hashed using bcrypt before storage
- Rate limiting via attempt counter (max 3 attempts)
- Automatic expiration via TTL
- Soft-delete support via is_verified flag
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.config import Base


class OTPVerification(Base):
    __tablename__ = "otp_verification"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("USER.user_id", ondelete="CASCADE"), nullable=False, index=True)
    code_hash = Column(String(255), nullable=False)  # bcrypt-hashed 6-digit OTP
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, default=0)
    is_verified = Column(Integer, default=0)  # 0 = pending, 1 = verified, 2 = expired/locked

    # Relationship (backref defined in User model)
    user = relationship("User", back_populates="otp_verifications")

    # Composite index for efficient cleanup of expired OTPs
    __table_args__ = (
        Index("idx_user_expires", "user_id", "expires_at"),
    )

    def __repr__(self):
        return f"<OTPVerification(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at}, is_verified={self.is_verified})>"

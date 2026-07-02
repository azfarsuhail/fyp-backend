"""
OTP Service Layer
-----------------
Handles OTP generation, verification, and lifecycle management.
Implements security best practices including:
- Secure random generation using secrets module
- bcrypt hashing for OTP storage
- Rate limiting via attempt counter
- TTL-based expiration
"""

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.otp_verification import OTPVerification
from app.core.security import pwd_context

# OTP Configuration
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
MAX_ATTEMPTS = 3


def generate_otp_code() -> str:
    """
    Generate a secure 6-digit numeric OTP code.
    
    Uses Python's secrets module for cryptographically secure random generation.
    
    Returns:
        6-digit numeric string
    """
    return ''.join(secrets.choice(string.digits) for _ in range(OTP_LENGTH))


def hash_otp_code(otp_code: str) -> str:
    """
    Hash an OTP code using bcrypt.
    
    Args:
        otp_code: Plain-text OTP string
        
    Returns:
        bcrypt-hashed string
    """
    return pwd_context.hash(otp_code)


def verify_otp_code(otp_code: str, code_hash: str) -> bool:
    """
    Verify a plain-text OTP code against its hash.
    
    Args:
        otp_code: Plain-text OTP to verify
        code_hash: bcrypt-hashed OTP stored in database
        
    Returns:
        True if OTP matches, False otherwise
    """
    return pwd_context.verify(otp_code, code_hash)


def create_otp_record(db: Session, user_id: int) -> OTPVerification:
    """
    Create a new OTP verification record for a user.
    
    Args:
        db: SQLAlchemy database session
        user_id: ID of the user to create OTP for
        
    Returns:
        Created OTPVerification record
    """
    # Generate and hash OTP
    otp_code = generate_otp_code()
    code_hash = hash_otp_code(otp_code)
    
    # Set expiration to 5 minutes from now
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
    
    # Create record
    otp_record = OTPVerification(
        user_id=user_id,
        code_hash=code_hash,
        expires_at=expires_at,
        attempts=0,
        is_verified=0
    )
    
    db.add(otp_record)
    db.commit()
    db.refresh(otp_record)
    
    return otp_record, otp_code


def get_active_otp(db: Session, user_id: int) -> Optional[OTPVerification]:
    """
    Retrieve the most recent active OTP for a user.
    
    An OTP is considered active if:
    - It hasn't expired (expires_at > now)
    - It hasn't been verified or locked out (is_verified == 0)
    
    Args:
        db: SQLAlchemy database session
        user_id: User ID to look up
        
    Returns:
        OTPVerification record if active, None otherwise
    """
    now = datetime.now(timezone.utc)
    
    otp_record = db.query(OTPVerification).filter(
        OTPVerification.user_id == user_id,
        OTPVerification.expires_at > now,
        OTPVerification.is_verified == 0
    ).order_by(OTPVerification.id.desc()).first()
    
    return otp_record


def verify_otp_and_increment_attempts(
    db: Session, 
    user_id: int, 
    otp_code: str
) -> Tuple[bool, str]:
    """
    Verify an OTP code and handle attempt tracking.
    
    Security Features:
    - Increments attempt counter on failure
    - Locks OTP after MAX_ATTEMPTS failed attempts
    - Returns appropriate error messages
    
    Args:
        db: SQLAlchemy database session
        user_id: User ID attempting verification
        otp_code: Plain-text OTP to verify
        
    Returns:
        Tuple of (success: bool, message: str)
        - (True, "success") if OTP is valid
        - (False, error_message) if verification fails
    """
    otp_record = get_active_otp(db, user_id)
    
    if otp_record is None:
        return False, "Invalid or expired OTP code"
    
    # Verify the OTP code
    if verify_otp_code(otp_code, otp_record.code_hash):
        # OTP is valid - mark as verified
        otp_record.is_verified = 1
    
    try:
        db.commit()
        return True, "success"
    except Exception:
        db.rollback()
        raise
    
    # OTP is invalid - increment attempts
    otp_record.attempts += 1
    
    # Check if max attempts reached
    if otp_record.attempts >= MAX_ATTEMPTS:
        otp_record.is_verified = 2  # Lock out the OTP
        
        try:
            db.commit()
            return False, "Too many failed attempts. OTP has been locked."
        except Exception:
            db.rollback()
            raise
    
    try:
        db.commit()
        remaining_attempts = MAX_ATTEMPTS - otp_record.attempts
        return False, f"Invalid OTP code. {remaining_attempts} attempts remaining."
    except Exception:
        db.rollback()
        raise
def cleanup_expired_otps(db: Session) -> int:
    """
    Soft-delete expired OTP records.
    
    This should be called periodically (e.g., via cron job) to clean up
    old OTP records from the database.
    
    Args:
        db: SQLAlchemy database session
        
    Returns:
        Number of expired OTPs cleaned up
    """
    now = datetime.now(timezone.utc)
    
    result = db.query(OTPVerification).filter(
        OTPVerification.expires_at < now,
        OTPVerification.is_verified == 0
    ).update({"is_verified": 2})  # Mark as expired
    
    try:
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def delete_otp_for_user(db: Session, user_id: int) -> None:
    """
    Delete all OTP records for a user (e.g., after successful password reset).
    
    Args:
        db: SQLAlchemy database session
        user_id: User ID to delete OTPs for
    """
    db.query(OTPVerification).filter(
        OTPVerification.user_id == user_id
    ).delete()
    db.commit()

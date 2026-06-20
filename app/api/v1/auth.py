import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from fastapi.background import BackgroundTasks

from app.schemas.user_schema import (
    UserCreate, UserOut, Token, ForgotPasswordRequest, ResetPasswordRequest,
    OTPRequestSchema, OTPVerifyAndResetSchema
)
from app.core.security import get_password_hash, verify_password, create_access_token, create_password_reset_token, verify_password_reset_token
from app.core.security_middleware import require_strong_password
from app.core.dependencies import get_db
from app.models.user import User
from app.models.profile_log import ProfileLog
from app.services.email import send_reset_password_email, send_otp_email
from app.services.otp_service import (
    create_otp_record,
    verify_otp_and_increment_attempts,
    delete_otp_for_user
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists in Neon DB
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Prevent admin registration - admins must be created manually
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration as admin is not allowed. Contact system administrator."
        )
    
    # Validate password strength
    password_errors = require_strong_password(user.password)
    if password_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"password_validation_errors": password_errors}
        )
    
    hashed_password = get_password_hash(user.password)
    
    # Create new user record
    new_user = User(
        email=user.email,
        full_name=user.full_name,
        password_hash=hashed_password,
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/login", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Fetch user from Neon DB
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    
    # Generate Token
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Initiate password reset process.
    
    Sends a password reset email to the provided address if it exists in the database.
    Returns a generic success message regardless of whether the email exists (to prevent email enumeration).
    """
    email = request.email
    
    # Check if user exists (but don't reveal this information for security)
    db_user = db.query(User).filter(User.email == email).first()
    
    if db_user:
        # Generate reset token
        token = create_password_reset_token(email)
        
        # Send email asynchronously using FastAPI's BackgroundTasks
        background_tasks.add_task(send_reset_password_email, email_to=email, token=token)
    
    # Always return same response to prevent email enumeration attacks
    return {
        "message": "If an account with that email address exists, a password reset link has been sent."
    }


@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset password using the reset token.
    
    Validates the token, verifies the new password meets strength requirements,
    and updates the user's password hash in the database.
    """
    token = request.token
    new_password = request.new_password
    
    # Log incoming request details for debugging
    logger.info(f"Reset password request received. Request body: token={token[:20]}..., new_password length={len(new_password)}")
    logger.info(f"Token value: {token}")
    
    # Verify the reset token
    email = verify_password_reset_token(token)
    
    logger.info(f"verify_password_reset_token result: email={email}, token_valid={email is not None}")
    
    if not email:
        logger.warning(f"Invalid or expired reset token provided. Token: {token[:50]}...")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Additional check: verify the email from token is valid and properly formatted
    if not email or not isinstance(email, str):
        logger.error(f"Invalid email extracted from token: {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token payload: email not found"
        )
    
    # Validate email format before querying database
    from email.utils import parseaddr
    parsed_email = parseaddr(email)[1]
    if not parsed_email or '@' not in parsed_email:
        logger.error(f"Email validation failed: {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format in token"
        )
    
    logger.info(f"Email validated from token: {parsed_email}")
    
    # Find the user by email
    user = db.query(User).filter(User.email == parsed_email).first()
    
    if not user:
        logger.warning(f"User not found for email: {parsed_email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logger.info(f"User found for email: {parsed_email}, user_id={user.user_id}")
    
    # Validate password strength
    password_errors = require_strong_password(new_password)
    if password_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"password_validation_errors": password_errors}
        )
    
    # Hash and update password
    hashed_password = get_password_hash(new_password)
    user.password_hash = hashed_password
    
    db.commit()
    
    return {
        "message": "Your password has been successfully reset. You can now log in with your new password."
    }


@router.post("/request-otp", status_code=status.HTTP_200_OK)
def request_otp(
    request: OTPRequestSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Request an OTP for password reset.
    
    Security Features:
    - Rate limited by IP (3 requests per hour via RateLimitAuthMiddleware)
    - Prevents email enumeration by returning generic success message
    - OTP is hashed before storage
    - OTP expires in 5 minutes
    
    Args:
        request: OTPRequestSchema with email
        background_tasks: FastAPI background tasks for email sending
        db: Database session
        
    Returns:
        Generic success message to prevent email enumeration
    """
    email = request.email
    
    # Check if user exists (but don't reveal this information for security)
    db_user = db.query(User).filter(User.email == email).first()
    
    if db_user:
        try:
            # Create OTP record and get the plain-text code
            otp_record, otp_code = create_otp_record(db, db_user.user_id)
            
            logger.info(f"OTP generated for user {db_user.user_id}, email: {email}")
            
            # Send email asynchronously using FastAPI's BackgroundTasks
            # Pass the plain-text OTP code for the email template
            background_tasks.add_task(
                send_otp_email,
                email_to=email,
                otp_code=otp_code
            )
            
            logger.info(f"OTP email queued for delivery to {email}")
            
        except Exception as e:
            # Log the error but don't reveal details
            logger.error(f"Error generating OTP for {email}: {str(e)}")
            # Still return success to prevent enumeration
            pass
    
    # Always return same response to prevent email enumeration attacks
    return {
        "message": "If an account with that email address exists, a password reset code has been sent."
    }


@router.post("/verify-otp-and-reset", status_code=status.HTTP_200_OK)
def verify_otp_and_reset_password(
    request: OTPVerifyAndResetSchema,
    db: Session = Depends(get_db)
):
    """
    Verify OTP and reset password in a single endpoint.
    
    Security Features:
    - Validates new password strength using require_strong_password()
    - Verifies OTP via service layer with attempt tracking
    - Locks OTP after 3 failed attempts
    - Logs password change in PROFILE_LOG audit table
    - Deletes OTP record after successful reset
    
    Args:
        request: OTPVerifyAndResetSchema with email, otp_code, and new_password
        db: Database session
        
    Returns:
        Success message confirming password reset
    """
    email = request.email
    otp_code = request.otp_code
    new_password = request.new_password
    
    logger.info(f"OTP verification request for email: {email}")
    
    # Find the user by email
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Don't reveal if user exists - return generic error
        logger.warning(f"User not found for email: {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP or email address"
        )
    
    # Validate password strength
    password_errors = require_strong_password(new_password)
    if password_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"password_validation_errors": password_errors}
        )
    
    # Verify the OTP
    success, message = verify_otp_and_increment_attempts(db, user.user_id, otp_code)
    
    if not success:
        logger.warning(f"OTP verification failed for user {user.user_id}: {message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # OTP is valid - proceed with password reset
    try:
        # Hash and update password
        hashed_password = get_password_hash(new_password)
        user.password_hash = hashed_password
        
        # Log the password change in PROFILE_LOG audit table
        password_log = ProfileLog(
            user_id=user.user_id,
            field_name="password_hash",
            old_value="***hidden***",  # Don't log actual password
            new_value="***updated***",
            changed_at=datetime.now(timezone.utc)
        )
        db.add(password_log)
        
        # Delete the OTP record after successful use
        delete_otp_for_user(db, user.user_id)
        
        db.commit()
        
        logger.info(f"Password successfully reset for user {user.user_id}")
        
        return {
            "message": "Your password has been successfully reset using the OTP code. You can now log in with your new password."
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error resetting password for user {user.user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password. Please try again."
        )
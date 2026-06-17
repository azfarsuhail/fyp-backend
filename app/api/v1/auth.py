from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from fastapi.background import BackgroundTasks

from app.schemas.user_schema import UserCreate, UserOut, Token, ForgotPasswordRequest, ResetPasswordRequest
from app.core.security import get_password_hash, verify_password, create_access_token, create_password_reset_token, verify_password_reset_token
from app.core.security_middleware import require_strong_password
from app.core.dependencies import get_db
from app.models.user import User
from app.services.email import send_reset_password_email

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
    
    # Verify the reset token
    email = verify_password_reset_token(token)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Find the user by email
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
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
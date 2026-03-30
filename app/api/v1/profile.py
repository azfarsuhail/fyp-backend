"""
Profile Router
--------------
User profile management: view, update, change password, and view history.
Logs all profile changes to PROFILE_LOG for audit trail.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.core.security import verify_password, get_password_hash
from app.schemas.profile_schema import ProfileOut, ProfileUpdate, PasswordChange, ProfileHistoryOut, ProfileLogOut
from app.models.user import User
from app.models.profile_log import ProfileLog

router = APIRouter()


def log_profile_change(db: Session, user_id: int, field_name: str, old_value: any, new_value: any):
    """Create a ProfileLog entry for a field change."""
    if old_value == new_value:
        return  # No change, don't log
    
    log_entry = ProfileLog(
        user_id=user_id,
        field_name=field_name,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
    )
    db.add(log_entry)


@router.get("/me", response_model=ProfileOut)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get the current authenticated user's profile."""
    user = db.query(User).filter(User.email == current_user["email"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/me/history", response_model=ProfileHistoryOut)
def get_profile_history(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get the change history for the current user's profile fields."""
    user = db.query(User).filter(User.email == current_user["email"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    logs = db.query(ProfileLog).filter(ProfileLog.user_id == user.user_id).order_by(ProfileLog.changed_at.desc()).all()
    
    return ProfileHistoryOut(
        user_id=user.user_id,
        full_name=user.full_name,
        total_changes=len(logs),
        history=logs,
    )


@router.put("/me", response_model=ProfileOut)
def update_my_profile(
    updates: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update the current user's profile (name, email, age, pain_level, mobility_level, has_support).
    
    All changes are logged to PROFILE_LOG for audit trail.
    """
    user = db.query(User).filter(User.email == current_user["email"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Log and update full_name
    if updates.full_name is not None and updates.full_name != user.full_name:
        log_profile_change(db, user.user_id, "full_name", user.full_name, updates.full_name)
        user.full_name = updates.full_name

    # Log and update email
    if updates.email is not None:
        if updates.email != user.email:
            log_profile_change(db, user.user_id, "email", user.email, updates.email)
        # Check if the new email is already taken
        existing = db.query(User).filter(User.email == updates.email).first()
        if existing and existing.user_id != user.user_id:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = updates.email

    # Log and update age
    if updates.age is not None and updates.age != user.age:
        log_profile_change(db, user.user_id, "age", user.age, updates.age)
        user.age = updates.age

    # Log and update pain_level
    if updates.pain_level is not None and updates.pain_level != user.pain_level:
        log_profile_change(db, user.user_id, "pain_level", user.pain_level, updates.pain_level)
        user.pain_level = updates.pain_level

    # Log and update mobility_level
    if updates.mobility_level is not None and updates.mobility_level != user.mobility_level:
        log_profile_change(db, user.user_id, "mobility_level", user.mobility_level, updates.mobility_level)
        user.mobility_level = updates.mobility_level

    # Log and update has_support
    if updates.has_support is not None and updates.has_support != user.has_support:
        log_profile_change(db, user.user_id, "has_support", user.has_support, updates.has_support)
        user.has_support = updates.has_support

    db.commit()
    db.refresh(user)
    return user


@router.post("/me/change-password", status_code=status.HTTP_200_OK)
def change_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Change the current user's password."""
    user = db.query(User).filter(User.email == current_user["email"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.password_hash = get_password_hash(payload.new_password)
    db.commit()

    return {"message": "Password updated successfully"}

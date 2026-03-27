"""
Profile Router
--------------
User profile management: view, update, and change password.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.core.security import verify_password, get_password_hash
from app.schemas.profile_schema import ProfileOut, ProfileUpdate, PasswordChange
from app.models.user import User

router = APIRouter()


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


@router.put("/me", response_model=ProfileOut)
def update_my_profile(
    updates: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update the current user's profile (name, email)."""
    user = db.query(User).filter(User.email == current_user["email"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if updates.full_name is not None:
        user.full_name = updates.full_name

    if updates.email is not None:
        # Check if the new email is already taken
        existing = db.query(User).filter(User.email == updates.email).first()
        if existing and existing.user_id != user.user_id:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = updates.email

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

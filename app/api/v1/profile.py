"""
Profile Router
--------------
User profile management: view, update, change password, and view history.
Logs all profile changes to PROFILE_LOG for audit trail.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from typing import List
from app.core.dependencies import get_db, get_current_user, RoleChecker
from app.core.security import verify_password, get_password_hash
from app.schemas.profile_schema import ProfileOut, ProfileUpdate, PasswordChange, ProfileHistoryOut, ProfileLogOut, PatientSearchOut
from app.models.user import User
from app.models.profile_log import ProfileLog

router = APIRouter()

# Allow GPs and admins to view patient histories
allow_gp = RoleChecker(allowed_roles=["gp", "admin"])


def normalize_current_meds(user: User) -> User:
    """Ensure current_meds is a Python list before Pydantic serializes the response."""
    if isinstance(user.current_meds, str):
        try:
            user.current_meds = json.loads(user.current_meds)
        except json.JSONDecodeError:
            user.current_meds = []
    return user


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
    return normalize_current_meds(user)


@router.get("/me/history", response_model=ProfileHistoryOut)
def get_profile_history(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get the change history for the current user's profile fields."""
    # Use eager loading to reduce 2 queries to 1
    user = db.query(User).options(
        joinedload(User.profile_logs)
    ).filter(User.email == current_user["email"]).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    logs = user.profile_logs
    
    return ProfileHistoryOut(
        user_id=user.user_id,
        full_name=user.full_name,
        total_changes=len(logs),
        history=logs,
    )



@router.get("/patients/{patient_id}/history", response_model=ProfileHistoryOut)
def get_patient_history(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_gp),
):
    """GP-only: Get the change history for a specific patient by user id."""
    # Use eager loading to reduce 2 queries to 1
    patient = db.query(User).options(
        joinedload(User.profile_logs)
    ).filter(User.user_id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if patient.role != "patient":
        raise HTTPException(status_code=400, detail="Requested user is not a patient")

    logs = patient.profile_logs

    return ProfileHistoryOut(
        user_id=patient.user_id,
        full_name=patient.full_name,
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

    # Log and update kinesiophobia
    if updates.kinesiophobia is not None and updates.kinesiophobia != user.kinesiophobia:
        log_profile_change(db, user.user_id, "kinesiophobia", user.kinesiophobia, updates.kinesiophobia)
        user.kinesiophobia = updates.kinesiophobia

    # Log and update occupation_type
    if updates.occupation_type is not None and updates.occupation_type != user.occupation_type:
        log_profile_change(db, user.user_id, "occupation_type", user.occupation_type, updates.occupation_type)
        user.occupation_type = updates.occupation_type

    # Log and update has_stairs
    if updates.has_stairs is not None and updates.has_stairs != user.has_stairs:
        log_profile_change(db, user.user_id, "has_stairs", user.has_stairs, updates.has_stairs)
        user.has_stairs = updates.has_stairs

    # Log and update current_meds (convert list to JSON string for storage)
    if updates.current_meds is not None and updates.current_meds != user.current_meds:
        old_meds = json.dumps(user.current_meds) if user.current_meds else None
        new_meds = json.dumps(updates.current_meds)
        log_profile_change(db, user.user_id, "current_meds", old_meds, new_meds)
        user.current_meds = json.dumps(updates.current_meds)

    # Log and update sleep_quality
    if updates.sleep_quality is not None and updates.sleep_quality != user.sleep_quality:
        log_profile_change(db, user.user_id, "sleep_quality", user.sleep_quality, updates.sleep_quality)
        user.sleep_quality = updates.sleep_quality

    db.commit()
    db.refresh(user)
    return normalize_current_meds(user)


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


@router.get("/patients/search", response_model=List[PatientSearchOut])
def search_patients_by_email(
    email: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_gp),
):
    """GP-only: Search for patients by email (partial match).
    
    Args:
        email: Email address to search for (case-insensitive partial match)
        db: Database session
        current_user: Current authenticated GP user
        
    Returns:
        List of matching patients with user_id, full_name, and email
    """
    # Use ilike for case-insensitive partial match
    search_pattern = f"%{email}%"
    patients = db.query(User).filter(
        User.email.ilike(search_pattern),
        User.role == "patient"
    ).all()
    
    return [
        PatientSearchOut(
            user_id=patient.user_id,
            full_name=patient.full_name,
            email=patient.email
        )
        for patient in patients
    ]


@router.post("/patients/assign/{patient_id}", response_model=ProfileOut)
def assign_patient_to_gp(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_gp),
):
    """GP-only: Assign a patient to the current GP.
    
    Args:
        patient_id: ID of the patient to assign
        db: Database session
        current_user: Current authenticated GP user
        
    Returns:
        Updated patient profile
    """
    # Verify patient exists
    patient = db.query(User).filter(User.user_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if patient.role != "patient":
        raise HTTPException(status_code=400, detail="Requested user is not a patient")
    
    # Verify current user is a GP
    gp = db.query(User).filter(User.email == current_user["email"], User.role == "gp").first()
    if not gp:
        raise HTTPException(status_code=403, detail="Only GPs can assign patients")
    
    # Assign patient to GP
    patient.primary_gp_id = gp.user_id
    db.commit()
    db.refresh(patient)
    
    return normalize_current_meds(patient)


@router.get("/patients/mine", response_model=List[PatientSearchOut])
def get_my_patients(
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_gp),
):
    """GP-only: Get all patients assigned to the current GP.
    
    Args:
        db: Database session
        current_user: Current authenticated GP user
        
    Returns:
        List of assigned patients with user_id, full_name, and email
    """
    # Verify current user is a GP
    gp = db.query(User).filter(User.email == current_user["email"], User.role == "gp").first()
    if not gp:
        raise HTTPException(status_code=403, detail="Only GPs can view assigned patients")
    
    # Get all patients assigned to this GP
    patients = db.query(User).filter(
        User.primary_gp_id == gp.user_id,
        User.role == "patient"
    ).all()
    
    return [
        PatientSearchOut(
            user_id=patient.user_id,
            full_name=patient.full_name,
            email=patient.email
        )
        for patient in patients
    ]

"""
Mobile Sync Router
------------------
API endpoints for mobile app data synchronization.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.core.dependencies import get_db, get_current_user, RoleChecker
from app.services.mobile_sync import MobileSyncService, sync_user_data

router = APIRouter()


@router.get("/sync/data", response_model=dict)
def sync_user_data_endpoint(
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_sync),
):
    """
    Get all user-specific data for mobile sync.
    
    Returns:
        JSON with user profile, images, reports, and history
    """
    user_id = current_user.get("user_id")
    if not user_id:
        # Get user_id from database
        from app.models.user import User
        user = db.query(User).filter(User.email == current_user["email"]).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_id = user.user_id
    
    sync_service = MobileSyncService(db, user_id)
    user_data = sync_service.get_user_data()
    
    return user_data


@router.get("/sync/summary")
def get_sync_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_sync),
):
    """
    Get a summary of data that will be synced.
    
    Returns:
        Dictionary with counts of images, reports, and history
    """
    user_id = current_user.get("user_id")
    if not user_id:
        from app.models.user import User
        user = db.query(User).filter(User.email == current_user["email"]).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_id = user.user_id
    
    sync_service = MobileSyncService(db, user_id)
    summary = sync_service.get_sync_summary()
    
    return summary


@router.post("/sync/export")
def export_user_data(
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_sync),
):
    """
    Export user data as JSON for mobile download.
    
    Returns:
        JSON file with all user data
    """
    user_id = current_user.get("user_id")
    if not user_id:
        from app.models.user import User
        user = db.query(User).filter(User.email == current_user["email"]).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_id = user.user_id
    
    sync_service = MobileSyncService(db, user_id)
    json_data = sync_service.export_to_json()
    
    return Response(
        content=json_data,
        media_type="application/json",
        headers={
            "Content-Disposition": "attachment; filename=user_data.json"
        }
    )


@router.get("/sync/status")
def get_sync_status(
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_sync),
):
    """
    Get sync status and last sync time.
    
    Note: This would typically track when the user last synced on the mobile app.
    For now, returns current data counts.
    """
    user_id = current_user.get("user_id")
    if not user_id:
        from app.models.user import User
        user = db.query(User).filter(User.email == current_user["email"]).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_id = user.user_id
    
    sync_service = MobileSyncService(db, user_id)
    summary = sync_service.get_sync_summary()
    
    return {
        **summary,
        "last_sync": None,  # Would be tracked in mobile app
        "available": True,
    }

# Only patients and GPs can sync data
allow_sync = RoleChecker(allowed_roles=["patient", "gp"])

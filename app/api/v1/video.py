"""
Video Library Router
--------------------
CRUD endpoints for the exercise video library.
- Patients can browse videos filtered by KL grade
- Admins can add/update/delete videos
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.core.dependencies import get_db, RoleChecker, get_current_user
from app.models.library import ExerciseVideo

router = APIRouter()

# Role guards
allow_browse = RoleChecker(allowed_roles=["patient", "gp", "admin"])
allow_manage = RoleChecker(allowed_roles=["admin"])


# ── Schemas (local to this router for simplicity) ────────────────────────────

class VideoCreate(BaseModel):
    title: str
    description: Optional[str] = None
    s3_url: str
    thumbnail_url: Optional[str] = None
    kl_grade_min: int
    kl_grade_max: int
    category: str
    difficulty: str = "beginner"
    duration_seconds: Optional[int] = None


class VideoOut(BaseModel):
    video_id: int
    title: str
    description: Optional[str] = None
    s3_url: str
    thumbnail_url: Optional[str] = None
    kl_grade_min: int
    kl_grade_max: int
    category: str
    difficulty: str
    duration_seconds: Optional[int] = None

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[VideoOut])
def list_videos(
    kl_grade: Optional[int] = Query(None, ge=0, le=4, description="Filter by KL grade"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_browse),
):
    """
    List exercise videos, optionally filtered by KL grade and/or category.
    """
    query = db.query(ExerciseVideo)

    if kl_grade is not None:
        query = query.filter(
            ExerciseVideo.kl_grade_min <= kl_grade,
            ExerciseVideo.kl_grade_max >= kl_grade,
        )

    if category:
        query = query.filter(ExerciseVideo.category == category)

    return query.all()


@router.get("/{video_id}", response_model=VideoOut)
def get_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_browse),
):
    """Get a specific exercise video by ID."""
    video = db.query(ExerciseVideo).filter(ExerciseVideo.video_id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.post("/", response_model=VideoOut, status_code=status.HTTP_201_CREATED)
def create_video(
    video: VideoCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_manage),
):
    """Create a new exercise video entry (Admin only)."""
    new_video = ExerciseVideo(**video.model_dump())
    db.add(new_video)
    db.commit()
    db.refresh(new_video)
    return new_video


@router.put("/{video_id}", response_model=VideoOut)
def update_video(
    video_id: int,
    updates: VideoCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_manage),
):
    """Update an exercise video entry (Admin only)."""
    video = db.query(ExerciseVideo).filter(ExerciseVideo.video_id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    for key, value in updates.model_dump().items():
        setattr(video, key, value)

    db.commit()
    db.refresh(video)
    return video


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_manage),
):
    """Delete an exercise video entry (Admin only)."""
    video = db.query(ExerciseVideo).filter(ExerciseVideo.video_id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    db.delete(video)
    db.commit()

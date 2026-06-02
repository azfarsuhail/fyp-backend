"""
Video Library Router
--------------------
CRUD endpoints for the exercise video library.
- Patients can browse videos filtered by KL grade
- Admins can add/update/delete videos
"""

import re

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

from app.core.dependencies import get_db, RoleChecker, get_current_user
from app.models.library import ExerciseVideo
from app.services.s3_service import upload_file_to_s3

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


VIDEO_CONTENT_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-matroska",
    "application/octet-stream",
}


def category_to_folder(category: str) -> str:
    folder = re.sub(r"[^a-z0-9]+", "-", category.strip().lower()).strip("-")
    return folder or "uncategorized"


def blank_to_none(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
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


@router.post("/upload", response_model=VideoOut, status_code=status.HTTP_201_CREATED)
async def create_video_with_file(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    kl_grade_min: int = Form(...),
    kl_grade_max: int = Form(...),
    category: str = Form(...),
    difficulty: str = Form("beginner"),
    duration_seconds: Optional[int] = Form(None),
    thumbnail_url: Optional[str] = Form(None),
    video_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_manage),
):
    """Upload a video file to S3 and create the video record (Admin only)."""
    folder = category_to_folder(category)
    description = blank_to_none(description)
    thumbnail_url = blank_to_none(thumbnail_url)
    category = category.strip()

    if video_file.content_type and video_file.content_type not in VIDEO_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{video_file.content_type}'. Expected a video file.",
        )

    try:
        s3_key = await upload_file_to_s3(video_file, folder=folder)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    new_video = ExerciseVideo(
        title=title,
        description=description,
        s3_url=s3_key,
        thumbnail_url=thumbnail_url,
        kl_grade_min=kl_grade_min,
        kl_grade_max=kl_grade_max,
        category=category,
        difficulty=difficulty,
        duration_seconds=duration_seconds,
    )
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


@router.put("/{video_id}/upload", response_model=VideoOut)
async def update_video_with_file(
    video_id: int,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    kl_grade_min: int = Form(...),
    kl_grade_max: int = Form(...),
    category: str = Form(...),
    difficulty: str = Form("beginner"),
    duration_seconds: Optional[int] = Form(None),
    thumbnail_url: Optional[str] = Form(None),
    video_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_manage),
):
    """Update a video record and optionally replace the S3-backed file."""
    video = db.query(ExerciseVideo).filter(ExerciseVideo.video_id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    description = blank_to_none(description)
    thumbnail_url = blank_to_none(thumbnail_url)
    category = category.strip()

    if video_file is not None:
        folder = category_to_folder(category)

        if video_file.content_type and video_file.content_type not in VIDEO_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type '{video_file.content_type}'. Expected a video file.",
            )

        try:
            video.s3_url = await upload_file_to_s3(video_file, folder=folder)
        except RuntimeError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )

    video.title = title
    video.description = description
    video.thumbnail_url = thumbnail_url
    video.kl_grade_min = kl_grade_min
    video.kl_grade_max = kl_grade_max
    video.category = category
    video.difficulty = difficulty
    video.duration_seconds = duration_seconds

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

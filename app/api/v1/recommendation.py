"""
Recommendation Router
---------------------
Standalone endpoint to re-generate or fetch recommendations
without re-running the full diagnostic pipeline.
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_db, RoleChecker
from app.schemas.report_schema import RecommendationResult
from app.models.user import User
from app.agents.recommendation_agent import generate_recommendation

router = APIRouter()

allow_access = RoleChecker(allowed_roles=["patient", "gp"])


@router.get("/", response_model=RecommendationResult)
def get_recommendation(
    kl_grade: int,
    pain_level: Optional[int] = None,
    mobility_level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_access),
):
    """
    Get personalised lifestyle recommendations for a given KL grade.

    This is useful when:
      - The user wants updated advice after reporting new symptoms
      - A GP wants to generate advice for a specific grade without uploading an image

    Query params:
      - kl_grade (required): 0-4
      - pain_level (optional): 0-10
      - mobility_level (optional): "limited", "moderate", "good"
    
    Profile-based filtering (April 2026):
      - Automatically applies user's kinesiophobia, occupation, medications, and stairs profile
      - Filters out contraindicated advice based on clinical constraints
    """
    if not 0 <= kl_grade <= 4:
        raise HTTPException(status_code=400, detail="KL grade must be between 0 and 4")

    if pain_level is not None and not 0 <= pain_level <= 10:
        raise HTTPException(status_code=400, detail="Pain level must be between 0 and 10")

    # Fetch full user profile for new constraint fields
    user = db.query(User).filter(User.email == current_user["email"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        result = generate_recommendation(
            kl_grade=kl_grade,
            db=db,
            pain_level=pain_level,
            mobility_level=mobility_level,
            # New profile fields (April 2026)
            kinesiophobia=user.kinesiophobia,
            occupation_type=user.occupation_type,
            has_stairs=user.has_stairs,
            current_meds=json.loads(user.current_meds) if user.current_meds else None,
            sleep_quality=user.sleep_quality,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation generation failed: {e}")

    return RecommendationResult(
        lifestyle_plan=result["lifestyle_plan"],
        warnings=result["warnings"],
        exercise_videos=result["exercise_videos"],
        recommendation=result["recommendation"],
        exercise_video_urls=result["exercise_video_urls"],
    )

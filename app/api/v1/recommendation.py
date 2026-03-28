"""
Recommendation Router
---------------------
Standalone endpoint to re-generate or fetch recommendations
without re-running the full diagnostic pipeline.
"""

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
    """
    if not 0 <= kl_grade <= 4:
        raise HTTPException(status_code=400, detail="KL grade must be between 0 and 4")

    if pain_level is not None and not 0 <= pain_level <= 10:
        raise HTTPException(status_code=400, detail="Pain level must be between 0 and 10")

    try:
        result = generate_recommendation(
            kl_grade=kl_grade,
            db=db,
            pain_level=pain_level,
            mobility_level=mobility_level,
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

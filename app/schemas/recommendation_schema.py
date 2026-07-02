from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.report_schema import ExerciseVideoOut, LifestyleItem, Warning


class Medication(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    dosage: str
    frequency: str
    instructions: Optional[str] = None
    contraindications: Optional[List[str]] = None
    kl_grade_min: int
    kl_grade_max: int


class RecommendationResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lifestyle_plan: List[LifestyleItem] = Field(default_factory=list)
    warnings: List[Warning] = Field(default_factory=list)
    exercise_videos: List[ExerciseVideoOut] = Field(default_factory=list)
    medications: List[Medication] = Field(default_factory=list)
    recommendation: str
    exercise_video_urls: List[str] = Field(default_factory=list)
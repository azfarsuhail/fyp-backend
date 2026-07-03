from pydantic import BaseModel, Field
from typing import Optional, List


class LifestyleItem(BaseModel):
    """A single structured recommendation — no free-text, no hallucination."""
    id: str = Field(..., description="Unique record ID e.g. EX-001")
    category: str = Field(..., description="exercise | nutrition | pain_management | lifestyle | flexibility")
    action: str = Field(..., description="The specific recommendation")
    evidence_level: str = Field(..., description="strong | moderate | emerging")
    source: str = Field(..., description="Guideline or study citation")
    frequency: Optional[str] = None
    duration_min: Optional[int] = None
    intensity: Optional[str] = None
    contraindications: Optional[List[str]] = None
    modifier_note: Optional[str] = Field(None, description="Note if parameters were adjusted for pain/mobility")


class Warning(BaseModel):
    """A grade-specific clinical warning."""
    level: str = Field(..., description="info | caution | warning")
    message: str


class ExerciseVideoOut(BaseModel):
    """Structured exercise video metadata."""
    video_id: int
    title: str
    s3_url: str
    category: str
    difficulty: str
    duration_seconds: Optional[int] = None

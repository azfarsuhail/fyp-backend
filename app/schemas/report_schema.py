from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


class DiagnosticRequest(BaseModel):
    """Input for the diagnostic pipeline — image_id + optional user context."""
    image_id: int
    pain_level: Optional[int] = Field(None, ge=0, le=10, description="Self-reported pain 0-10")
    mobility_level: Optional[str] = Field(None, description="e.g. 'limited', 'moderate', 'good'")


class DiagnosticResult(BaseModel):
    """Output from the Diagnostic Agent (CNN inference)."""
    kl_grade: int = Field(..., ge=0, le=4, description="Kellgren-Lawrence grade 0-4")
    confidence: float = Field(..., ge=0.0, le=1.0)
    diagnosis_summary: str


# ── Parametric RAG Output Schemas ─────────────────────────────────────────────

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


class RecommendationResult(BaseModel):
    """
    Parametric RAG output — fully structured, zero hallucination.
    The mobile app renders each field directly into UI cards.
    """
    lifestyle_plan: List[LifestyleItem] = Field(default_factory=list, description="Ordered list of recommendations")
    warnings: List[Warning] = Field(default_factory=list, description="Grade-specific warnings")
    exercise_videos: List[ExerciseVideoOut] = Field(default_factory=list, description="Matching exercise videos")
    recommendation: str = Field(..., description="Legacy text summary for backward compatibility")
    exercise_video_urls: List[str] = Field(default_factory=list, description="Legacy: list of S3 URLs")


class ReportOut(BaseModel):
    """Full report returned to the client."""
    model_config = ConfigDict(from_attributes=True)
    
    report_id: int
    image_id: int
    user_id: int
    kl_grade: int
    confidence: float
    diagnosis_summary: Optional[str] = None
    recommendation: Optional[str] = None
    lifestyle_plan: Optional[List[LifestyleItem]] = None
    warnings: Optional[List[Warning]] = None
    exercise_video_urls: Optional[List[str]] = []
    created_at: datetime

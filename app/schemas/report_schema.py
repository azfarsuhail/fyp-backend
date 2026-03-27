from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


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


class RecommendationResult(BaseModel):
    """Output from the Recommendation Agent (RAG)."""
    recommendation: str
    exercise_video_urls: List[str] = []


class ReportOut(BaseModel):
    """Full report returned to the client."""
    report_id: int
    image_id: int
    user_id: int
    kl_grade: int
    confidence: float
    diagnosis_summary: Optional[str] = None
    recommendation: Optional[str] = None
    exercise_video_urls: Optional[List[str]] = []
    created_at: datetime

    class Config:
        from_attributes = True

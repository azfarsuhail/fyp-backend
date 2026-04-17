from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.config import Base


class Report(Base):
    __tablename__ = "REPORT"

    report_id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("IMAGE.image_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("USER.user_id"), nullable=False)

    # Diagnostic Agent outputs
    kl_grade = Column(Integer, nullable=False)          # 0-4 Kellgren-Lawrence grade
    confidence = Column(Float, nullable=False)           # Model confidence score
    diagnosis_summary = Column(Text, nullable=True)      # Human-readable diagnosis

    # Recommendation Agent outputs (Parametric RAG)
    recommendation = Column(Text, nullable=True)         # Legacy text summary
    lifestyle_plan = Column(Text, nullable=True)         # JSON: structured parametric recommendations
    warnings = Column(Text, nullable=True)               # JSON: grade-specific warnings
    exercise_video_urls = Column(Text, nullable=True)    # JSON string of S3 video URLs

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    image = relationship("Image", back_populates="report")
    user = relationship("User", backref="reports")

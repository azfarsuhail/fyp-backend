from sqlalchemy import Column, Integer, String, Text
from app.core.config import Base


class ExerciseVideo(Base):
    """Pre-generated exercise videos stored on S3, tagged by KL grade."""
    __tablename__ = "EXERCISE_VIDEO"

    video_id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    s3_url = Column(String, nullable=False)
    thumbnail_url = Column(String, nullable=True)
    kl_grade_min = Column(Integer, nullable=False)   # Minimum KL grade this video applies to
    kl_grade_max = Column(Integer, nullable=False)   # Maximum KL grade this video applies to
    category = Column(String, nullable=False)         # e.g. "strengthening", "flexibility", "low-impact"
    difficulty = Column(String, default="beginner")   # "beginner", "intermediate", "advanced"
    duration_seconds = Column(Integer, nullable=True)

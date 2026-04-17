from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.config import Base


class Image(Base):
    __tablename__ = "IMAGE"

    image_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("USER.user_id"), nullable=False)
    s3_url = Column(String, nullable=False)           # Original image URL on S3
    processed_s3_url = Column(String, nullable=True)   # Preprocessed image URL on S3
    file_name = Column(String, nullable=False)
    content_type = Column(String, default="image/png")
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", backref="images")
    report = relationship("Report", back_populates="image", uselist=False)

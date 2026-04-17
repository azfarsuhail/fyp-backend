from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class ImageUploadResponse(BaseModel):
    """Returned after a successful X-ray upload."""
    model_config = ConfigDict(from_attributes=True)
    
    image_id: int
    user_id: int
    s3_url: str
    file_name: str
    uploaded_at: datetime


class ImageOut(BaseModel):
    """Full image record returned in listings."""
    model_config = ConfigDict(from_attributes=True)
    
    image_id: int
    user_id: int
    s3_url: str
    processed_s3_url: Optional[str] = None
    file_name: str
    content_type: str
    uploaded_at: datetime

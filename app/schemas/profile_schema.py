from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class ProfileUpdate(BaseModel):
    """Fields a user can update on their profile."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    age: Optional[int] = Field(None, ge=1, le=120)
    pain_level: Optional[int] = Field(None, ge=0, le=10, description="Self-reported pain 0-10")
    mobility_level: Optional[str] = Field(None, description="'limited', 'moderate', or 'good'")
    has_support: Optional[bool] = Field(None, description="Is there someone to help them?")


class ProfileOut(BaseModel):
    """Public profile view."""
    model_config = ConfigDict(from_attributes=True)
    
    user_id: int
    email: EmailStr
    full_name: str
    role: str
    age: Optional[int] = None
    pain_level: Optional[int] = None
    mobility_level: Optional[str] = None
    has_support: Optional[bool] = None
    created_at: datetime
    last_login: Optional[datetime] = None


class PasswordChange(BaseModel):
    """Request body for changing password."""
    current_password: str
    new_password: str


class ProfileLogOut(BaseModel):
    """A single audit log entry for a profile field change."""
    model_config = ConfigDict(from_attributes=True)
    
    log_id: int
    user_id: int
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_at: datetime


class ProfileHistoryOut(BaseModel):
    """Full change history for a user's profile."""
    user_id: int
    full_name: str
    total_changes: int
    history: List[ProfileLogOut]

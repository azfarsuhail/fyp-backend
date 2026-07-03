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
    
    # Additional patient context fields (April 2026)
    kinesiophobia: Optional[str] = Field(None, description="'low', 'moderate', or 'high'")
    occupation_type: Optional[str] = Field(None, description="'sedentary', 'light_manual', or 'heavy_manual'")
    has_stairs: Optional[bool] = Field(None, description="Access to stairs at home/work")
    current_meds: Optional[List[str]] = Field(None, description="List of current medications")
    sleep_quality: Optional[str] = Field(None, description="'poor', 'fair', or 'good'")


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
    
    # Additional patient context fields (April 2026)
    kinesiophobia: Optional[str] = None
    occupation_type: Optional[str] = None
    has_stairs: Optional[bool] = None
    current_meds: Optional[List[str]] = None
    sleep_quality: Optional[str] = None
    
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


class PatientSearchOut(BaseModel):
    """Search result for patient lookup by email."""
    user_id: int
    full_name: str
    email: str

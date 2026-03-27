from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class ProfileUpdate(BaseModel):
    """Fields a user can update on their profile."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class ProfileOut(BaseModel):
    """Public profile view."""
    user_id: int
    email: EmailStr
    full_name: str
    role: str
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    """Request body for changing password."""
    current_password: str
    new_password: str

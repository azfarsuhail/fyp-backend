from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "patient"  # 'patient', 'gp', or 'admin'
    # Patient context fields (optional at registration)
    age: Optional[int] = Field(None, ge=1, le=120)
    pain_level: Optional[int] = Field(None, ge=0, le=10, description="Self-reported pain 0-10")
    mobility_level: Optional[str] = Field(None, description="'limited', 'moderate', or 'good'")
    has_support: Optional[bool] = Field(None, description="Is there someone to help them?")


class UserOut(BaseModel):
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


class Token(BaseModel):
    access_token: str
    token_type: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        if not v or len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
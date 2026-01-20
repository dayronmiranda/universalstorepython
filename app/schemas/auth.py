"""Authentication schemas"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.user import UserRole


class MagicLinkRequest(BaseModel):
    """Request schema for magic link"""
    email: EmailStr

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class MagicLinkResponse(BaseModel):
    """Response schema for magic link request"""
    success: bool = True
    message: str = "Magic link sent to your email"


class VerifyMagicLinkRequest(BaseModel):
    """Request schema for verifying magic link"""
    token: str

    class Config:
        json_schema_extra = {
            "example": {
                "token": "abc123def456..."
            }
        }


class TokenResponse(BaseModel):
    """JWT token response"""
    success: bool = True
    token: str
    user: "UserProfileResponse"


class UserProfileResponse(BaseModel):
    """User profile response"""
    id: str
    email: EmailStr
    name: Optional[str] = None
    role: UserRole
    active: bool

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "name": "John Doe",
                "role": "client",
                "active": True
            }
        }


class UpdateProfileRequest(BaseModel):
    """Request schema for updating user profile"""
    name: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "phone": "+1234567890"
            }
        }

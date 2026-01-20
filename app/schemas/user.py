"""User schemas for CRUD operations"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserCreate(BaseModel):
    """Schema for creating a new user"""
    email: EmailStr
    name: Optional[str] = None
    role: UserRole = UserRole.CLIENT

    class Config:
        json_schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "name": "New User",
                "role": "client"
            }
        }


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    name: Optional[str] = None
    role: Optional[UserRole] = None
    active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Name",
                "role": "support",
                "active": True
            }
        }


class UserResponse(BaseModel):
    """Schema for user response"""
    id: str
    email: EmailStr
    name: Optional[str] = None
    role: UserRole
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "name": "John Doe",
                "role": "client",
                "active": True,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }


class CustomerResponse(BaseModel):
    """Schema for customer response with stats"""
    id: str
    email: EmailStr
    name: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole
    active: bool
    order_count: int
    total_spent: float
    last_order_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "customer@example.com",
                "name": "Jane Smith",
                "phone": "+1234567890",
                "role": "client",
                "active": True,
                "order_count": 5,
                "total_spent": 299.99,
                "last_order_date": "2024-01-15T10:30:00",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-15T10:30:00"
            }
        }

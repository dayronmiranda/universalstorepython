"""User models"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration"""
    CLIENT = "client"
    SUPPORT = "support"
    PRODUCT_MANAGER = "product_manager"
    ADMIN = "admin"


class User(BaseModel):
    """User model for authentication and authorization"""
    id: Optional[str] = Field(None, alias="_id")
    email: EmailStr
    name: Optional[str] = None
    role: UserRole = UserRole.CLIENT
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "role": "client",
                "active": True
            }
        }


class Customer(BaseModel):
    """Customer model (client users with additional info)"""
    id: Optional[str] = Field(None, alias="_id")
    email: EmailStr
    name: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole = UserRole.CLIENT
    active: bool = True
    order_count: int = 0
    total_spent: float = 0.0
    last_order_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "email": "customer@example.com",
                "name": "Jane Smith",
                "phone": "+1234567890",
                "role": "client",
                "active": True,
                "order_count": 5,
                "total_spent": 299.99
            }
        }


class MagicLink(BaseModel):
    """Magic link model for passwordless authentication"""
    id: Optional[str] = Field(None, alias="_id")
    email: EmailStr
    token: str
    used: bool = False
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

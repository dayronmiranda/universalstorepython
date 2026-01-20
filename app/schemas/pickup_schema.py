"""Pickup location schemas"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.common import Address


class PickupSlotResponse(BaseModel):
    """Response schema for pickup slot"""
    day_of_week: int
    start_time: str
    end_time: str
    capacity: int


class PickupLocationResponse(BaseModel):
    """Response schema for pickup location"""
    id: str
    name: str
    address: Address
    phone: Optional[str] = None
    email: Optional[str] = None
    available_slots: List[PickupSlotResponse]
    instructions: Optional[str] = None
    active: bool


class PickupConfirmRequest(BaseModel):
    """Schema for confirming pickup"""
    location_id: str
    pickup_date: datetime
    notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "location_id": "507f1f77bcf86cd799439011",
                "pickup_date": "2024-01-25T14:00:00",
                "notes": "I'll arrive around 2 PM"
            }
        }


class PickupVerifyRequest(BaseModel):
    """Schema for verifying pickup code"""
    pickup_code: str

    class Config:
        json_schema_extra = {
            "example": {
                "pickup_code": "PICK-ABC123"
            }
        }


class PickupSuggestTimesRequest(BaseModel):
    """Schema for suggesting pickup times"""
    location_id: str
    preferred_date: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "location_id": "507f1f77bcf86cd799439011",
                "preferred_date": "2024-01-25T00:00:00"
            }
        }

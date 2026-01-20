"""Pickup location models"""

from pydantic import BaseModel, Field
from datetime import datetime, time
from typing import Optional, List
from app.models.common import Address


class PickupSlot(BaseModel):
    """Pickup time slot"""
    day_of_week: int = Field(ge=0, le=6)  # 0=Monday, 6=Sunday
    start_time: str  # "09:00"
    end_time: str  # "17:00"
    capacity: int = Field(default=10, ge=1)


class PickupLocation(BaseModel):
    """Pickup location model"""
    id: Optional[str] = Field(None, alias="_id")
    name: str
    address: Address
    phone: Optional[str] = None
    email: Optional[str] = None
    available_slots: List[PickupSlot] = []
    instructions: Optional[str] = None
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "Main Warehouse",
                "address": {
                    "address_line1": "123 Warehouse St",
                    "city": "New York",
                    "postal_code": "10001",
                    "country": "USA"
                },
                "phone": "+1234567890",
                "email": "pickup@jollytienda.com",
                "available_slots": [
                    {
                        "day_of_week": 1,
                        "start_time": "09:00",
                        "end_time": "17:00",
                        "capacity": 10
                    }
                ],
                "active": True
            }
        }


class PickupConfirmation(BaseModel):
    """Pickup confirmation for an order"""
    order_id: str
    location_id: str
    pickup_date: datetime
    pickup_code: str
    confirmed: bool = False
    confirmed_at: Optional[datetime] = None
    notes: Optional[str] = None

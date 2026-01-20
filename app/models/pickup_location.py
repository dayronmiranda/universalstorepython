from pydantic import BaseModel, EmailStr
from typing import Optional, Dict
from datetime import datetime


class Coordinates(BaseModel):
    lat: float
    lng: float


class DaySchedule(BaseModel):
    open: str  # "09:00"
    close: str  # "17:00"
    closed: bool = False


class WeeklySchedule(BaseModel):
    monday: Optional[DaySchedule] = None
    tuesday: Optional[DaySchedule] = None
    wednesday: Optional[DaySchedule] = None
    thursday: Optional[DaySchedule] = None
    friday: Optional[DaySchedule] = None
    saturday: Optional[DaySchedule] = None
    sunday: Optional[DaySchedule] = None


class PickupLocation(BaseModel):
    slug: Optional[str] = None
    name: str
    description: Optional[str] = None
    address: str
    city: str
    province: Optional[str] = None
    postalCode: Optional[str] = None
    country: str
    coordinates: Optional[Coordinates] = None
    operatingHours: Optional[WeeklySchedule] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    urgentPhone: Optional[str] = None
    estimatedCapacity: int
    maxOrdersPerSlot: Optional[int] = None
    slotDurationMinutes: Optional[int] = 30
    isActive: bool = True
    isDefault: bool = False
    sortOrder: int = 0
    internalNotes: Optional[str] = None
    pickupInstructions: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

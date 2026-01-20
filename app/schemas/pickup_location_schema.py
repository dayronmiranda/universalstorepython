from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class CoordinatesRequest(BaseModel):
    lat: float
    lng: float


class DayScheduleRequest(BaseModel):
    open: str
    close: str
    closed: bool = False


class WeeklyScheduleRequest(BaseModel):
    monday: Optional[DayScheduleRequest] = None
    tuesday: Optional[DayScheduleRequest] = None
    wednesday: Optional[DayScheduleRequest] = None
    thursday: Optional[DayScheduleRequest] = None
    friday: Optional[DayScheduleRequest] = None
    saturday: Optional[DayScheduleRequest] = None
    sunday: Optional[DayScheduleRequest] = None


class CreatePickupLocationRequest(BaseModel):
    slug: Optional[str] = None
    name: str
    description: Optional[str] = None
    address: str
    city: str
    province: Optional[str] = None
    postalCode: Optional[str] = None
    country: str
    coordinates: Optional[CoordinatesRequest] = None
    operatingHours: Optional[WeeklyScheduleRequest] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    urgentPhone: Optional[str] = None
    estimatedCapacity: int
    maxOrdersPerSlot: Optional[int] = None
    slotDurationMinutes: Optional[int] = 30
    isActive: bool = True
    isDefault: bool = False
    internalNotes: Optional[str] = None
    pickupInstructions: Optional[str] = None


class UpdatePickupLocationRequest(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None
    coordinates: Optional[CoordinatesRequest] = None
    operatingHours: Optional[WeeklyScheduleRequest] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    urgentPhone: Optional[str] = None
    estimatedCapacity: Optional[int] = None
    maxOrdersPerSlot: Optional[int] = None
    slotDurationMinutes: Optional[int] = None
    isActive: Optional[bool] = None
    isDefault: Optional[bool] = None
    internalNotes: Optional[str] = None
    pickupInstructions: Optional[str] = None


class CoordinatesResponse(BaseModel):
    lat: float
    lng: float


class DayScheduleResponse(BaseModel):
    open: str
    close: str
    closed: bool


class WeeklyScheduleResponse(BaseModel):
    monday: Optional[DayScheduleResponse] = None
    tuesday: Optional[DayScheduleResponse] = None
    wednesday: Optional[DayScheduleResponse] = None
    thursday: Optional[DayScheduleResponse] = None
    friday: Optional[DayScheduleResponse] = None
    saturday: Optional[DayScheduleResponse] = None
    sunday: Optional[DayScheduleResponse] = None


class PickupLocationResponse(BaseModel):
    id: str
    slug: str
    name: str
    description: Optional[str] = None
    address: str
    city: str
    province: Optional[str] = None
    postalCode: Optional[str] = None
    country: str
    coordinates: Optional[CoordinatesResponse] = None
    operatingHours: Optional[WeeklyScheduleResponse] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    urgentPhone: Optional[str] = None
    estimatedCapacity: int
    maxOrdersPerSlot: Optional[int] = None
    slotDurationMinutes: Optional[int] = None
    isActive: bool
    isDefault: bool
    sortOrder: int
    internalNotes: Optional[str] = None
    pickupInstructions: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class ReorderItem(BaseModel):
    id: str
    sortOrder: int


class ReorderPickupLocationsRequest(BaseModel):
    order: List[ReorderItem]


class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


class PickupLocationListResponse(BaseModel):
    locations: List[PickupLocationResponse]
    pagination: PaginationInfo

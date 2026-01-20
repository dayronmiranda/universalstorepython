"""Admin Pickup Locations Management Endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId
from typing import Optional
import re

from app.database import get_database
from app.api.deps import require_admin
from app.schemas.pickup_location_schema import (
    CreatePickupLocationRequest,
    UpdatePickupLocationRequest,
    PickupLocationResponse,
    PickupLocationListResponse,
    ReorderPickupLocationsRequest,
    PaginationInfo,
)
from app.utils.validators import validate_object_id

router = APIRouter()


def generate_slug(name: str) -> str:
    """Generate URL-friendly slug from name"""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')
    return slug


def convert_location_for_response(location: dict) -> dict:
    """Convert MongoDB location document to response format"""
    return {
        "id": str(location["_id"]),
        "slug": location.get("slug"),
        "name": location.get("name"),
        "description": location.get("description"),
        "address": location.get("address"),
        "city": location.get("city"),
        "province": location.get("province"),
        "postalCode": location.get("postalCode"),
        "country": location.get("country"),
        "coordinates": location.get("coordinates"),
        "operatingHours": location.get("operatingHours"),
        "phone": location.get("phone"),
        "email": location.get("email"),
        "urgentPhone": location.get("urgentPhone"),
        "estimatedCapacity": location.get("estimatedCapacity"),
        "maxOrdersPerSlot": location.get("maxOrdersPerSlot"),
        "slotDurationMinutes": location.get("slotDurationMinutes", 30),
        "isActive": location.get("isActive", True),
        "isDefault": location.get("isDefault", False),
        "sortOrder": location.get("sortOrder", 0),
        "internalNotes": location.get("internalNotes"),
        "pickupInstructions": location.get("pickupInstructions"),
        "createdAt": location.get("createdAt"),
        "updatedAt": location.get("updatedAt"),
    }


# 1. GET /admin/store/pickup-locations - List pickup locations with pagination
@router.get("")
async def list_pickup_locations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    active: Optional[bool] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List pickup locations with pagination (Admin only).
    """
    query = {}
    if active is not None:
        query["isActive"] = active

    skip = (page - 1) * limit
    cursor = db.pickup_locations.find(query).sort("sortOrder", 1).skip(skip).limit(limit)
    locations = await cursor.to_list(length=limit)
    total = await db.pickup_locations.count_documents(query)

    return {
        "success": True,
        "data": {
            "locations": [convert_location_for_response(loc) for loc in locations],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    }


# 2. POST /admin/store/pickup-locations - Create pickup location
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_pickup_location(
    location_data: CreatePickupLocationRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create new pickup location (Admin only).
    """
    # Generate slug if not provided
    if location_data.slug:
        slug = location_data.slug
    else:
        slug = generate_slug(location_data.name)

    # Check slug uniqueness
    existing = await db.pickup_locations.find_one({"slug": slug})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Slug '{slug}' already exists. Please use a different slug or name."
        )

    # Get max sortOrder to append at end
    max_order_result = await db.pickup_locations.find_one(
        {},
        sort=[("sortOrder", -1)]
    )
    next_order = (max_order_result.get("sortOrder", 0) + 1) if max_order_result else 1

    # Build location document
    location_dict = location_data.model_dump(exclude_unset=True, exclude_none=False)
    location_dict["slug"] = slug
    location_dict["sortOrder"] = next_order
    location_dict["createdAt"] = datetime.utcnow()
    location_dict["updatedAt"] = datetime.utcnow()

    result = await db.pickup_locations.insert_one(location_dict)
    location = await db.pickup_locations.find_one({"_id": result.inserted_id})

    return {
        "success": True,
        "message": "Pickup location created successfully",
        "data": convert_location_for_response(location)
    }


# 3. GET /admin/store/pickup-locations/{id} - Get single pickup location
@router.get("/{location_id}")
async def get_pickup_location(
    location_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get pickup location by ID (Admin only).
    """
    if not validate_object_id(location_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid location ID"
        )

    location = await db.pickup_locations.find_one({"_id": ObjectId(location_id)})

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pickup location not found"
        )

    return {
        "success": True,
        "data": convert_location_for_response(location)
    }


# 4. PUT /admin/store/pickup-locations/{id} - Update pickup location
@router.put("/{location_id}")
async def update_pickup_location(
    location_id: str,
    location_data: UpdatePickupLocationRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update pickup location (Admin only).
    """
    if not validate_object_id(location_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid location ID"
        )

    # Check if location exists
    location = await db.pickup_locations.find_one({"_id": ObjectId(location_id)})
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pickup location not found"
        )

    update_dict = location_data.model_dump(exclude_unset=True, exclude_none=False)

    # If slug is being updated, check uniqueness
    if "slug" in update_dict:
        existing = await db.pickup_locations.find_one({
            "slug": update_dict["slug"],
            "_id": {"$ne": ObjectId(location_id)}
        })
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Slug '{update_dict['slug']}' already exists"
            )

    update_dict["updatedAt"] = datetime.utcnow()

    await db.pickup_locations.update_one(
        {"_id": ObjectId(location_id)},
        {"$set": update_dict}
    )

    updated_location = await db.pickup_locations.find_one({"_id": ObjectId(location_id)})

    return {
        "success": True,
        "message": "Pickup location updated successfully",
        "data": convert_location_for_response(updated_location)
    }


# 5. DELETE /admin/store/pickup-locations/{id} - Delete pickup location
@router.delete("/{location_id}")
async def delete_pickup_location(
    location_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete pickup location (Admin only).
    """
    if not validate_object_id(location_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid location ID"
        )

    location = await db.pickup_locations.find_one({"_id": ObjectId(location_id)})

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pickup location not found"
        )

    # Check if this is the default location
    if location.get("isDefault"):
        # Count other locations
        count = await db.pickup_locations.count_documents({})
        if count > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete default pickup location. Please set another location as default first."
            )

    await db.pickup_locations.delete_one({"_id": ObjectId(location_id)})

    return {
        "success": True,
        "message": "Pickup location deleted successfully"
    }


# 6. POST /admin/store/pickup-locations/{id}/toggle - Toggle active status
@router.post("/{location_id}/toggle")
async def toggle_pickup_location(
    location_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Toggle pickup location active status (Admin only).
    """
    if not validate_object_id(location_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid location ID"
        )

    location = await db.pickup_locations.find_one({"_id": ObjectId(location_id)})

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pickup location not found"
        )

    new_status = not location.get("isActive", True)

    # If deactivating and it's the default location, check if there are other active locations
    if not new_status and location.get("isDefault"):
        other_active = await db.pickup_locations.count_documents({
            "_id": {"$ne": ObjectId(location_id)},
            "isActive": True
        })
        if other_active == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the default location when there are no other active locations"
            )

    await db.pickup_locations.update_one(
        {"_id": ObjectId(location_id)},
        {"$set": {"isActive": new_status, "updatedAt": datetime.utcnow()}}
    )

    return {
        "success": True,
        "message": f"Location {'activated' if new_status else 'deactivated'} successfully",
        "data": {"isActive": new_status}
    }


# 7. POST /admin/store/pickup-locations/reorder - Reorder locations
@router.post("/reorder")
async def reorder_pickup_locations(
    reorder_data: ReorderPickupLocationsRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Reorder pickup locations (Admin only).
    """
    # Validate all IDs
    for item in reorder_data.order:
        if not validate_object_id(item.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid location ID: {item.id}"
            )

    # Verify all locations exist
    for item in reorder_data.order:
        location = await db.pickup_locations.find_one({"_id": ObjectId(item.id)})
        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pickup location not found: {item.id}"
            )

    # Update each location's sortOrder
    for item in reorder_data.order:
        await db.pickup_locations.update_one(
            {"_id": ObjectId(item.id)},
            {"$set": {"sortOrder": item.sortOrder, "updatedAt": datetime.utcnow()}}
        )

    return {
        "success": True,
        "message": "Pickup locations reordered successfully"
    }

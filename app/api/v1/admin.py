"""Admin advanced endpoints - Media, Maintenance, Database Management"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId
from typing import List, Optional

from app.database import get_database, database
from app.api.deps import require_admin
from app.schemas.admin_schema import (
    ProductImageUpload,
    MaintenanceToggleRequest,
    DatabaseCreateRequest,
    DatabaseSwitchRequest,
)
from app.utils.validators import validate_object_id

router = APIRouter()


# Media Management endpoints

@router.get("/media/product-images")
async def list_product_images(
    product_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List product images (Admin only).
    """
    query = {}
    if product_id:
        if not validate_object_id(product_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid product ID"
            )
        query["product_id"] = product_id

    skip = (page - 1) * limit
    cursor = db.product_images.find(query).sort("created_at", -1).skip(skip).limit(limit)
    images = await cursor.to_list(length=limit)

    total = await db.product_images.count_documents(query)

    return {
        "success": True,
        "data": {
            "images": [
                {
                    "id": str(img["_id"]),
                    "product_id": img["product_id"],
                    "url": img["url"],
                    "filename": img["filename"],
                    "size": img.get("size"),
                    "mime_type": img.get("mime_type"),
                    "is_primary": img.get("is_primary", False),
                    "alt_text": img.get("alt_text"),
                    "created_at": img.get("created_at")
                }
                for img in images
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    }


@router.post("/media/product-images", status_code=status.HTTP_201_CREATED)
async def upload_product_image(
    image_data: ProductImageUpload,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Upload product image (Admin only).
    In production, this would handle actual file upload to CDN/S3.
    """
    if not validate_object_id(image_data.product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID"
        )

    # Verify product exists
    product = await db.products.find_one({"_id": ObjectId(image_data.product_id)})
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # If setting as primary, unset other primary images for this product
    if image_data.is_primary:
        await db.product_images.update_many(
            {"product_id": image_data.product_id, "is_primary": True},
            {"$set": {"is_primary": False}}
        )

    # Create image record
    image_doc = {
        "product_id": image_data.product_id,
        "url": image_data.url,
        "filename": image_data.filename,
        "size": 0,  # Would be actual file size
        "mime_type": "image/jpeg",  # Would be detected
        "is_primary": image_data.is_primary,
        "alt_text": image_data.alt_text,
        "uploaded_by": current_user["_id"],
        "created_at": datetime.utcnow()
    }

    result = await db.product_images.insert_one(image_doc)

    # Update product images array
    await db.products.update_one(
        {"_id": ObjectId(image_data.product_id)},
        {
            "$addToSet": {"images": image_data.url},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

    if image_data.is_primary:
        await db.products.update_one(
            {"_id": ObjectId(image_data.product_id)},
            {"$set": {"image": image_data.url}}
        )

    return {
        "success": True,
        "message": "Image uploaded successfully",
        "data": {
            "id": str(result.inserted_id),
            "url": image_data.url
        }
    }


@router.delete("/media/product-images/{image_id}")
async def delete_product_image(
    image_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete product image (Admin only).
    """
    if not validate_object_id(image_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image ID"
        )

    image = await db.product_images.find_one({"_id": ObjectId(image_id)})

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    # Delete image record
    await db.product_images.delete_one({"_id": ObjectId(image_id)})

    # Remove from product images array
    await db.products.update_one(
        {"_id": ObjectId(image["product_id"])},
        {
            "$pull": {"images": image["url"]},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

    return {
        "success": True,
        "message": "Image deleted successfully"
    }


# Maintenance Mode endpoints

@router.get("/store/config/maintenance")
async def get_maintenance_config(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get maintenance mode configuration (Admin only).
    """
    config = await db.maintenance_config.find_one({})

    if not config:
        # Return default config
        return {
            "success": True,
            "data": {
                "enabled": False,
                "message": "We are currently performing maintenance. Please check back soon.",
                "allowed_ips": [],
                "scheduled_start": None,
                "scheduled_end": None
            }
        }

    return {
        "success": True,
        "data": {
            "enabled": config.get("enabled", False),
            "message": config.get("message", ""),
            "allowed_ips": config.get("allowed_ips", []),
            "scheduled_start": config.get("scheduled_start"),
            "scheduled_end": config.get("scheduled_end"),
            "updated_at": config.get("updated_at")
        }
    }


@router.post("/store/config/maintenance/toggle")
async def toggle_maintenance_mode(
    toggle_data: MaintenanceToggleRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Toggle maintenance mode (Admin only).
    """
    update_data = {
        "enabled": toggle_data.enabled,
        "updated_by": current_user["_id"],
        "updated_at": datetime.utcnow()
    }

    if toggle_data.message:
        update_data["message"] = toggle_data.message

    # Upsert maintenance config
    await db.maintenance_config.update_one(
        {},
        {"$set": update_data},
        upsert=True
    )

    return {
        "success": True,
        "message": f"Maintenance mode {'enabled' if toggle_data.enabled else 'disabled'}",
        "data": {
            "enabled": toggle_data.enabled
        }
    }


# Database Management endpoints

@router.get("/database/current")
async def get_current_database(
    current_user: dict = Depends(require_admin)
):
    """
    Get current database information (Admin only).
    """
    return {
        "success": True,
        "data": {
            "database_name": database.db.name if database.db else None,
            "connected": database.db is not None
        }
    }


@router.get("/database/list")
async def list_databases(
    current_user: dict = Depends(require_admin)
):
    """
    List all databases (Admin only).
    """
    try:
        db_list = await database.client.list_database_names()
        return {
            "success": True,
            "data": {
                "databases": db_list
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list databases: {str(e)}"
        )


@router.get("/database/stats")
async def get_database_stats(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get database statistics (Admin only).
    """
    try:
        stats = await db.command("dbStats")
        return {
            "success": True,
            "data": {
                "database": stats.get("db"),
                "collections": stats.get("collections"),
                "views": stats.get("views"),
                "objects": stats.get("objects"),
                "dataSize": stats.get("dataSize"),
                "storageSize": stats.get("storageSize"),
                "indexes": stats.get("indexes"),
                "indexSize": stats.get("indexSize")
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get database stats: {str(e)}"
        )


@router.get("/database/status")
async def get_database_status(
    current_user: dict = Depends(require_admin)
):
    """
    Get database health status (Admin only).
    """
    try:
        # Ping database
        await database.db.command("ping")
        server_status = await database.db.command("serverStatus")

        return {
            "success": True,
            "data": {
                "status": "healthy",
                "host": server_status.get("host"),
                "version": server_status.get("version"),
                "uptime": server_status.get("uptime"),
                "connections": server_status.get("connections")
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database is unhealthy: {str(e)}"
        )


@router.post("/database/create", status_code=status.HTTP_201_CREATED)
async def create_database(
    create_data: DatabaseCreateRequest,
    current_user: dict = Depends(require_admin)
):
    """
    Create a new database (Admin only).
    """
    try:
        # MongoDB creates databases on first write
        new_db = database.client[create_data.database_name]
        # Create a dummy collection to initialize the database
        await new_db.create_collection("_init")

        return {
            "success": True,
            "message": f"Database '{create_data.database_name}' created successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create database: {str(e)}"
        )


@router.post("/database/switch")
async def switch_database(
    switch_data: DatabaseSwitchRequest,
    current_user: dict = Depends(require_admin)
):
    """
    Switch to a different database (Admin only).
    WARNING: This changes the active database for all connections!
    """
    try:
        # Verify database exists
        db_list = await database.client.list_database_names()
        if switch_data.database_name not in db_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Database '{switch_data.database_name}' not found"
            )

        # Switch database
        database.db = database.client[switch_data.database_name]

        return {
            "success": True,
            "message": f"Switched to database '{switch_data.database_name}'",
            "data": {
                "current_database": switch_data.database_name
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to switch database: {str(e)}"
        )


@router.get("/database/check/{database_name}")
async def check_database_exists(
    database_name: str,
    current_user: dict = Depends(require_admin)
):
    """
    Check if a database exists (Admin only).
    """
    try:
        db_list = await database.client.list_database_names()
        exists = database_name in db_list

        return {
            "success": True,
            "data": {
                "database_name": database_name,
                "exists": exists
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check database: {str(e)}"
        )


@router.get("/database/collections")
async def list_collections(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List all collections in current database (Admin only).
    """
    try:
        collections = await db.list_collection_names()
        return {
            "success": True,
            "data": {
                "collections": collections,
                "count": len(collections)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collections: {str(e)}"
        )


@router.get("/database/server")
async def get_server_info(
    current_user: dict = Depends(require_admin)
):
    """
    Get MongoDB server information (Admin only).
    """
    try:
        server_info = await database.db.command("buildInfo")
        return {
            "success": True,
            "data": {
                "version": server_info.get("version"),
                "git_version": server_info.get("gitVersion"),
                "modules": server_info.get("modules"),
                "allocator": server_info.get("allocator"),
                "javascript_engine": server_info.get("javascriptEngine")
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get server info: {str(e)}"
        )


@router.get("/jobaudit")
async def list_job_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    job_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List job audit logs (Admin only).
    """
    query = {}
    if job_type:
        query["job_type"] = job_type
    if status:
        query["status"] = status

    skip = (page - 1) * limit
    cursor = db.job_audit.find(query).sort("created_at", -1).skip(skip).limit(limit)
    logs = await cursor.to_list(length=limit)

    total = await db.job_audit.count_documents(query)

    return {
        "success": True,
        "data": {
            "logs": [
                {
                    "id": str(log["_id"]),
                    "job_type": log["job_type"],
                    "status": log["status"],
                    "details": log.get("details"),
                    "error": log.get("error"),
                    "duration_ms": log.get("duration_ms"),
                    "triggered_by": log.get("triggered_by"),
                    "created_at": log.get("created_at")
                }
                for log in logs
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    }


# Public endpoint (no auth required)

router_public = APIRouter()


@router_public.get("/store/maintenance-status")
async def check_maintenance_status(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Check if site is in maintenance mode (Public endpoint).
    """
    config = await db.maintenance_config.find_one({})

    if not config:
        return {
            "success": True,
            "data": {
                "maintenance_mode": False
            }
        }

    return {
        "success": True,
        "data": {
            "maintenance_mode": config.get("enabled", False),
            "message": config.get("message", "") if config.get("enabled") else None,
            "scheduled_end": config.get("scheduled_end") if config.get("enabled") else None
        }
    }

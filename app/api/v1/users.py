"""Admin users and customers management endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId
from typing import List, Optional

from app.database import get_database
from app.api.deps import require_admin
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    CustomerResponse,
)
from app.schemas.common import SuccessResponse
from app.utils.validators import validate_object_id

router = APIRouter()


# Admin User Management

@router.get("/users", response_model=List[UserResponse])
async def list_admin_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_admin)
):
    """
    List admin users (admin, product_manager, support).
    Requires admin role.
    """
    # Build query for non-client users
    query = {"role": {"$ne": "client"}}

    if role and role != "client":
        query["role"] = role

    skip = (page - 1) * limit

    cursor = db.users.find(query).skip(skip).limit(limit).sort("created_at", -1)
    users = await cursor.to_list(length=limit)

    return [
        UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            name=user.get("name"),
            role=user["role"],
            active=user.get("active", True),
            created_at=user.get("created_at", datetime.utcnow()),
            updated_at=user.get("updated_at", datetime.utcnow()),
        )
        for user in users
    ]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    user_data: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_admin)
):
    """
    Create a new admin user.
    Requires admin role.
    """
    # Check if email already exists
    existing_user = await db.users.find_one({"email": user_data.email.lower()})

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Only allow creating non-client users through this endpoint
    if user_data.role == "client":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use customer endpoints to create client users"
        )

    # Create user document
    user_dict = {
        "email": user_data.email.lower(),
        "name": user_data.name,
        "role": user_data.role,
        "active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    result = await db.users.insert_one(user_dict)

    # Fetch created user
    created_user = await db.users.find_one({"_id": result.inserted_id})

    return UserResponse(
        id=str(created_user["_id"]),
        email=created_user["email"],
        name=created_user.get("name"),
        role=created_user["role"],
        active=created_user.get("active", True),
        created_at=created_user.get("created_at", datetime.utcnow()),
        updated_at=created_user.get("updated_at", datetime.utcnow()),
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_admin_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_admin)
):
    """
    Get a specific admin user by ID.
    Requires admin role.
    """
    if not validate_object_id(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    user = await db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Only return non-client users
    if user.get("role") == "client":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        name=user.get("name"),
        role=user["role"],
        active=user.get("active", True),
        created_at=user.get("created_at", datetime.utcnow()),
        updated_at=user.get("updated_at", datetime.utcnow()),
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_admin_user(
    user_id: str,
    user_data: UserUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_admin)
):
    """
    Update an admin user.
    Requires admin role.
    """
    if not validate_object_id(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    user = await db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Only allow updating non-client users
    if user.get("role") == "client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update client users through this endpoint"
        )

    # Build update data
    update_dict = user_data.model_dump(exclude_unset=True)

    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    update_dict["updated_at"] = datetime.utcnow()

    # Update user
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_dict}
    )

    # Fetch updated user
    updated_user = await db.users.find_one({"_id": ObjectId(user_id)})

    return UserResponse(
        id=str(updated_user["_id"]),
        email=updated_user["email"],
        name=updated_user.get("name"),
        role=updated_user["role"],
        active=updated_user.get("active", True),
        created_at=updated_user.get("created_at", datetime.utcnow()),
        updated_at=updated_user.get("updated_at", datetime.utcnow()),
    )


@router.delete("/users/{user_id}", response_model=SuccessResponse)
async def delete_admin_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_admin)
):
    """
    Delete an admin user (soft delete by setting active=False).
    Requires admin role.
    """
    if not validate_object_id(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    # Prevent self-deletion
    if user_id == current_user["_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    user = await db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Only allow deleting non-client users
    if user.get("role") == "client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete client users through this endpoint"
        )

    # Soft delete
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"active": False, "updated_at": datetime.utcnow()}}
    )

    return SuccessResponse(
        success=True,
        message="User deleted successfully"
    )


# Customer Management

@router.get("/customers", response_model=List[CustomerResponse])
async def list_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_admin)
):
    """
    List customer users (clients with stats).
    Requires admin role.
    """
    # Build query for client users
    query = {"role": "client"}

    if search:
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}},
        ]

    skip = (page - 1) * limit

    cursor = db.users.find(query).skip(skip).limit(limit).sort("created_at", -1)
    customers = await cursor.to_list(length=limit)

    return [
        CustomerResponse(
            id=str(customer["_id"]),
            email=customer["email"],
            name=customer.get("name"),
            phone=customer.get("phone"),
            role=customer["role"],
            active=customer.get("active", True),
            order_count=customer.get("order_count", 0),
            total_spent=customer.get("total_spent", 0.0),
            last_order_date=customer.get("last_order_date"),
            created_at=customer.get("created_at", datetime.utcnow()),
            updated_at=customer.get("updated_at", datetime.utcnow()),
        )
        for customer in customers
    ]


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_admin)
):
    """
    Get a specific customer by ID with stats.
    Requires admin role.
    """
    if not validate_object_id(customer_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer ID"
        )

    customer = await db.users.find_one({"_id": ObjectId(customer_id), "role": "client"})

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    return CustomerResponse(
        id=str(customer["_id"]),
        email=customer["email"],
        name=customer.get("name"),
        phone=customer.get("phone"),
        role=customer["role"],
        active=customer.get("active", True),
        order_count=customer.get("order_count", 0),
        total_spent=customer.get("total_spent", 0.0),
        last_order_date=customer.get("last_order_date"),
        created_at=customer.get("created_at", datetime.utcnow()),
        updated_at=customer.get("updated_at", datetime.utcnow()),
    )


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    active: bool,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_admin)
):
    """
    Update user active status (Admin only).
    Requires admin role.
    """
    if not validate_object_id(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    # Prevent self-deactivation
    if user_id == current_user["_id"] and not active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )

    user = await db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update user status
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"active": active, "updated_at": datetime.utcnow()}}
    )

    return {
        "success": True,
        "message": f"User {'activated' if active else 'deactivated'} successfully"
    }


@router.get("/customers/{customer_id}/orders")
async def get_customer_orders(
    customer_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_admin)
):
    """
    Get all orders for a specific customer (Admin only).
    Requires admin role.
    """
    if not validate_object_id(customer_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer ID"
        )

    # Verify customer exists
    customer = await db.users.find_one({"_id": ObjectId(customer_id), "role": "client"})

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    # Get customer orders
    skip = (page - 1) * limit
    cursor = db.orders.find({"user_id": customer_id}).sort("created_at", -1).skip(skip).limit(limit)
    orders = await cursor.to_list(length=limit)

    # Format orders
    formatted_orders = []
    for order in orders:
        formatted_orders.append({
            "id": str(order["_id"]),
            "order_number": order["order_number"],
            "total": order.get("total", 0.0),
            "status": order.get("status", "pending"),
            "payment_status": order.get("payment_status", "pending"),
            "item_count": len(order.get("items", [])),
            "created_at": order.get("created_at", datetime.utcnow()),
        })

    # Get total count
    total_orders = await db.orders.count_documents({"user_id": customer_id})

    return {
        "success": True,
        "data": {
            "customer": {
                "id": str(customer["_id"]),
                "email": customer["email"],
                "name": customer.get("name")
            },
            "orders": formatted_orders,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_orders,
                "pages": (total_orders + limit - 1) // limit
            }
        }
    }

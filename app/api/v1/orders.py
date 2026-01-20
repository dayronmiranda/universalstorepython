"""Orders and Cart endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from bson import ObjectId
from typing import List, Optional
import secrets

from app.database import get_database
from app.api.deps import get_current_user, require_admin
from app.schemas.order import (
    CartCreate,
    CartUpdate,
    CartResponse,
    CartItemResponse,
    OrderCreate,
    OrderResponse,
    OrderItemResponse,
    OrderStatusUpdate,
    OrderNoteCreate,
)
from app.schemas.common import SuccessResponse
from app.utils.validators import validate_object_id

router = APIRouter()


# Helper functions

async def calculate_cart_items(items_input: list, db: AsyncIOMotorDatabase) -> tuple:
    """
    Calculate cart items with current prices and validate stock availability.
    Returns (cart_items, total)
    """
    cart_items = []
    total = 0.0

    for item in items_input:
        product_id = item.product_id
        quantity = item.quantity

        if not validate_object_id(product_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid product ID: {product_id}"
            )

        product = await db.products.find_one({"_id": ObjectId(product_id), "active": True})

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product not found: {product_id}"
            )

        # Calculate available stock
        available_stock = product.get("stock", 0) - product.get("reserved_stock", 0)

        if available_stock < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product '{product['name']}'. Available: {available_stock}"
            )

        # Calculate price (use sale_price if on_sale, otherwise regular price)
        unit_price = product.get("sale_price", product["price"]) if product.get("on_sale") else product["price"]
        subtotal = unit_price * quantity

        cart_items.append({
            "product_id": str(product["_id"]),
            "name": product["name"],
            "product_image": product.get("image"),
            "quantity": quantity,
            "unit_price": unit_price,
            "subtotal": subtotal,
        })

        total += subtotal

    return cart_items, total


async def reserve_stock(cart_items: list, db: AsyncIOMotorDatabase):
    """Reserve stock for cart items"""
    for item in cart_items:
        await db.products.update_one(
            {"_id": ObjectId(item["product_id"])},
            {"$inc": {"reserved_stock": item["quantity"]}}
        )


async def release_stock(cart_items: list, db: AsyncIOMotorDatabase):
    """Release reserved stock for cart items"""
    for item in cart_items:
        await db.products.update_one(
            {"_id": ObjectId(item["product_id"])},
            {"$inc": {"reserved_stock": -item["quantity"]}}
        )


def generate_order_number() -> str:
    """Generate unique order number"""
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    random_suffix = secrets.token_hex(4).upper()
    return f"ORD-{timestamp}-{random_suffix}"


# Cart endpoints

@router.get("/carts", response_model=CartResponse)
async def get_or_create_cart(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get current user's cart or create a new one if it doesn't exist.
    """
    user_id = current_user["_id"]

    # Find existing cart
    cart = await db.carts.find_one({"user_id": user_id})

    if not cart:
        # Create new empty cart
        cart_data = {
            "user_id": user_id,
            "items": [],
            "total": 0.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = await db.carts.insert_one(cart_data)
        cart = await db.carts.find_one({"_id": result.inserted_id})

    return CartResponse(
        id=str(cart["_id"]),
        user_id=cart["user_id"],
        items=[CartItemResponse(**item) for item in cart.get("items", [])],
        total=cart.get("total", 0.0),
        reserved_until=cart.get("reserved_until"),
        created_at=cart.get("created_at", datetime.utcnow()),
        updated_at=cart.get("updated_at", datetime.utcnow()),
    )


@router.post("/carts", response_model=CartResponse)
async def create_cart_with_items(
    cart_data: CartCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create or update cart with items and reserve stock.
    """
    user_id = current_user["_id"]

    # Calculate cart items and validate stock
    cart_items, total = await calculate_cart_items(cart_data.items, db)

    # Find existing cart
    existing_cart = await db.carts.find_one({"user_id": user_id})

    if existing_cart:
        # Release old stock reservations
        if existing_cart.get("items"):
            await release_stock(existing_cart["items"], db)

        # Update cart
        await db.carts.update_one(
            {"_id": existing_cart["_id"]},
            {
                "$set": {
                    "items": cart_items,
                    "total": total,
                    "reserved_until": datetime.utcnow() + timedelta(minutes=15),
                    "updated_at": datetime.utcnow(),
                }
            }
        )
        cart_id = existing_cart["_id"]
    else:
        # Create new cart
        cart_doc = {
            "user_id": user_id,
            "items": cart_items,
            "total": total,
            "reserved_until": datetime.utcnow() + timedelta(minutes=15),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = await db.carts.insert_one(cart_doc)
        cart_id = result.inserted_id

    # Reserve stock
    await reserve_stock(cart_items, db)

    # Fetch and return cart
    cart = await db.carts.find_one({"_id": cart_id})

    return CartResponse(
        id=str(cart["_id"]),
        user_id=cart["user_id"],
        items=[CartItemResponse(**item) for item in cart.get("items", [])],
        total=cart.get("total", 0.0),
        reserved_until=cart.get("reserved_until"),
        created_at=cart.get("created_at", datetime.utcnow()),
        updated_at=cart.get("updated_at", datetime.utcnow()),
    )


@router.put("/carts/{cart_id}", response_model=CartResponse)
async def update_cart(
    cart_id: str,
    cart_data: CartUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update cart items and stock reservations.
    """
    if not validate_object_id(cart_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cart ID"
        )

    user_id = current_user["_id"]

    # Find cart
    cart = await db.carts.find_one({"_id": ObjectId(cart_id), "user_id": user_id})

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )

    # Release old stock reservations
    if cart.get("items"):
        await release_stock(cart["items"], db)

    # Calculate new cart items
    cart_items, total = await calculate_cart_items(cart_data.items, db)

    # Update cart
    await db.carts.update_one(
        {"_id": ObjectId(cart_id)},
        {
            "$set": {
                "items": cart_items,
                "total": total,
                "reserved_until": datetime.utcnow() + timedelta(minutes=15),
                "updated_at": datetime.utcnow(),
            }
        }
    )

    # Reserve new stock
    await reserve_stock(cart_items, db)

    # Fetch and return updated cart
    updated_cart = await db.carts.find_one({"_id": ObjectId(cart_id)})

    return CartResponse(
        id=str(updated_cart["_id"]),
        user_id=updated_cart["user_id"],
        items=[CartItemResponse(**item) for item in updated_cart.get("items", [])],
        total=updated_cart.get("total", 0.0),
        reserved_until=updated_cart.get("reserved_until"),
        created_at=updated_cart.get("created_at", datetime.utcnow()),
        updated_at=updated_cart.get("updated_at", datetime.utcnow()),
    )


@router.delete("/carts/{cart_id}", response_model=SuccessResponse)
async def clear_cart(
    cart_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Clear cart and release stock reservations.
    """
    if not validate_object_id(cart_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cart ID"
        )

    user_id = current_user["_id"]

    # Find cart
    cart = await db.carts.find_one({"_id": ObjectId(cart_id), "user_id": user_id})

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )

    # Release stock reservations
    if cart.get("items"):
        await release_stock(cart["items"], db)

    # Clear cart
    await db.carts.update_one(
        {"_id": ObjectId(cart_id)},
        {
            "$set": {
                "items": [],
                "total": 0.0,
                "reserved_until": None,
                "updated_at": datetime.utcnow(),
            }
        }
    )

    return SuccessResponse(
        success=True,
        message="Cart cleared successfully"
    )


@router.post("/carts/{cart_id}/keep-alive")
async def keep_cart_alive(
    cart_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Keep cart alive by extending expiration time by 30 minutes.
    """
    if not validate_object_id(cart_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cart ID"
        )

    user_id = current_user["_id"]

    # Find cart
    cart = await db.carts.find_one({"_id": ObjectId(cart_id), "user_id": user_id})

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )

    # Check if cart has items
    if not cart.get("items"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot extend expiration of empty cart"
        )

    # Extend expiration by 30 minutes
    new_expiration = datetime.utcnow() + timedelta(minutes=30)

    await db.carts.update_one(
        {"_id": ObjectId(cart_id)},
        {
            "$set": {
                "reserved_until": new_expiration,
                "updated_at": datetime.utcnow(),
            }
        }
    )

    return {
        "success": True,
        "data": {
            "message": "Cart expiration extended",
            "expiresAt": new_expiration.isoformat()
        }
    }


@router.get("/carts/{cart_id}/status")
async def get_cart_status(
    cart_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get cart expiration status and time remaining.
    Returns status: active (>5 min), expiring_soon (1-5 min), or expired (<=0 min).
    """
    if not validate_object_id(cart_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cart ID"
        )

    user_id = current_user["_id"]

    # Find cart
    cart = await db.carts.find_one({"_id": ObjectId(cart_id), "user_id": user_id})

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )

    # Calculate time remaining
    reserved_until = cart.get("reserved_until")
    now = datetime.utcnow()

    if not reserved_until:
        # No expiration set (empty cart)
        minutes_remaining = 0
        status_str = "expired"
        expires_at = None
    else:
        time_delta = reserved_until - now
        minutes_remaining = time_delta.total_seconds() / 60
        expires_at = reserved_until.isoformat()

        # Determine status based on minutes remaining
        if minutes_remaining <= 0:
            status_str = "expired"
        elif minutes_remaining <= 5:
            status_str = "expiring_soon"
        else:
            status_str = "active"

    # Get cart stats
    item_count = len(cart.get("items", []))
    total_value = cart.get("total", 0.0)

    return {
        "success": True,
        "data": {
            "cartId": str(cart["_id"]),
            "status": status_str,
            "minutesRemaining": max(0, minutes_remaining),
            "expiresAt": expires_at,
            "itemCount": item_count,
            "totalValue": total_value
        }
    }


# Order endpoints

@router.get("/orders", response_model=List[OrderResponse])
async def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List current user's orders.
    """
    user_id = current_user["_id"]

    skip = (page - 1) * limit

    cursor = db.orders.find({"user_id": user_id}).sort("created_at", -1).skip(skip).limit(limit)
    orders = await cursor.to_list(length=limit)

    return [
        OrderResponse(
            id=str(order["_id"]),
            order_number=order["order_number"],
            user_id=order["user_id"],
            items=[OrderItemResponse(**item) for item in order.get("items", [])],
            total=order.get("total", 0.0),
            status=order.get("status", "pending"),
            payment_status=order.get("payment_status", "pending"),
            payment_intent_id=order.get("payment_intent_id"),
            shipping_address=order.get("shipping_address"),
            customer_email=order.get("customer_email"),
            customer_name=order.get("customer_name"),
            notes=order.get("notes"),
            created_at=order.get("created_at", datetime.utcnow()),
            updated_at=order.get("updated_at", datetime.utcnow()),
        )
        for order in orders
    ]


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create an order from cart or with new items.
    Stock is moved from reserved to actual order, cart is cleared.
    """
    user_id = current_user["_id"]

    # Get cart if cart_id provided
    if order_data.cart_id:
        if not validate_object_id(order_data.cart_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cart ID"
            )

        cart = await db.carts.find_one({"_id": ObjectId(order_data.cart_id), "user_id": user_id})

        if not cart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart not found"
            )

        if not cart.get("items"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cart is empty"
            )

        order_items = cart["items"]
        total = cart["total"]
    else:
        # No cart specified, would need items in order_data (not in schema currently)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cart_id is required"
        )

    # Generate order number
    order_number = generate_order_number()

    # Create order document
    order_doc = {
        "order_number": order_number,
        "user_id": user_id,
        "items": order_items,
        "total": total,
        "status": "pending",
        "payment_status": "pending",
        "shipping_address": order_data.shipping_address.model_dump() if order_data.shipping_address else None,
        "customer_email": order_data.customer_email or current_user.get("email"),
        "customer_name": order_data.customer_name or current_user.get("name"),
        "notes": order_data.notes,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    result = await db.orders.insert_one(order_doc)

    # Convert reserved stock to actual stock reduction
    for item in order_items:
        await db.products.update_one(
            {"_id": ObjectId(item["product_id"])},
            {
                "$inc": {
                    "stock": -item["quantity"],
                    "reserved_stock": -item["quantity"]
                }
            }
        )

    # Clear cart
    if order_data.cart_id:
        await db.carts.update_one(
            {"_id": ObjectId(order_data.cart_id)},
            {
                "$set": {
                    "items": [],
                    "total": 0.0,
                    "reserved_until": None,
                    "updated_at": datetime.utcnow(),
                }
            }
        )

    # Update user stats
    await db.users.update_one(
        {"_id": user_id},
        {
            "$inc": {"order_count": 1, "total_spent": total},
            "$set": {"last_order_date": datetime.utcnow()}
        }
    )

    # Fetch created order
    created_order = await db.orders.find_one({"_id": result.inserted_id})

    return OrderResponse(
        id=str(created_order["_id"]),
        order_number=created_order["order_number"],
        user_id=created_order["user_id"],
        items=[OrderItemResponse(**item) for item in created_order.get("items", [])],
        total=created_order.get("total", 0.0),
        status=created_order.get("status", "pending"),
        payment_status=created_order.get("payment_status", "pending"),
        payment_intent_id=created_order.get("payment_intent_id"),
        shipping_address=created_order.get("shipping_address"),
        customer_email=created_order.get("customer_email"),
        customer_name=created_order.get("customer_name"),
        notes=created_order.get("notes"),
        created_at=created_order.get("created_at", datetime.utcnow()),
        updated_at=created_order.get("updated_at", datetime.utcnow()),
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get a specific order by ID.
    Users can only access their own orders unless they are admin.
    """
    if not validate_object_id(order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID"
        )

    order = await db.orders.find_one({"_id": ObjectId(order_id)})

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Check ownership or admin
    if order["user_id"] != current_user["_id"] and current_user.get("role") not in ["admin", "support"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this order"
        )

    return OrderResponse(
        id=str(order["_id"]),
        order_number=order["order_number"],
        user_id=order["user_id"],
        items=[OrderItemResponse(**item) for item in order.get("items", [])],
        total=order.get("total", 0.0),
        status=order.get("status", "pending"),
        payment_status=order.get("payment_status", "pending"),
        payment_intent_id=order.get("payment_intent_id"),
        shipping_address=order.get("shipping_address"),
        customer_email=order.get("customer_email"),
        customer_name=order.get("customer_name"),
        notes=order.get("notes"),
        created_at=order.get("created_at", datetime.utcnow()),
        updated_at=order.get("updated_at", datetime.utcnow()),
    )


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Cancel an order and restore stock.
    Only pending or paid orders can be cancelled.
    """
    if not validate_object_id(order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID"
        )

    order = await db.orders.find_one({"_id": ObjectId(order_id)})

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Check ownership or admin
    if order["user_id"] != current_user["_id"] and current_user.get("role") not in ["admin", "support"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this order"
        )

    # Check if order can be cancelled
    if order.get("status") not in ["pending", "paid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order with status '{order.get('status')}'"
        )

    # Restore stock
    for item in order.get("items", []):
        await db.products.update_one(
            {"_id": ObjectId(item["product_id"])},
            {"$inc": {"stock": item["quantity"]}}
        )

    # Update order status
    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {
            "$set": {
                "status": "cancelled",
                "updated_at": datetime.utcnow(),
            }
        }
    )

    # Fetch updated order
    updated_order = await db.orders.find_one({"_id": ObjectId(order_id)})

    return OrderResponse(
        id=str(updated_order["_id"]),
        order_number=updated_order["order_number"],
        user_id=updated_order["user_id"],
        items=[OrderItemResponse(**item) for item in updated_order.get("items", [])],
        total=updated_order.get("total", 0.0),
        status=updated_order.get("status", "pending"),
        payment_status=updated_order.get("payment_status", "pending"),
        payment_intent_id=updated_order.get("payment_intent_id"),
        shipping_address=updated_order.get("shipping_address"),
        customer_email=updated_order.get("customer_email"),
        customer_name=updated_order.get("customer_name"),
        notes=updated_order.get("notes"),
        created_at=updated_order.get("created_at", datetime.utcnow()),
        updated_at=updated_order.get("updated_at", datetime.utcnow()),
    )

@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update order status (Admin only).
    """
    if not validate_object_id(order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID"
        )

    order = await db.orders.find_one({"_id": ObjectId(order_id)})

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Update order status
    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {
            "$set": {
                "status": status_update.status,
                "updated_at": datetime.utcnow(),
            }
        }
    )

    # Fetch updated order
    updated_order = await db.orders.find_one({"_id": ObjectId(order_id)})

    return OrderResponse(
        id=str(updated_order["_id"]),
        order_number=updated_order["order_number"],
        user_id=updated_order["user_id"],
        items=[OrderItemResponse(**item) for item in updated_order.get("items", [])],
        total=updated_order.get("total", 0.0),
        status=updated_order.get("status", "pending"),
        payment_status=updated_order.get("payment_status", "pending"),
        payment_intent_id=updated_order.get("payment_intent_id"),
        shipping_address=updated_order.get("shipping_address"),
        customer_email=updated_order.get("customer_email"),
        customer_name=updated_order.get("customer_name"),
        notes=updated_order.get("notes"),
        created_at=updated_order.get("created_at", datetime.utcnow()),
        updated_at=updated_order.get("updated_at", datetime.utcnow()),
    )


@router.post("/orders/{order_id}/notes")
async def add_order_note(
    order_id: str,
    note_data: OrderNoteCreate,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Add note to order (Admin only).
    """
    if not validate_object_id(order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID"
        )

    order = await db.orders.find_one({"_id": ObjectId(order_id)})

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Create note entry
    note_entry = {
        "note": note_data.note,
        "created_by": current_user["_id"],
        "created_by_name": current_user.get("name") or current_user.get("email"),
        "created_at": datetime.utcnow()
    }

    # Add note to order
    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {
            "$push": {"notes_history": note_entry},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

    return {
        "success": True,
        "message": "Note added successfully",
        "data": note_entry
    }


@router.get("/orders/all", response_model=List[OrderResponse])
async def list_all_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List all orders (Admin only).
    """
    # Build query
    query = {}

    if status:
        query["status"] = status

    if search:
        query["$or"] = [
            {"order_number": {"$regex": search, "$options": "i"}},
            {"customer_email": {"$regex": search, "$options": "i"}},
            {"customer_name": {"$regex": search, "$options": "i"}},
        ]

    skip = (page - 1) * limit

    cursor = db.orders.find(query).sort("created_at", -1).skip(skip).limit(limit)
    orders = await cursor.to_list(length=limit)

    return [
        OrderResponse(
            id=str(order["_id"]),
            order_number=order["order_number"],
            user_id=order["user_id"],
            items=[OrderItemResponse(**item) for item in order.get("items", [])],
            total=order.get("total", 0.0),
            status=order.get("status", "pending"),
            payment_status=order.get("payment_status", "pending"),
            payment_intent_id=order.get("payment_intent_id"),
            shipping_address=order.get("shipping_address"),
            customer_email=order.get("customer_email"),
            customer_name=order.get("customer_name"),
            notes=order.get("notes"),
            created_at=order.get("created_at", datetime.utcnow()),
            updated_at=order.get("updated_at", datetime.utcnow()),
        )
        for order in orders
    ]


@router.get("/orders/pending-items")
async def get_pending_items(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get stats about pending order items (Admin only).
    Returns counts by status and total value.
    """
    # Aggregate pending orders
    pipeline = [
        {
            "$match": {
                "status": {"$in": ["pending", "paid", "processing"]}
            }
        },
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "total_value": {"$sum": "$total"},
                "total_items": {
                    "$sum": {
                        "$reduce": {
                            "input": "$items",
                            "initialValue": 0,
                            "in": {"$add": ["$$value", "$$this.quantity"]}
                        }
                    }
                }
            }
        }
    ]

    results = await db.orders.aggregate(pipeline).to_list(length=None)

    # Format response
    stats_by_status = {}
    total_orders = 0
    total_value = 0.0
    total_items = 0

    for result in results:
        status_name = result["_id"]
        stats_by_status[status_name] = {
            "orderCount": result["count"],
            "totalValue": result["total_value"],
            "itemCount": result["total_items"]
        }
        total_orders += result["count"]
        total_value += result["total_value"]
        total_items += result["total_items"]

    return {
        "success": True,
        "data": {
            "summary": {
                "totalOrders": total_orders,
                "totalValue": total_value,
                "totalItems": total_items
            },
            "byStatus": stats_by_status
        }
    }


# Pickup Locations endpoints

@router.get("/pickup-locations")
async def list_pickup_locations(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List all active pickup locations (Public).
    """
    cursor = db.pickup_locations.find({"active": True})
    locations = await cursor.to_list(length=None)

    return {
        "success": True,
        "data": [
            {
                "id": str(loc["_id"]),
                "name": loc["name"],
                "address": loc.get("address"),
                "phone": loc.get("phone"),
                "email": loc.get("email"),
                "available_slots": loc.get("available_slots", []),
                "instructions": loc.get("instructions")
            }
            for loc in locations
        ]
    }


@router.post("/{order_id}/pickup/confirm")
async def confirm_pickup(
    order_id: str,
    location_id: str,
    pickup_date: datetime,
    notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Confirm pickup for an order.
    """
    if not validate_object_id(order_id) or not validate_object_id(location_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID or location ID"
        )

    order = await db.orders.find_one({"_id": ObjectId(order_id)})

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Check ownership
    if order["user_id"] != current_user["_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    # Verify location exists
    location = await db.pickup_locations.find_one({"_id": ObjectId(location_id), "active": True})
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pickup location not found"
        )

    # Generate pickup code
    import secrets
    pickup_code = f"PICK-{secrets.token_hex(4).upper()}"

    # Create pickup confirmation
    pickup_data = {
        "order_id": order_id,
        "location_id": location_id,
        "location_name": location["name"],
        "pickup_date": pickup_date,
        "pickup_code": pickup_code,
        "confirmed": False,
        "notes": notes,
        "created_at": datetime.utcnow()
    }

    await db.pickup_confirmations.insert_one(pickup_data)

    # Update order
    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {
            "$set": {
                "pickup_code": pickup_code,
                "pickup_location_id": location_id,
                "pickup_date": pickup_date,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "success": True,
        "message": "Pickup confirmed",
        "data": {
            "pickup_code": pickup_code,
            "location": location["name"],
            "pickup_date": pickup_date.isoformat()
        }
    }


@router.post("/pickup/verify")
async def verify_pickup_code(
    pickup_code: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Verify pickup code (Admin only - for warehouse staff).
    """
    order = await db.orders.find_one({"pickup_code": pickup_code})

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid pickup code"
        )

    # Mark as picked up
    await db.orders.update_one(
        {"_id": order["_id"]},
        {
            "$set": {
                "status": "delivered",
                "pickup_confirmed_at": datetime.utcnow(),
                "pickup_confirmed_by": current_user["_id"],
                "updated_at": datetime.utcnow()
            }
        }
    )

    await db.pickup_confirmations.update_one(
        {"pickup_code": pickup_code},
        {
            "$set": {
                "confirmed": True,
                "confirmed_at": datetime.utcnow(),
                "confirmed_by": current_user["_id"]
            }
        }
    )

    return {
        "success": True,
        "message": "Pickup verified successfully",
        "data": {
            "order_number": order["order_number"],
            "customer_name": order.get("customer_name"),
            "customer_email": order.get("customer_email")
        }
    }


@router.get("/pickup/suggest-times")
async def suggest_pickup_times(
    location_id: str,
    preferred_date: Optional[datetime] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Suggest available pickup times for a location.
    """
    if not validate_object_id(location_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid location ID"
        )

    location = await db.pickup_locations.find_one({"_id": ObjectId(location_id), "active": True})

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pickup location not found"
        )

    # Get available slots for the location
    available_slots = location.get("available_slots", [])

    # If preferred date provided, filter by day of week
    if preferred_date:
        day_of_week = preferred_date.weekday()
        available_slots = [slot for slot in available_slots if slot.get("day_of_week") == day_of_week]

    # Generate suggested times for next 7 days
    from datetime import timedelta
    today = datetime.utcnow()
    suggested_times = []

    for i in range(7):
        check_date = today + timedelta(days=i)
        day_of_week = check_date.weekday()

        for slot in available_slots:
            if slot.get("day_of_week") == day_of_week:
                suggested_times.append({
                    "date": check_date.date().isoformat(),
                    "day_of_week": day_of_week,
                    "start_time": slot.get("start_time"),
                    "end_time": slot.get("end_time"),
                    "available": True
                })

    return {
        "success": True,
        "data": {
            "location": {
                "id": str(location["_id"]),
                "name": location["name"]
            },
            "suggested_times": suggested_times[:20]  # Limit to 20 suggestions
        }
    }


# Stats & Analytics endpoint

@router.get("/payment-stats")
async def get_payment_stats(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get payment statistics (Admin only).
    """
    from datetime import timedelta

    start_date = datetime.utcnow() - timedelta(days=days)

    pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {
            "$facet": {
                "total": [{"$count": "count"}],
                "revenue": [{"$group": {"_id": None, "total": {"$sum": "$total"}}}],
                "by_status": [
                    {"$group": {"_id": "$payment_status", "count": {"$sum": 1}, "amount": {"$sum": "$total"}}}
                ],
                "by_date": [
                    {
                        "$group": {
                            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                            "orders": {"$sum": 1},
                            "revenue": {"$sum": "$total"}
                        }
                    },
                    {"$sort": {"_id": 1}}
                ]
            }
        }
    ]

    result = await db.orders.aggregate(pipeline).to_list(length=1)

    if not result:
        return {
            "success": True,
            "data": {
                "total_orders": 0,
                "total_revenue": 0.0,
                "by_status": {},
                "timeline": []
            }
        }

    data = result[0]

    # Format status breakdown
    by_status = {}
    refunded_amount = 0.0

    for status_data in data.get("by_status", []):
        status_name = status_data["_id"] or "unknown"
        by_status[status_name] = {
            "count": status_data["count"],
            "amount": status_data["amount"]
        }
        if status_name == "refunded":
            refunded_amount = status_data["amount"]

    return {
        "success": True,
        "data": {
            "period_days": days,
            "total_orders": data["total"][0]["count"] if data["total"] else 0,
            "total_revenue": data["revenue"][0]["total"] if data["revenue"] else 0.0,
            "pending_payments": by_status.get("pending", {}).get("count", 0),
            "failed_payments": by_status.get("failed", {}).get("count", 0),
            "refunded_amount": refunded_amount,
            "by_status": by_status,
            "timeline": [
                {
                    "date": entry["_id"],
                    "orders": entry["orders"],
                    "revenue": entry["revenue"]
                }
                for entry in data.get("by_date", [])
            ]
        }
    }

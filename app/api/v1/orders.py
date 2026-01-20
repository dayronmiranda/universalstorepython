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

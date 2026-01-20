"""Payments endpoints using Stripe"""

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel
from typing import Optional

from app.database import get_database
from app.api.deps import get_current_user
from app.core.stripe_client import (
    create_checkout_session,
    create_payment_intent,
    retrieve_checkout_session
)
from app.utils.validators import validate_object_id

router = APIRouter()


# Request/Response schemas

class CheckoutSessionRequest(BaseModel):
    """Request schema for creating a checkout session"""
    order_id: str
    success_url: str
    cancel_url: str

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "507f1f77bcf86cd799439011",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel"
            }
        }


class CheckoutSessionResponse(BaseModel):
    """Response schema for checkout session"""
    success: bool = True
    session_id: str
    url: str


class PaymentIntentRequest(BaseModel):
    """Request schema for creating a payment intent"""
    order_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "507f1f77bcf86cd799439011"
            }
        }


class PaymentIntentResponse(BaseModel):
    """Response schema for payment intent"""
    success: bool = True
    client_secret: str
    payment_intent_id: str


class VerifyPaymentRequest(BaseModel):
    """Request schema for verifying payment"""
    session_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "cs_test_a1b2c3d4e5f6g7h8i9j0"
            }
        }


class VerifyPaymentResponse(BaseModel):
    """Response schema for payment verification"""
    success: bool = True
    order_id: str
    payment_status: str
    order_status: str


# Endpoints

@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_stripe_checkout(
    request: CheckoutSessionRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a Stripe Checkout session for an order.
    """
    if not validate_object_id(request.order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID"
        )

    # Get order
    order = await db.orders.find_one({"_id": ObjectId(request.order_id)})

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Check ownership
    if order["user_id"] != current_user["_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this order"
        )

    # Check order status
    if order.get("status") not in ["pending"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order cannot be paid. Current status: " + order.get("status", "unknown")
        )

    # Prepare line items for Stripe
    line_items = []
    for item in order.get("items", []):
        line_items.append({
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": item["name"],
                    "images": [item["product_image"]] if item.get("product_image") else [],
                },
                "unit_amount": int(item["unit_price"] * 100),  # Convert to cents
            },
            "quantity": item["quantity"],
        })

    # Create Stripe checkout session
    try:
        session = await create_checkout_session(
            line_items=line_items,
            customer_email=order.get("customer_email") or current_user.get("email"),
            success_url=request.success_url + f"?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=request.cancel_url,
            metadata={
                "order_id": str(order["_id"]),
                "order_number": order["order_number"],
                "user_id": current_user["_id"],
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}"
        )

    # Store session ID in order
    await db.orders.update_one(
        {"_id": ObjectId(request.order_id)},
        {
            "$set": {
                "stripe_session_id": session.id,
                "updated_at": datetime.utcnow(),
            }
        }
    )

    return CheckoutSessionResponse(
        success=True,
        session_id=session.id,
        url=session.url
    )


@router.get("/checkout/{session_id}")
async def get_checkout_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get details of a Stripe Checkout session.
    """
    try:
        session = await retrieve_checkout_session(session_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checkout session not found: {str(e)}"
        )

    # Get order from metadata
    order_id = session.metadata.get("order_id")

    if not order_id or not validate_object_id(order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID in session metadata"
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
            detail="Not authorized to access this session"
        )

    return {
        "success": True,
        "session": {
            "id": session.id,
            "payment_status": session.payment_status,
            "status": session.status,
            "amount_total": session.amount_total,
            "currency": session.currency,
            "customer_email": session.customer_email,
        },
        "order_id": order_id,
    }


@router.post("/intent", response_model=PaymentIntentResponse)
async def create_stripe_payment_intent(
    request: PaymentIntentRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a Stripe Payment Intent for an order (for custom payment flows).
    """
    if not validate_object_id(request.order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID"
        )

    # Get order
    order = await db.orders.find_one({"_id": ObjectId(request.order_id)})

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Check ownership
    if order["user_id"] != current_user["_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this order"
        )

    # Check order status
    if order.get("status") not in ["pending"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order cannot be paid. Current status: " + order.get("status", "unknown")
        )

    # Create payment intent
    amount_cents = int(order["total"] * 100)  # Convert to cents

    try:
        payment_intent = await create_payment_intent(
            amount=amount_cents,
            currency="usd",
            customer_email=order.get("customer_email") or current_user.get("email"),
            metadata={
                "order_id": str(order["_id"]),
                "order_number": order["order_number"],
                "user_id": current_user["_id"],
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment intent: {str(e)}"
        )

    # Store payment intent ID in order
    await db.orders.update_one(
        {"_id": ObjectId(request.order_id)},
        {
            "$set": {
                "payment_intent_id": payment_intent.id,
                "updated_at": datetime.utcnow(),
            }
        }
    )

    return PaymentIntentResponse(
        success=True,
        client_secret=payment_intent.client_secret,
        payment_intent_id=payment_intent.id
    )


@router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_payment(
    request: VerifyPaymentRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Verify payment status after Stripe checkout/payment.
    Updates order status based on payment status.
    """
    try:
        session = await retrieve_checkout_session(request.session_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checkout session not found: {str(e)}"
        )

    # Get order from metadata
    order_id = session.metadata.get("order_id")

    if not order_id or not validate_object_id(order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID in session metadata"
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
            detail="Not authorized to access this order"
        )

    # Update order based on payment status
    payment_status = "pending"
    order_status = order.get("status", "pending")

    if session.payment_status == "paid":
        payment_status = "completed"
        order_status = "paid"
    elif session.payment_status == "unpaid":
        payment_status = "pending"
    elif session.payment_status == "failed":
        payment_status = "failed"

    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {
            "$set": {
                "payment_status": payment_status,
                "status": order_status,
                "payment_intent_id": session.payment_intent,
                "updated_at": datetime.utcnow(),
            }
        }
    )

    return VerifyPaymentResponse(
        success=True,
        order_id=order_id,
        payment_status=payment_status,
        order_status=order_status
    )

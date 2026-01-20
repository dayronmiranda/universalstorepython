"""Payments endpoints using Stripe"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel
from typing import Optional

from app.database import get_database
from app.api.deps import get_current_user, require_admin
from app.utils.validators import validate_object_id
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


# Payments Advanced endpoints

@router.post("/refund")
async def process_refund(
    order_id: str,
    amount: Optional[float] = None,
    reason: Optional[str] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Process a refund for an order (Admin only).
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

    if not order.get("payment_intent_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order has no payment intent to refund"
        )

    # Calculate refund amount
    refund_amount = amount if amount else order.get("total", 0.0)
    refund_amount_cents = int(refund_amount * 100)

    try:
        import stripe
        refund = stripe.Refund.create(
            payment_intent=order["payment_intent_id"],
            amount=refund_amount_cents,
            reason=reason or "requested_by_customer"
        )

        # Update order
        await db.orders.update_one(
            {"_id": ObjectId(order_id)},
            {
                "$set": {
                    "payment_status": "refunded",
                    "refund_id": refund.id,
                    "refunded_amount": refund_amount,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return {
            "success": True,
            "message": "Refund processed successfully",
            "data": {
                "refund_id": refund.id,
                "amount": refund_amount,
                "status": refund.status
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process refund: {str(e)}"
        )


@router.get("/customers")
async def list_stripe_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List Stripe customers (Admin only).
    """
    try:
        import stripe
        customers = stripe.Customer.list(limit=limit)

        return {
            "success": True,
            "data": {
                "customers": [
                    {
                        "id": c.id,
                        "email": c.email,
                        "name": c.name,
                        "created": c.created
                    }
                    for c in customers.data
                ],
                "has_more": customers.has_more
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list customers: {str(e)}"
        )


@router.get("/customers/{customer_id}")
async def get_stripe_customer(
    customer_id: str,
    current_user: dict = Depends(require_admin)
):
    """
    Get Stripe customer details (Admin only).
    """
    try:
        import stripe
        customer = stripe.Customer.retrieve(customer_id)

        return {
            "success": True,
            "data": {
                "id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "phone": customer.phone,
                "address": customer.address,
                "created": customer.created,
                "balance": customer.balance,
                "currency": customer.currency
            }
        }
    except stripe.error.InvalidRequestError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get customer: {str(e)}"
        )


@router.get("/transactions")
async def list_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_admin)
):
    """
    List payment transactions (Admin only).
    """
    try:
        import stripe
        charges = stripe.Charge.list(limit=limit)

        return {
            "success": True,
            "data": {
                "transactions": [
                    {
                        "id": c.id,
                        "amount": c.amount / 100,
                        "currency": c.currency,
                        "status": c.status,
                        "customer": c.customer,
                        "payment_method": c.payment_method,
                        "created": c.created,
                        "refunded": c.refunded,
                        "amount_refunded": c.amount_refunded / 100 if c.amount_refunded else 0
                    }
                    for c in charges.data
                ],
                "has_more": charges.has_more
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list transactions: {str(e)}"
        )


@router.get("/disputes")
async def list_disputes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_admin)
):
    """
    List payment disputes (Admin only).
    """
    try:
        import stripe
        disputes = stripe.Dispute.list(limit=limit)

        return {
            "success": True,
            "data": {
                "disputes": [
                    {
                        "id": d.id,
                        "amount": d.amount / 100,
                        "currency": d.currency,
                        "status": d.status,
                        "reason": d.reason,
                        "charge": d.charge,
                        "created": d.created
                    }
                    for d in disputes.data
                ],
                "has_more": disputes.has_more
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list disputes: {str(e)}"
        )


@router.get("/webhook-events")
async def list_webhook_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List Stripe webhook events log (Admin only).
    """
    skip = (page - 1) * limit

    # Fetch webhook events from database
    cursor = db.webhook_events.find({}).sort("created_at", -1).skip(skip).limit(limit)
    events = await cursor.to_list(length=limit)

    total = await db.webhook_events.count_documents({})

    return {
        "success": True,
        "data": {
            "events": [
                {
                    "id": str(event["_id"]),
                    "event_type": event.get("event_type"),
                    "event_id": event.get("event_id"),
                    "processed": event.get("processed", False),
                    "error": event.get("error"),
                    "created_at": event.get("created_at")
                }
                for event in events
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    }

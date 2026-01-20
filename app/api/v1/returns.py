"""Returns management endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId
from typing import List, Optional
import secrets

from app.database import get_database
from app.api.deps import get_current_user, require_admin
from app.schemas.return_schema import (
    ReturnCreate,
    ReturnResponse,
    ReturnItemResponse,
    ReturnApproveRequest,
    ReturnRejectRequest,
    ReturnRefundRequest,
)
from app.models.return_model import ReturnStatus
from app.utils.validators import validate_object_id

router = APIRouter()


def generate_return_number() -> str:
    """Generate unique return number"""
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    random_suffix = secrets.token_hex(4).upper()
    return f"RET-{timestamp}-{random_suffix}"


@router.get("/returns", response_model=List[ReturnResponse])
async def list_returns(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List all returns (Admin only).
    """
    query = {}
    if status:
        query["status"] = status

    skip = (page - 1) * limit
    cursor = db.returns.find(query).sort("created_at", -1).skip(skip).limit(limit)
    returns = await cursor.to_list(length=limit)

    return [
        ReturnResponse(
            id=str(ret["_id"]),
            return_number=ret["return_number"],
            order_id=ret["order_id"],
            order_number=ret["order_number"],
            user_id=ret["user_id"],
            items=[ReturnItemResponse(**item) for item in ret.get("items", [])],
            total_refund=ret.get("total_refund", 0.0),
            status=ret.get("status", "pending"),
            reason=ret.get("reason"),
            customer_notes=ret.get("customer_notes"),
            admin_notes=ret.get("admin_notes"),
            refund_method=ret.get("refund_method"),
            refunded_amount=ret.get("refunded_amount"),
            created_at=ret.get("created_at", datetime.utcnow()),
            updated_at=ret.get("updated_at", datetime.utcnow()),
        )
        for ret in returns
    ]


@router.get("/returns/{return_id}", response_model=ReturnResponse)
async def get_return(
    return_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get return details (Admin only).
    """
    if not validate_object_id(return_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid return ID"
        )

    ret = await db.returns.find_one({"_id": ObjectId(return_id)})

    if not ret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found"
        )

    return ReturnResponse(
        id=str(ret["_id"]),
        return_number=ret["return_number"],
        order_id=ret["order_id"],
        order_number=ret["order_number"],
        user_id=ret["user_id"],
        items=[ReturnItemResponse(**item) for item in ret.get("items", [])],
        total_refund=ret.get("total_refund", 0.0),
        status=ret.get("status", "pending"),
        reason=ret.get("reason"),
        customer_notes=ret.get("customer_notes"),
        admin_notes=ret.get("admin_notes"),
        refund_method=ret.get("refund_method"),
        refunded_amount=ret.get("refunded_amount"),
        created_at=ret.get("created_at", datetime.utcnow()),
        updated_at=ret.get("updated_at", datetime.utcnow()),
    )


@router.patch("/returns/{return_id}/approve")
async def approve_return(
    return_id: str,
    approve_data: ReturnApproveRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Approve a return (Admin only).
    """
    if not validate_object_id(return_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid return ID"
        )

    ret = await db.returns.find_one({"_id": ObjectId(return_id)})

    if not ret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found"
        )

    if ret.get("status") != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve return with status '{ret.get('status')}'"
        )

    # Update return
    await db.returns.update_one(
        {"_id": ObjectId(return_id)},
        {
            "$set": {
                "status": "approved",
                "admin_notes": approve_data.admin_notes,
                "refund_method": approve_data.refund_method,
                "approved_by": current_user["_id"],
                "approved_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )

    # Restore stock for returned items
    for item in ret.get("items", []):
        await db.products.update_one(
            {"_id": ObjectId(item["product_id"])},
            {"$inc": {"stock": item["quantity"]}}
        )

    return {
        "success": True,
        "message": "Return approved successfully"
    }


@router.patch("/returns/{return_id}/reject")
async def reject_return(
    return_id: str,
    reject_data: ReturnRejectRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Reject a return (Admin only).
    """
    if not validate_object_id(return_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid return ID"
        )

    ret = await db.returns.find_one({"_id": ObjectId(return_id)})

    if not ret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found"
        )

    if ret.get("status") != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject return with status '{ret.get('status')}'"
        )

    # Update return
    await db.returns.update_one(
        {"_id": ObjectId(return_id)},
        {
            "$set": {
                "status": "rejected",
                "admin_notes": reject_data.admin_notes,
                "rejected_by": current_user["_id"],
                "rejected_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "success": True,
        "message": "Return rejected successfully"
    }


@router.post("/returns/{return_id}/refund")
async def process_return_refund(
    return_id: str,
    refund_data: ReturnRefundRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Process refund for approved return (Admin only).
    """
    if not validate_object_id(return_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid return ID"
        )

    ret = await db.returns.find_one({"_id": ObjectId(return_id)})

    if not ret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found"
        )

    if ret.get("status") != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Return must be approved before processing refund"
        )

    # Get order for payment details
    order = await db.orders.find_one({"_id": ObjectId(ret["order_id"])})
    if not order or not order.get("payment_intent_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order has no payment to refund"
        )

    # Calculate refund amount
    refund_amount = refund_data.amount if refund_data.amount else ret.get("total_refund", 0.0)
    refund_amount_cents = int(refund_amount * 100)

    try:
        import stripe
        refund = stripe.Refund.create(
            payment_intent=order["payment_intent_id"],
            amount=refund_amount_cents,
            reason="requested_by_customer"
        )

        # Update return
        await db.returns.update_one(
            {"_id": ObjectId(return_id)},
            {
                "$set": {
                    "status": "refunded",
                    "refunded_amount": refund_amount,
                    "refund_transaction_id": refund.id,
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

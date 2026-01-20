"""Return schemas for requests and responses"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.return_model import ReturnReason, ReturnStatus


class ReturnItemInput(BaseModel):
    """Input schema for return item"""
    product_id: str
    quantity: int = Field(ge=1)
    reason: ReturnReason


class ReturnCreate(BaseModel):
    """Schema for creating a return"""
    order_id: str
    items: List[ReturnItemInput]
    reason: ReturnReason
    customer_notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "507f1f77bcf86cd799439011",
                "items": [
                    {
                        "product_id": "507f191e810c19729de860eb",
                        "quantity": 1,
                        "reason": "defective"
                    }
                ],
                "reason": "defective",
                "customer_notes": "Product arrived damaged"
            }
        }


class ReturnItemResponse(BaseModel):
    """Response schema for return item"""
    product_id: str
    name: str
    product_image: Optional[str] = None
    quantity: int
    unit_price: float
    subtotal: float
    reason: ReturnReason


class ReturnResponse(BaseModel):
    """Response schema for return"""
    id: str
    return_number: str
    order_id: str
    order_number: str
    user_id: str
    items: List[ReturnItemResponse]
    total_refund: float
    status: ReturnStatus
    reason: ReturnReason
    customer_notes: Optional[str] = None
    admin_notes: Optional[str] = None
    refund_method: Optional[str] = None
    refunded_amount: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class ReturnApproveRequest(BaseModel):
    """Schema for approving a return"""
    admin_notes: Optional[str] = None
    refund_method: str = "original"  # "original" or "store_credit"


class ReturnRejectRequest(BaseModel):
    """Schema for rejecting a return"""
    admin_notes: str

    class Config:
        json_schema_extra = {
            "example": {
                "admin_notes": "Product shows signs of use, not eligible for return"
            }
        }


class ReturnRefundRequest(BaseModel):
    """Schema for processing refund"""
    amount: Optional[float] = None  # If None, use total_refund

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 24.99
            }
        }

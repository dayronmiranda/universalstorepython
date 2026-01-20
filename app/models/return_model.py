"""Return models for product returns and refunds"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class ReturnReason(str, Enum):
    """Return reason enumeration"""
    DEFECTIVE = "defective"
    WRONG_ITEM = "wrong_item"
    NOT_AS_DESCRIBED = "not_as_described"
    NO_LONGER_NEEDED = "no_longer_needed"
    DAMAGED = "damaged"
    OTHER = "other"


class ReturnStatus(str, Enum):
    """Return status enumeration"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REFUNDED = "refunded"
    COMPLETED = "completed"


class ReturnItem(BaseModel):
    """Return item model"""
    product_id: str
    name: str
    product_image: Optional[str] = None
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)
    subtotal: float = Field(ge=0)
    reason: ReturnReason


class Return(BaseModel):
    """Return model"""
    id: Optional[str] = Field(None, alias="_id")
    return_number: str
    order_id: str
    order_number: str
    user_id: str
    items: List[ReturnItem]
    total_refund: float = Field(ge=0)
    status: ReturnStatus = ReturnStatus.PENDING
    reason: ReturnReason
    customer_notes: Optional[str] = None
    admin_notes: Optional[str] = None
    refund_method: Optional[str] = None  # "original", "store_credit"
    refunded_amount: Optional[float] = None
    refund_transaction_id: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "return_number": "RET-2024-001",
                "order_id": "507f1f77bcf86cd799439011",
                "order_number": "ORD-2024-001",
                "user_id": "507f191e810c19729de860ea",
                "items": [
                    {
                        "product_id": "507f191e810c19729de860eb",
                        "name": "Premium Widget",
                        "quantity": 1,
                        "unit_price": 24.99,
                        "subtotal": 24.99,
                        "reason": "defective"
                    }
                ],
                "total_refund": 24.99,
                "status": "pending",
                "reason": "defective",
                "customer_notes": "Product arrived damaged"
            }
        }

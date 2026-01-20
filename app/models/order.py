"""Order and Cart models"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum
from app.models.common import Address


class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class OrderItem(BaseModel):
    """Order item model"""
    product_id: str
    name: str
    product_image: Optional[str] = None
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)
    subtotal: float = Field(ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "507f1f77bcf86cd799439011",
                "name": "Premium Widget",
                "product_image": "https://example.com/image.jpg",
                "quantity": 2,
                "unit_price": 24.99,
                "subtotal": 49.98
            }
        }


class Order(BaseModel):
    """Order model"""
    id: Optional[str] = Field(None, alias="_id")
    order_number: str
    user_id: str
    items: List[OrderItem]
    total: float = Field(ge=0)
    status: OrderStatus = OrderStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.PENDING
    payment_intent_id: Optional[str] = None
    shipping_address: Optional[Address] = None
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "order_number": "ORD-2024-001",
                "user_id": "507f1f77bcf86cd799439011",
                "items": [
                    {
                        "product_id": "507f191e810c19729de860ea",
                        "name": "Premium Widget",
                        "quantity": 2,
                        "unit_price": 24.99,
                        "subtotal": 49.98
                    }
                ],
                "total": 49.98,
                "status": "pending",
                "payment_status": "pending",
                "customer_email": "customer@example.com",
                "customer_name": "John Doe"
            }
        }


class CartItem(BaseModel):
    """Cart item model"""
    product_id: str
    name: str
    product_image: Optional[str] = None
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)
    subtotal: float = Field(ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "507f1f77bcf86cd799439011",
                "name": "Premium Widget",
                "product_image": "https://example.com/image.jpg",
                "quantity": 1,
                "unit_price": 24.99,
                "subtotal": 24.99
            }
        }


class Cart(BaseModel):
    """Shopping cart model"""
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    items: List[CartItem] = []
    total: float = Field(default=0, ge=0)
    reserved_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "items": [
                    {
                        "product_id": "507f191e810c19729de860ea",
                        "name": "Premium Widget",
                        "quantity": 2,
                        "unit_price": 24.99,
                        "subtotal": 49.98
                    }
                ],
                "total": 49.98
            }
        }

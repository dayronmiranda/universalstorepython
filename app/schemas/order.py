"""Order and Cart schemas"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from app.models.order import OrderStatus, PaymentStatus
from app.models.common import Address


class CartItemInput(BaseModel):
    """Input schema for cart item"""
    product_id: str
    quantity: int = Field(ge=1)

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "507f1f77bcf86cd799439011",
                "quantity": 2
            }
        }


class CartCreate(BaseModel):
    """Schema for creating a cart with items"""
    items: List[CartItemInput]

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {"product_id": "507f1f77bcf86cd799439011", "quantity": 2},
                    {"product_id": "507f191e810c19729de860ea", "quantity": 1}
                ]
            }
        }


class CartUpdate(BaseModel):
    """Schema for updating cart items"""
    items: List[CartItemInput]

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {"product_id": "507f1f77bcf86cd799439011", "quantity": 3}
                ]
            }
        }


class CartItemResponse(BaseModel):
    """Response schema for cart item"""
    product_id: str
    name: str
    product_image: Optional[str] = None
    quantity: int
    unit_price: float
    subtotal: float


class CartResponse(BaseModel):
    """Response schema for cart"""
    id: str
    user_id: str
    items: List[CartItemResponse]
    total: float
    reserved_until: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "user_id": "507f191e810c19729de860ea",
                "items": [
                    {
                        "product_id": "507f191e810c19729de860eb",
                        "name": "Premium Widget",
                        "quantity": 2,
                        "unit_price": 24.99,
                        "subtotal": 49.98
                    }
                ],
                "total": 49.98,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }


class OrderItemResponse(BaseModel):
    """Response schema for order item"""
    product_id: str
    name: str
    product_image: Optional[str] = None
    quantity: int
    unit_price: float
    subtotal: float


class OrderCreate(BaseModel):
    """Schema for creating an order"""
    cart_id: Optional[str] = None
    shipping_address: Optional[Address] = None
    customer_email: Optional[EmailStr] = None
    customer_name: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "cart_id": "507f1f77bcf86cd799439011",
                "shipping_address": {
                    "address_line1": "123 Main St",
                    "city": "New York",
                    "postal_code": "10001",
                    "country": "USA"
                },
                "customer_email": "customer@example.com",
                "customer_name": "John Doe",
                "notes": "Please deliver between 9am-5pm"
            }
        }


class OrderResponse(BaseModel):
    """Response schema for order"""
    id: str
    order_number: str
    user_id: str
    items: List[OrderItemResponse]
    total: float
    status: OrderStatus
    payment_status: PaymentStatus
    payment_intent_id: Optional[str] = None
    shipping_address: Optional[Address] = None
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "order_number": "ORD-2024-001",
                "user_id": "507f191e810c19729de860ea",
                "items": [
                    {
                        "product_id": "507f191e810c19729de860eb",
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
                "customer_name": "John Doe",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }

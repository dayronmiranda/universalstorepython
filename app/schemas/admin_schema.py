"""Admin advanced schemas"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ProductImageUpload(BaseModel):
    """Schema for uploading product image"""
    product_id: str
    filename: str
    url: str
    is_primary: bool = False
    alt_text: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "507f1f77bcf86cd799439011",
                "filename": "product-image.jpg",
                "url": "https://cdn.example.com/images/product-image.jpg",
                "is_primary": True,
                "alt_text": "Product front view"
            }
        }


class MaintenanceToggleRequest(BaseModel):
    """Schema for toggling maintenance mode"""
    enabled: bool
    message: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "message": "We are upgrading our systems. Back soon!"
            }
        }


class DatabaseCreateRequest(BaseModel):
    """Schema for creating database"""
    database_name: str

    class Config:
        json_schema_extra = {
            "example": {
                "database_name": "jollytienda_test"
            }
        }


class DatabaseSwitchRequest(BaseModel):
    """Schema for switching database"""
    database_name: str

    class Config:
        json_schema_extra = {
            "example": {
                "database_name": "jollytienda_production"
            }
        }


class StatsResponse(BaseModel):
    """Generic stats response"""
    success: bool = True
    data: Dict[str, Any]


class ProductStatsResponse(BaseModel):
    """Product statistics response"""
    total_products: int
    active_products: int
    out_of_stock: int
    low_stock: int
    total_value: float
    by_category: Dict[str, int]


class PaymentStatsResponse(BaseModel):
    """Payment statistics response"""
    total_orders: int
    total_revenue: float
    pending_payments: int
    failed_payments: int
    refunded_amount: float
    by_status: Dict[str, Any]

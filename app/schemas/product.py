"""Product schemas for CRUD operations"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.product import StockStatus


class ProductCreate(BaseModel):
    """Schema for creating a new product"""
    name: str
    description: Optional[str] = None
    price: float = Field(ge=0)
    sale_price: Optional[float] = Field(None, ge=0)
    stock: int = Field(default=0, ge=0)
    image: Optional[str] = None
    images: List[str] = []
    category: Optional[str] = None
    featured: bool = False
    on_sale: bool = False
    stock_status: StockStatus = StockStatus.INSTOCK
    active: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "name": "New Product",
                "description": "A great product",
                "price": 49.99,
                "sale_price": 39.99,
                "stock": 50,
                "image": "https://example.com/image.jpg",
                "images": [],
                "category": "507f1f77bcf86cd799439011",
                "featured": False,
                "on_sale": True,
                "stock_status": "instock",
                "active": True
            }
        }


class ProductUpdate(BaseModel):
    """Schema for updating a product"""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    sale_price: Optional[float] = Field(None, ge=0)
    stock: Optional[int] = Field(None, ge=0)
    image: Optional[str] = None
    images: Optional[List[str]] = None
    category: Optional[str] = None
    featured: Optional[bool] = None
    on_sale: Optional[bool] = None
    stock_status: Optional[StockStatus] = None
    active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Product Name",
                "price": 59.99,
                "stock": 75,
                "featured": True
            }
        }


class ProductResponse(BaseModel):
    """Schema for product response"""
    id: str
    name: str
    description: Optional[str] = None
    price: float
    sale_price: Optional[float] = None
    stock: int
    reserved_stock: int
    available_stock: int
    image: Optional[str] = None
    images: List[str]
    category: Optional[str] = None
    featured: bool
    on_sale: bool
    stock_status: StockStatus
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "name": "Premium Widget",
                "description": "High-quality widget",
                "price": 29.99,
                "sale_price": 24.99,
                "stock": 100,
                "reserved_stock": 5,
                "available_stock": 95,
                "image": "https://example.com/image.jpg",
                "images": [],
                "category": "507f191e810c19729de860ea",
                "featured": True,
                "on_sale": True,
                "stock_status": "instock",
                "active": True,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }


class CategoryCreate(BaseModel):
    """Schema for creating a new category"""
    name: str
    slug: str
    description: Optional[str] = None
    image: Optional[str] = None
    parent_id: Optional[str] = None
    active: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Electronics",
                "slug": "electronics",
                "description": "Electronic devices",
                "image": "https://example.com/category.jpg",
                "parent_id": None,
                "active": True
            }
        }


class CategoryResponse(BaseModel):
    """Schema for category response"""
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    image: Optional[str] = None
    parent_id: Optional[str] = None
    active: bool
    product_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "name": "Electronics",
                "slug": "electronics",
                "description": "Electronic devices",
                "image": "https://example.com/category.jpg",
                "parent_id": None,
                "active": True,
                "product_count": 42,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }

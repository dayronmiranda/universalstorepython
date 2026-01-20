"""Product models"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class StockStatus(str, Enum):
    """Stock status enumeration"""
    INSTOCK = "instock"
    OUTOFSTOCK = "outofstock"
    ONBACKORDER = "onbackorder"


class Product(BaseModel):
    """Product model"""
    id: Optional[str] = Field(None, alias="_id")
    name: str
    description: Optional[str] = None
    price: float = Field(ge=0)
    sale_price: Optional[float] = Field(None, ge=0)
    stock: int = Field(default=0, ge=0)
    reserved_stock: int = Field(default=0, ge=0)
    image: Optional[str] = None
    images: List[str] = []
    category: Optional[str] = None
    featured: bool = False
    on_sale: bool = False
    stock_status: StockStatus = StockStatus.INSTOCK
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "Premium Widget",
                "description": "High-quality widget for all your needs",
                "price": 29.99,
                "sale_price": 24.99,
                "stock": 100,
                "reserved_stock": 5,
                "image": "https://example.com/image.jpg",
                "images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
                "category": "507f1f77bcf86cd799439011",
                "featured": True,
                "on_sale": True,
                "stock_status": "instock",
                "active": True
            }
        }

    @property
    def available_stock(self) -> int:
        """Calculate available stock (total - reserved)"""
        return max(0, self.stock - self.reserved_stock)

    @property
    def effective_price(self) -> float:
        """Get the effective price (sale price if on sale, otherwise regular price)"""
        if self.on_sale and self.sale_price is not None:
            return self.sale_price
        return self.price


class Category(BaseModel):
    """Product category model"""
    id: Optional[str] = Field(None, alias="_id")
    name: str
    slug: str
    description: Optional[str] = None
    image: Optional[str] = None
    parent_id: Optional[str] = None
    active: bool = True
    product_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "Electronics",
                "slug": "electronics",
                "description": "Electronic devices and accessories",
                "image": "https://example.com/category.jpg",
                "parent_id": None,
                "active": True,
                "product_count": 42
            }
        }

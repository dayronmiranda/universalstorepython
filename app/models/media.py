"""Media and file models"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ProductImage(BaseModel):
    """Product image model"""
    id: Optional[str] = Field(None, alias="_id")
    product_id: str
    url: str
    filename: str
    size: int  # bytes
    mime_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    is_primary: bool = False
    alt_text: Optional[str] = None
    uploaded_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "product_id": "507f1f77bcf86cd799439011",
                "url": "https://cdn.example.com/images/product-123.jpg",
                "filename": "product-123.jpg",
                "size": 204800,
                "mime_type": "image/jpeg",
                "width": 1200,
                "height": 800,
                "is_primary": True,
                "alt_text": "Premium Widget - Front View",
                "uploaded_by": "507f191e810c19729de860ea"
            }
        }


class MediaFile(BaseModel):
    """Generic media file model"""
    id: Optional[str] = Field(None, alias="_id")
    url: str
    filename: str
    size: int
    mime_type: str
    category: str  # "product", "category", "banner", "other"
    uploaded_by: str
    metadata: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

"""Common models and base classes"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any
from bson import ObjectId


class PyObjectId(str):
    """Custom type for MongoDB ObjectId"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str):
            if ObjectId.is_valid(v):
                return v
            raise ValueError("Invalid ObjectId")
        raise ValueError("Invalid ObjectId")


class Address(BaseModel):
    """Address model"""
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postal_code: str
    country: str
    phone: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "address_line1": "123 Main St",
                "address_line2": "Apt 4B",
                "city": "New York",
                "state": "NY",
                "postal_code": "10001",
                "country": "USA",
                "phone": "+1234567890"
            }
        }

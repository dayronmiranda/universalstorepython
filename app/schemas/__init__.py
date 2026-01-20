"""Pydantic schemas for request/response validation"""

from app.schemas.common import SuccessResponse, ErrorResponse, PaginationParams
from app.schemas.auth import (
    MagicLinkRequest,
    MagicLinkResponse,
    VerifyMagicLinkRequest,
    TokenResponse,
    UserProfileResponse,
    UpdateProfileRequest,
)
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    CustomerResponse,
)
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    CategoryCreate,
    CategoryResponse,
)
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    CartCreate,
    CartUpdate,
    CartResponse,
    CartKeepAliveResponse,
    CartStatusResponse,
    CartStatusData,
)

__all__ = [
    "SuccessResponse",
    "ErrorResponse",
    "PaginationParams",
    "MagicLinkRequest",
    "MagicLinkResponse",
    "VerifyMagicLinkRequest",
    "TokenResponse",
    "UserProfileResponse",
    "UpdateProfileRequest",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "CustomerResponse",
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "CategoryCreate",
    "CategoryResponse",
    "OrderCreate",
    "OrderResponse",
    "CartCreate",
    "CartUpdate",
    "CartResponse",
    "CartKeepAliveResponse",
    "CartStatusResponse",
    "CartStatusData",
]

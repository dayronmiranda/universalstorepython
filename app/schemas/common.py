"""Common response schemas"""

from pydantic import BaseModel, Field
from typing import Optional, Any, Generic, TypeVar, List

T = TypeVar('T')


class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: str
    detail: Optional[str] = None


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper"""
    success: bool = True
    data: List[T]
    total: int
    page: int
    limit: int
    pages: int

"""FastAPI dependencies for authentication and database access"""

from fastapi import Depends, HTTPException, status, Header
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.core.security import verify_token
from bson import ObjectId
from typing import Optional


async def get_current_user(
    authorization: str = Header(None),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> dict:
    """
    Dependency to get current authenticated user from JWT token

    Args:
        authorization: Authorization header with Bearer token
        db: Database instance

    Returns:
        User dictionary from database

    Raises:
        HTTPException: If authentication fails
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.replace("Bearer ", "")
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Fetch user from database
    user = await db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.get("active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Convert ObjectId to string for JSON serialization
    user["_id"] = str(user["_id"])

    return user


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency to ensure current user is active

    Args:
        current_user: Current user from get_current_user

    Returns:
        Active user dictionary
    """
    return current_user


async def require_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency to require admin, product_manager, or support role

    Args:
        current_user: Current user from get_current_user

    Returns:
        Admin user dictionary

    Raises:
        HTTPException: If user doesn't have required permissions
    """
    allowed_roles = ["admin", "product_manager", "support"]

    if current_user.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required.",
        )

    return current_user


async def require_product_manager(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency to require product_manager or admin role

    Args:
        current_user: Current user from get_current_user

    Returns:
        Product manager/admin user dictionary

    Raises:
        HTTPException: If user doesn't have required permissions
    """
    allowed_roles = ["admin", "product_manager"]

    if current_user.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Product manager role required.",
        )

    return current_user


async def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Optional[dict]:
    """
    Dependency to optionally get current user (doesn't require authentication)

    Args:
        authorization: Optional authorization header
        db: Database instance

    Returns:
        User dictionary if authenticated, None otherwise
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    try:
        token = authorization.replace("Bearer ", "")
        payload = verify_token(token)

        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        user = await db.users.find_one({"_id": ObjectId(user_id)})

        if user and user.get("active", True):
            user["_id"] = str(user["_id"])
            return user

    except Exception:
        pass

    return None

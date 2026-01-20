"""Security utilities for JWT and magic links"""

from datetime import datetime, timedelta
from jose import jwt, JWTError
from app.config import settings
import secrets


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Dictionary containing the payload data (should include 'sub' for user ID)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded payload dictionary or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


def generate_magic_token() -> str:
    """
    Generate a secure random token for magic links

    Returns:
        URL-safe random token string
    """
    return secrets.token_urlsafe(32)


def get_magic_link_expiry() -> datetime:
    """
    Get the expiration datetime for magic links

    Returns:
        Datetime object for magic link expiration
    """
    return datetime.utcnow() + timedelta(minutes=settings.magic_link_expire_minutes)

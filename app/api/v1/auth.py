"""Authentication endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId

from app.database import get_database
from app.api.deps import get_current_user
from app.core.security import (
    create_access_token,
    generate_magic_token,
    get_magic_link_expiry
)
from app.core.email import send_magic_link_email
from app.schemas.auth import (
    MagicLinkRequest,
    MagicLinkResponse,
    VerifyMagicLinkRequest,
    TokenResponse,
    UserProfileResponse,
    UpdateProfileRequest,
)
from app.schemas.common import SuccessResponse

router = APIRouter()


@router.post("/magic-link", response_model=MagicLinkResponse)
async def request_magic_link(
    request: MagicLinkRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Request a magic link for passwordless authentication.
    If the user doesn't exist, creates a new user account.
    """
    email = request.email.lower()

    # Check if user exists, if not create one
    user = await db.users.find_one({"email": email})

    if not user:
        # Create new user
        user_data = {
            "email": email,
            "name": None,
            "role": "client",
            "active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = await db.users.insert_one(user_data)
        user_id = result.inserted_id
    else:
        user_id = user["_id"]

    # Generate magic token
    token = generate_magic_token()
    expires_at = get_magic_link_expiry()

    # Store magic link in database
    magic_link_data = {
        "email": email,
        "token": token,
        "user_id": user_id,
        "used": False,
        "expires_at": expires_at,
        "created_at": datetime.utcnow(),
    }
    await db.magic_links.insert_one(magic_link_data)

    # Send magic link email
    try:
        await send_magic_link_email(email, token)
    except Exception as e:
        # Log error but don't fail the request
        print(f"Failed to send email: {str(e)}")
        # In production, you might want to handle this differently

    return MagicLinkResponse(
        success=True,
        message="Magic link sent to your email"
    )


@router.post("/verify", response_model=TokenResponse)
async def verify_magic_link(
    request: VerifyMagicLinkRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Verify magic link token and return JWT access token
    """
    token = request.token

    # Find magic link
    magic_link = await db.magic_links.find_one({"token": token})

    if not magic_link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid magic link"
        )

    # Check if already used
    if magic_link.get("used", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Magic link already used"
        )

    # Check if expired
    if datetime.utcnow() > magic_link["expires_at"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Magic link expired"
        )

    # Mark as used
    await db.magic_links.update_one(
        {"_id": magic_link["_id"]},
        {"$set": {"used": True}}
    )

    # Get user
    user = await db.users.find_one({"_id": magic_link["user_id"]})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Create JWT token
    access_token = create_access_token(data={"sub": str(user["_id"])})

    # Prepare user profile response
    user_profile = UserProfileResponse(
        id=str(user["_id"]),
        email=user["email"],
        name=user.get("name"),
        role=user["role"],
        active=user.get("active", True)
    )

    return TokenResponse(
        success=True,
        token=access_token,
        user=user_profile
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current authenticated user's profile
    """
    return UserProfileResponse(
        id=current_user["_id"],
        email=current_user["email"],
        name=current_user.get("name"),
        role=current_user["role"],
        active=current_user.get("active", True)
    )


@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
    profile_update: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update current user's profile
    """
    update_data = {}

    if profile_update.name is not None:
        update_data["name"] = profile_update.name

    if profile_update.phone is not None:
        update_data["phone"] = profile_update.phone

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    update_data["updated_at"] = datetime.utcnow()

    # Update user
    await db.users.update_one(
        {"_id": ObjectId(current_user["_id"])},
        {"$set": update_data}
    )

    # Get updated user
    updated_user = await db.users.find_one({"_id": ObjectId(current_user["_id"])})

    return UserProfileResponse(
        id=str(updated_user["_id"]),
        email=updated_user["email"],
        name=updated_user.get("name"),
        role=updated_user["role"],
        active=updated_user.get("active", True)
    )


@router.post("/logout", response_model=SuccessResponse)
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout current user (client-side should remove the token)
    """
    return SuccessResponse(
        success=True,
        message="Logged out successfully"
    )

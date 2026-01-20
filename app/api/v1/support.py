"""Support and chat endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId
from typing import List, Optional

from app.database import get_database
from app.api.deps import get_current_user, require_admin
from app.schemas.support_schema import (
    ChatCreate,
    ChatUpdate,
    MessageCreate,
    ChatResponse,
    ChatWithMessagesResponse,
    MessageResponse,
    ChatStatusUpdate,
    ChatAssignRequest,
    ChatRateRequest,
    AgentStatusUpdate,
    ChatTransferRequest,
    ChatEscalateRequest,
    ChatReleaseRequest,
    ChatResolveRequest,
    ChatPriorityUpdate,
)
from app.models.support import ChatStatus, MessageSender
from app.utils.validators import validate_object_id

router = APIRouter()


def convert_message_to_response(msg: dict) -> dict:
    """Convert MongoDB message document to MessageResponse format."""
    return {
        "id": msg.get("_id"),
        "sender_type": msg.get("sender_type"),
        "sender_id": msg.get("sender_id"),
        "sender_name": msg.get("sender_name"),
        "message": msg.get("message"),
        "attachments": msg.get("attachments", []),
        "read": msg.get("read", False),
        "created_at": msg.get("created_at")
    }


@router.get("", response_model=List[ChatResponse])
async def list_chats(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    view: Optional[str] = None,  # "all" for admin to see all chats
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List user chats or all chats (for admin with view=all).
    """
    query = {}

    # Admin can see all chats with view=all
    if view == "all" and current_user.get("role") in ["admin", "support"]:
        pass  # No filter, show all
    else:
        # Regular users see only their chats
        query["user_id"] = current_user["_id"]

    if status_filter:
        query["status"] = status_filter

    skip = (page - 1) * limit
    cursor = db.chats.find(query).sort("last_message_at", -1).skip(skip).limit(limit)
    chats = await cursor.to_list(length=limit)

    return [
        ChatResponse(
            id=str(chat["_id"]),
            user_id=chat["user_id"],
            user_email=chat["user_email"],
            user_name=chat.get("user_name"),
            subject=chat["subject"],
            status=chat.get("status", "open"),
            assigned_to=chat.get("assigned_to"),
            assigned_to_name=chat.get("assigned_to_name"),
            priority=chat.get("priority", "normal"),
            category=chat.get("category"),
            last_message_at=chat.get("last_message_at", datetime.utcnow()),
            unread_count=chat.get("unread_count", 0),
            agent_unread_count=chat.get("agent_unread_count", 0),
            rating=chat.get("rating"),
            rating_comment=chat.get("rating_comment"),
            created_at=chat.get("created_at", datetime.utcnow()),
            updated_at=chat.get("updated_at", datetime.utcnow()),
            closed_at=chat.get("closed_at"),
        )
        for chat in chats
    ]


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_data: ChatCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new support chat.
    """
    # Create first message
    first_message = {
        "_id": str(ObjectId()),
        "sender_type": "user",
        "sender_id": current_user["_id"],
        "sender_name": current_user.get("name") or current_user.get("email"),
        "message": chat_data.message,
        "attachments": [],
        "read": False,
        "created_at": datetime.utcnow()
    }

    # Create chat document
    chat_doc = {
        "user_id": current_user["_id"],
        "user_email": current_user.get("email"),
        "user_name": current_user.get("name"),
        "subject": chat_data.subject,
        "status": "open",
        "priority": chat_data.priority or "normal",
        "category": chat_data.category,
        "messages": [first_message],
        "last_message_at": datetime.utcnow(),
        "unread_count": 0,
        "agent_unread_count": 1,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = await db.chats.insert_one(chat_doc)
    created_chat = await db.chats.find_one({"_id": result.inserted_id})

    return ChatResponse(
        id=str(created_chat["_id"]),
        user_id=created_chat["user_id"],
        user_email=created_chat["user_email"],
        user_name=created_chat.get("user_name"),
        subject=created_chat["subject"],
        status=created_chat["status"],
        assigned_to=created_chat.get("assigned_to"),
        assigned_to_name=created_chat.get("assigned_to_name"),
        priority=created_chat["priority"],
        category=created_chat.get("category"),
        last_message_at=created_chat["last_message_at"],
        unread_count=created_chat["unread_count"],
        agent_unread_count=created_chat["agent_unread_count"],
        rating=created_chat.get("rating"),
        rating_comment=created_chat.get("rating_comment"),
        created_at=created_chat["created_at"],
        updated_at=created_chat["updated_at"],
        closed_at=created_chat.get("closed_at"),
    )


@router.get("/poll", response_model=dict)
async def poll_updates(
    since: datetime = Query(..., description="Get updates since this timestamp"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Poll for chat updates since a specific timestamp.
    """
    query = {
        "user_id": current_user["_id"],
        "updated_at": {"$gt": since}
    }

    # Admin can see all updates
    if current_user.get("role") in ["admin", "support"]:
        query = {"updated_at": {"$gt": since}}

    cursor = db.chats.find(query).limit(50)
    updated_chats = await cursor.to_list(length=50)

    return {
        "success": True,
        "data": {
            "has_updates": len(updated_chats) > 0,
            "count": len(updated_chats),
            "chat_ids": [str(chat["_id"]) for chat in updated_chats]
        }
    }


@router.get("/unread")
async def get_unread_count(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get unread message count for current user.
    """
    query = {"user_id": current_user["_id"]}

    pipeline = [
        {"$match": query},
        {
            "$group": {
                "_id": None,
                "total_unread": {"$sum": "$unread_count"},
                "chats_with_unread": {
                    "$sum": {"$cond": [{"$gt": ["$unread_count", 0]}, 1, 0]}
                }
            }
        }
    ]

    result = await db.chats.aggregate(pipeline).to_list(length=1)

    if result:
        return {
            "success": True,
            "data": {
                "total_unread": result[0]["total_unread"],
                "chats_with_unread": result[0]["chats_with_unread"]
            }
        }
    else:
        return {
            "success": True,
            "data": {
                "total_unread": 0,
                "chats_with_unread": 0
            }
        }


@router.get("/{chat_id}", response_model=ChatWithMessagesResponse)
async def get_chat(
    chat_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get chat with messages.
    """
    if not validate_object_id(chat_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    chat = await db.chats.find_one({"_id": ObjectId(chat_id)})

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    # Check permissions
    is_owner = chat["user_id"] == current_user["_id"]
    is_admin = current_user.get("role") in ["admin", "support"]

    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this chat"
        )

    # Mark messages as read for current user
    if is_owner:
        await db.chats.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"unread_count": 0}}
        )
    elif is_admin:
        await db.chats.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"agent_unread_count": 0}}
        )

    return ChatWithMessagesResponse(
        id=str(chat["_id"]),
        user_id=chat["user_id"],
        user_email=chat["user_email"],
        user_name=chat.get("user_name"),
        subject=chat["subject"],
        status=chat["status"],
        assigned_to=chat.get("assigned_to"),
        assigned_to_name=chat.get("assigned_to_name"),
        priority=chat["priority"],
        category=chat.get("category"),
        last_message_at=chat["last_message_at"],
        unread_count=0 if is_owner else chat.get("unread_count", 0),
        agent_unread_count=0 if is_admin else chat.get("agent_unread_count", 0),
        rating=chat.get("rating"),
        rating_comment=chat.get("rating_comment"),
        created_at=chat["created_at"],
        updated_at=chat["updated_at"],
        closed_at=chat.get("closed_at"),
        messages=[MessageResponse(**convert_message_to_response(msg)) for msg in chat.get("messages", [])]
    )


@router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: str,
    chat_update: ChatUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update chat details.
    """
    if not validate_object_id(chat_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    chat = await db.chats.find_one({"_id": ObjectId(chat_id)})

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    # Check permissions
    is_owner = chat["user_id"] == current_user["_id"]
    is_admin = current_user.get("role") in ["admin", "support"]

    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this chat"
        )

    update_data = chat_update.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()

    await db.chats.update_one(
        {"_id": ObjectId(chat_id)},
        {"$set": update_data}
    )

    updated_chat = await db.chats.find_one({"_id": ObjectId(chat_id)})

    return ChatResponse(
        id=str(updated_chat["_id"]),
        user_id=updated_chat["user_id"],
        user_email=updated_chat["user_email"],
        user_name=updated_chat.get("user_name"),
        subject=updated_chat["subject"],
        status=updated_chat["status"],
        assigned_to=updated_chat.get("assigned_to"),
        assigned_to_name=updated_chat.get("assigned_to_name"),
        priority=updated_chat["priority"],
        category=updated_chat.get("category"),
        last_message_at=updated_chat["last_message_at"],
        unread_count=updated_chat["unread_count"],
        agent_unread_count=updated_chat["agent_unread_count"],
        rating=updated_chat.get("rating"),
        rating_comment=updated_chat.get("rating_comment"),
        created_at=updated_chat["created_at"],
        updated_at=updated_chat["updated_at"],
        closed_at=updated_chat.get("closed_at"),
    )


@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    chat_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get messages for a chat.
    """
    if not validate_object_id(chat_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    chat = await db.chats.find_one({"_id": ObjectId(chat_id)})

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    # Check permissions
    is_owner = chat["user_id"] == current_user["_id"]
    is_admin = current_user.get("role") in ["admin", "support"]

    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this chat"
        )

    return [MessageResponse(**convert_message_to_response(msg)) for msg in chat.get("messages", [])]


@router.post("/{chat_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    chat_id: str,
    message_data: MessageCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Send a message in a chat.
    """
    if not validate_object_id(chat_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    chat = await db.chats.find_one({"_id": ObjectId(chat_id)})

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    # Check permissions
    is_owner = chat["user_id"] == current_user["_id"]
    is_admin = current_user.get("role") in ["admin", "support"]

    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to send messages in this chat"
        )

    # Determine sender type
    if is_admin and not is_owner:
        sender_type = "agent"
        unread_field = "unread_count"
        increment_value = 1
    else:
        sender_type = "user"
        unread_field = "agent_unread_count"
        increment_value = 1

    # Create message
    message = {
        "_id": str(ObjectId()),
        "sender_type": sender_type,
        "sender_id": current_user["_id"],
        "sender_name": current_user.get("name") or current_user.get("email"),
        "message": message_data.message,
        "attachments": message_data.attachments,
        "read": False,
        "created_at": datetime.utcnow()
    }

    # Add message to chat
    await db.chats.update_one(
        {"_id": ObjectId(chat_id)},
        {
            "$push": {"messages": message},
            "$set": {"last_message_at": datetime.utcnow(), "updated_at": datetime.utcnow()},
            "$inc": {unread_field: increment_value}
        }
    )

    return MessageResponse(**convert_message_to_response(message))


@router.patch("/{chat_id}/status")
async def update_chat_status(
    chat_id: str,
    status_update: ChatStatusUpdate,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update chat status (Admin only).
    """
    if not validate_object_id(chat_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    chat = await db.chats.find_one({"_id": ObjectId(chat_id)})

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    update_data = {
        "status": status_update.status,
        "updated_at": datetime.utcnow()
    }

    if status_update.status == "closed":
        update_data["closed_at"] = datetime.utcnow()

    await db.chats.update_one(
        {"_id": ObjectId(chat_id)},
        {"$set": update_data}
    )

    return {
        "success": True,
        "message": f"Chat status updated to {status_update.status}"
    }


@router.patch("/{chat_id}/assign")
async def assign_chat(
    chat_id: str,
    assign_data: ChatAssignRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Assign chat to an agent (Admin only).
    """
    if not validate_object_id(chat_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    if not validate_object_id(assign_data.agent_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agent ID"
        )

    chat = await db.chats.find_one({"_id": ObjectId(chat_id)})

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    # Verify agent exists and has appropriate role
    agent = await db.users.find_one({"_id": ObjectId(assign_data.agent_id)})
    if not agent or agent.get("role") not in ["admin", "support"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agent or agent does not have support role"
        )

    await db.chats.update_one(
        {"_id": ObjectId(chat_id)},
        {
            "$set": {
                "assigned_to": assign_data.agent_id,
                "assigned_to_name": agent.get("name") or agent.get("email"),
                "status": "assigned",
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "success": True,
        "message": f"Chat assigned to {agent.get('name') or agent.get('email')}"
    }


@router.post("/{chat_id}/rate")
async def rate_chat(
    chat_id: str,
    rate_data: ChatRateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Rate a support chat (user only).
    """
    if not validate_object_id(chat_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    chat = await db.chats.find_one({"_id": ObjectId(chat_id)})

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    # Only chat owner can rate
    if chat["user_id"] != current_user["_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the chat owner can rate it"
        )

    # Chat must be resolved or closed
    if chat.get("status") not in ["resolved", "closed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only rate resolved or closed chats"
        )

    await db.chats.update_one(
        {"_id": ObjectId(chat_id)},
        {
            "$set": {
                "rating": rate_data.rating,
                "rating_comment": rate_data.comment,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "success": True,
        "message": "Thank you for your feedback!"
    }


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a chat (Admin only).
    Only closed chats can be deleted.
    """
    if not validate_object_id(chat_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    chat = await db.chats.find_one({"_id": ObjectId(chat_id)})

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    # Only allow deletion of closed chats
    if chat.get("status") != "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only closed chats can be deleted"
        )

    # Delete chat
    result = await db.chats.delete_one({"_id": ObjectId(chat_id)})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat"
        )

    return {
        "success": True,
        "message": "Chat deleted successfully"
    }


# Agent-specific endpoints

@router.get("/agent/profile")
async def get_agent_profile(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get agent profile with stats (Support/Admin only).
    """
    agent_id = current_user["_id"]

    # Get agent's assigned chats
    assigned_chats = await db.chats.count_documents({"assigned_to": agent_id})

    # Get agent's resolved chats
    resolved_chats = await db.chats.count_documents({
        "assigned_to": agent_id,
        "status": "resolved"
    })

    # Get average rating
    pipeline = [
        {"$match": {"assigned_to": agent_id, "rating": {"$exists": True}}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}}}
    ]
    rating_result = await db.chats.aggregate(pipeline).to_list(length=1)
    avg_rating = rating_result[0]["avg_rating"] if rating_result else None

    # Get agent status from user document
    agent = await db.users.find_one({"_id": ObjectId(agent_id)})
    agent_status = agent.get("agent_status", "offline")

    return {
        "success": True,
        "data": {
            "id": agent_id,
            "email": current_user.get("email"),
            "name": current_user.get("name"),
            "role": current_user.get("role"),
            "status": agent_status,
            "stats": {
                "assigned_chats": assigned_chats,
                "resolved_chats": resolved_chats,
                "average_rating": avg_rating
            }
        }
    }


@router.put("/agent/status")
async def update_agent_status(
    status_update: AgentStatusUpdate,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update agent status (Support/Admin only).
    """
    valid_statuses = ["online", "away", "offline"]
    if status_update.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    await db.users.update_one(
        {"_id": ObjectId(current_user["_id"])},
        {
            "$set": {
                "agent_status": status_update.status,
                "agent_status_updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "success": True,
        "message": f"Agent status updated to {status_update.status}",
        "data": {
            "status": status_update.status
        }
    }


@router.get("/agent/dashboard")
async def get_agent_dashboard(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get agent dashboard with statistics (Support/Admin only).
    """
    agent_id = current_user["_id"]

    # Get active chats assigned to agent
    active_chats = await db.chats.count_documents({
        "assigned_to": agent_id,
        "status": {"$in": ["open", "assigned", "in_progress"]}
    })

    # Get pending chats (unassigned)
    pending_chats = await db.chats.count_documents({
        "status": "open",
        "assigned_to": {"$exists": False}
    })

    # Get resolved today
    from datetime import datetime, timedelta
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_today = await db.chats.count_documents({
        "assigned_to": agent_id,
        "status": "resolved",
        "closed_at": {"$gte": today_start}
    })

    # Get average response time (simplified)
    avg_response_time = 0  # Placeholder

    return {
        "success": True,
        "data": {
            "active_chats": active_chats,
            "pending_chats": pending_chats,
            "resolved_today": resolved_today,
            "avg_response_time_minutes": avg_response_time
        }
    }


@router.get("/agent/chats", response_model=List[ChatResponse])
async def get_agent_chats(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get chats assigned to current agent (Support/Admin only).
    """
    query = {"assigned_to": current_user["_id"]}

    if status_filter:
        query["status"] = status_filter

    skip = (page - 1) * limit
    cursor = db.chats.find(query).sort("last_message_at", -1).skip(skip).limit(limit)
    chats = await cursor.to_list(length=limit)

    return [
        ChatResponse(
            id=str(chat["_id"]),
            user_id=chat["user_id"],
            user_email=chat["user_email"],
            user_name=chat.get("user_name"),
            subject=chat["subject"],
            status=chat.get("status", "open"),
            assigned_to=chat.get("assigned_to"),
            assigned_to_name=chat.get("assigned_to_name"),
            priority=chat.get("priority", "normal"),
            category=chat.get("category"),
            last_message_at=chat.get("last_message_at", datetime.utcnow()),
            unread_count=chat.get("unread_count", 0),
            agent_unread_count=chat.get("agent_unread_count", 0),
            rating=chat.get("rating"),
            rating_comment=chat.get("rating_comment"),
            created_at=chat.get("created_at", datetime.utcnow()),
            updated_at=chat.get("updated_at", datetime.utcnow()),
            closed_at=chat.get("closed_at"),
        )
        for chat in chats
    ]


@router.get("/agent/queue", response_model=List[ChatResponse])
async def get_agent_queue(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    priority: Optional[str] = None,
    category: Optional[str] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get queue of unassigned chats (Support/Admin only).
    """
    query = {
        "status": "open",
        "$or": [
            {"assigned_to": {"$exists": False}},
            {"assigned_to": None}
        ]
    }

    if priority:
        query["priority"] = priority

    if category:
        query["category"] = category

    skip = (page - 1) * limit
    cursor = db.chats.find(query).sort([("priority", -1), ("created_at", 1)]).skip(skip).limit(limit)
    chats = await cursor.to_list(length=limit)

    return [
        ChatResponse(
            id=str(chat["_id"]),
            user_id=chat["user_id"],
            user_email=chat["user_email"],
            user_name=chat.get("user_name"),
            subject=chat["subject"],
            status=chat.get("status", "open"),
            assigned_to=chat.get("assigned_to"),
            assigned_to_name=chat.get("assigned_to_name"),
            priority=chat.get("priority", "normal"),
            category=chat.get("category"),
            last_message_at=chat.get("last_message_at", datetime.utcnow()),
            unread_count=chat.get("unread_count", 0),
            agent_unread_count=chat.get("agent_unread_count", 0),
            rating=chat.get("rating"),
            rating_comment=chat.get("rating_comment"),
            created_at=chat.get("created_at", datetime.utcnow()),
            updated_at=chat.get("updated_at", datetime.utcnow()),
            closed_at=chat.get("closed_at"),
        )
        for chat in chats
    ]


@router.get("/agent/queue/stats")
async def get_queue_stats(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get queue statistics (Support/Admin only).
    """
    # Count by priority
    pipeline = [
        {
            "$match": {
                "status": "open",
                "$or": [
                    {"assigned_to": {"$exists": False}},
                    {"assigned_to": None}
                ]
            }
        },
        {
            "$group": {
                "_id": "$priority",
                "count": {"$sum": 1}
            }
        }
    ]

    priority_stats = await db.chats.aggregate(pipeline).to_list(length=10)

    # Total queue size
    total_queue = sum(stat["count"] for stat in priority_stats)

    # Oldest waiting chat
    oldest_chat = await db.chats.find_one(
        {
            "status": "open",
            "$or": [
                {"assigned_to": {"$exists": False}},
                {"assigned_to": None}
            ]
        },
        sort=[("created_at", 1)]
    )

    oldest_wait_minutes = 0
    if oldest_chat:
        wait_time = datetime.utcnow() - oldest_chat.get("created_at", datetime.utcnow())
        oldest_wait_minutes = int(wait_time.total_seconds() / 60)

    return {
        "success": True,
        "data": {
            "total_queue": total_queue,
            "by_priority": {stat["_id"]: stat["count"] for stat in priority_stats},
            "oldest_wait_minutes": oldest_wait_minutes
        }
    }


@router.post("/agent/claim/{chat_id}")
async def claim_chat(
    chat_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Claim a chat from queue (Support/Admin only).
    """
    if not validate_object_id(chat_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    chat = await db.chats.find_one({"_id": ObjectId(chat_id)})

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    # Check if chat is already assigned
    if chat.get("assigned_to"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat is already assigned to another agent"
        )

    # Assign chat to current agent
    await db.chats.update_one(
        {"_id": ObjectId(chat_id)},
        {
            "$set": {
                "assigned_to": current_user["_id"],
                "assigned_to_name": current_user.get("name") or current_user.get("email"),
                "status": "assigned",
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "success": True,
        "message": "Chat claimed successfully"
    }


@router.post("/agent/transfer/{chat_id}")
async def transfer_chat(
    chat_id: str,
    transfer_data: ChatTransferRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Transfer chat to another agent (Support/Admin only).
    """
    if not validate_object_id(chat_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    if not validate_object_id(transfer_data.agent_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agent ID"
        )

    chat = await db.chats.find_one({"_id": ObjectId(chat_id)})

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    # Verify target agent exists and has appropriate role
    target_agent = await db.users.find_one({"_id": ObjectId(transfer_data.agent_id)})
    if not target_agent or target_agent.get("role") not in ["admin", "support"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agent or agent does not have support role"
        )

    # Create transfer message
    transfer_message = {
        "_id": str(ObjectId()),
        "sender_type": "system",
        "sender_id": "system",
        "sender_name": "System",
        "message": f"Chat transferred from {current_user.get('name') or current_user.get('email')} to {target_agent.get('name') or target_agent.get('email')}. Reason: {transfer_data.reason or 'N/A'}",
        "attachments": [],
        "read": False,
        "created_at": datetime.utcnow()
    }

    await db.chats.update_one(
        {"_id": ObjectId(chat_id)},
        {
            "$set": {
                "assigned_to": transfer_data.agent_id,
                "assigned_to_name": target_agent.get("name") or target_agent.get("email"),
                "updated_at": datetime.utcnow()
            },
            "$push": {"messages": transfer_message}
        }
    )

    return {
        "success": True,
        "message": f"Chat transferred to {target_agent.get('name') or target_agent.get('email')}"
    }


@router.post("/agent/release/{chat_id}")
async def release_chat(
    chat_id: str,
    release_data: ChatReleaseRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Release chat back to queue (Support/Admin only).
    """
    if not validate_object_id(chat_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    chat = await db.chats.find_one({"_id": ObjectId(chat_id)})

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    # Create release message
    release_message = {
        "_id": str(ObjectId()),
        "sender_type": "system",
        "sender_id": "system",
        "sender_name": "System",
        "message": f"Chat released back to queue by {current_user.get('name') or current_user.get('email')}. Reason: {release_data.reason or 'N/A'}",
        "attachments": [],
        "read": False,
        "created_at": datetime.utcnow()
    }

    await db.chats.update_one(
        {"_id": ObjectId(chat_id)},
        {
            "$set": {
                "status": "open",
                "updated_at": datetime.utcnow()
            },
            "$unset": {"assigned_to": "", "assigned_to_name": ""},
            "$push": {"messages": release_message}
        }
    )

    return {
        "success": True,
        "message": "Chat released back to queue"
    }


@router.post("/agent/escalate/{chat_id}")
async def escalate_chat(
    chat_id: str,
    escalate_data: ChatEscalateRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Escalate a chat (Support/Admin only).
    """
    if not validate_object_id(chat_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    chat = await db.chats.find_one({"_id": ObjectId(chat_id)})

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    # Create escalation message
    escalation_message = {
        "_id": str(ObjectId()),
        "sender_type": "system",
        "sender_id": "system",
        "sender_name": "System",
        "message": f"Chat escalated by {current_user.get('name') or current_user.get('email')}. Reason: {escalate_data.reason}",
        "attachments": [],
        "read": False,
        "created_at": datetime.utcnow()
    }

    await db.chats.update_one(
        {"_id": ObjectId(chat_id)},
        {
            "$set": {
                "priority": escalate_data.priority or "high",
                "status": "escalated",
                "updated_at": datetime.utcnow()
            },
            "$push": {"messages": escalation_message}
        }
    )

    return {
        "success": True,
        "message": "Chat escalated successfully"
    }


@router.post("/agent/resolve/{chat_id}")
async def resolve_chat(
    chat_id: str,
    resolve_data: ChatResolveRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Resolve a chat (Support/Admin only).
    """
    if not validate_object_id(chat_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    chat = await db.chats.find_one({"_id": ObjectId(chat_id)})

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    # Create resolution message if note provided
    messages_update = {}
    if resolve_data.resolution_note:
        resolution_message = {
            "_id": str(ObjectId()),
            "sender_type": "agent",
            "sender_id": current_user["_id"],
            "sender_name": current_user.get("name") or current_user.get("email"),
            "message": f"Resolution note: {resolve_data.resolution_note}",
            "attachments": [],
            "read": False,
            "created_at": datetime.utcnow()
        }
        messages_update["$push"] = {"messages": resolution_message}

    update_data = {
        "$set": {
            "status": "resolved",
            "closed_at": datetime.utcnow(),
            "resolved_by": current_user["_id"],
            "resolved_by_name": current_user.get("name") or current_user.get("email"),
            "updated_at": datetime.utcnow()
        }
    }

    if messages_update:
        update_data.update(messages_update)

    await db.chats.update_one({"_id": ObjectId(chat_id)}, update_data)

    return {
        "success": True,
        "message": "Chat resolved successfully"
    }


@router.put("/agent/priority/{chat_id}")
async def update_chat_priority(
    chat_id: str,
    priority_update: ChatPriorityUpdate,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update chat priority (Support/Admin only).
    """
    if not validate_object_id(chat_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    valid_priorities = ["low", "normal", "high", "urgent"]
    if priority_update.priority not in valid_priorities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"
        )

    chat = await db.chats.find_one({"_id": ObjectId(chat_id)})

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    await db.chats.update_one(
        {"_id": ObjectId(chat_id)},
        {
            "$set": {
                "priority": priority_update.priority,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "success": True,
        "message": f"Chat priority updated to {priority_update.priority}"
    }


@router.get("/agent/online")
async def get_online_agents(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get list of online agents.
    """
    # Find all agents (support/admin) with online status
    cursor = db.users.find({
        "role": {"$in": ["admin", "support"]},
        "agent_status": "online"
    })

    agents = await cursor.to_list(length=100)

    return {
        "success": True,
        "data": {
            "agents": [
                {
                    "id": str(agent["_id"]),
                    "email": agent.get("email"),
                    "name": agent.get("name"),
                    "role": agent.get("role"),
                    "status": agent.get("agent_status", "offline")
                }
                for agent in agents
            ],
            "count": len(agents)
        }
    }

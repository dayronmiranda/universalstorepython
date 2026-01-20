"""Support and chat models"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class ChatStatus(str, Enum):
    """Chat status enumeration"""
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PENDING_USER = "pending_user"
    RESOLVED = "resolved"
    CLOSED = "closed"


class MessageSender(str, Enum):
    """Message sender type"""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class Message(BaseModel):
    """Chat message model"""
    id: Optional[str] = Field(None, alias="_id")
    sender_type: MessageSender
    sender_id: str
    sender_name: Optional[str] = None
    message: str
    attachments: List[str] = []
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class Chat(BaseModel):
    """Support chat model"""
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    user_email: str
    user_name: Optional[str] = None
    subject: str
    status: ChatStatus = ChatStatus.OPEN
    assigned_to: Optional[str] = None  # Agent user ID
    assigned_to_name: Optional[str] = None
    priority: Optional[str] = "normal"  # "low", "normal", "high", "urgent"
    category: Optional[str] = None  # "order", "product", "payment", "general"
    messages: List[Message] = []
    last_message_at: datetime = Field(default_factory=datetime.utcnow)
    unread_count: int = 0  # Unread messages for user
    agent_unread_count: int = 0  # Unread messages for agent
    rating: Optional[int] = None  # 1-5 stars
    rating_comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "user_email": "customer@example.com",
                "user_name": "John Doe",
                "subject": "Question about my order",
                "status": "open",
                "priority": "normal",
                "category": "order",
                "messages": []
            }
        }

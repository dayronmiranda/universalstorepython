"""Support and chat schemas"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.support import ChatStatus, MessageSender


class ChatCreate(BaseModel):
    """Schema for creating a chat"""
    subject: str
    message: str
    category: Optional[str] = "general"
    priority: Optional[str] = "normal"

    class Config:
        json_schema_extra = {
            "example": {
                "subject": "Question about my order",
                "message": "When will my order arrive?",
                "category": "order",
                "priority": "normal"
            }
        }


class ChatUpdate(BaseModel):
    """Schema for updating a chat"""
    subject: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None


class MessageCreate(BaseModel):
    """Schema for creating a message"""
    message: str
    attachments: List[str] = []

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Thank you for your help!",
                "attachments": []
            }
        }


class MessageResponse(BaseModel):
    """Response schema for message"""
    id: str
    sender_type: MessageSender
    sender_id: str
    sender_name: Optional[str] = None
    message: str
    attachments: List[str]
    read: bool
    created_at: datetime


class ChatResponse(BaseModel):
    """Response schema for chat"""
    id: str
    user_id: str
    user_email: str
    user_name: Optional[str] = None
    subject: str
    status: ChatStatus
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    priority: str
    category: Optional[str] = None
    last_message_at: datetime
    unread_count: int
    agent_unread_count: int
    rating: Optional[int] = None
    rating_comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None


class ChatWithMessagesResponse(ChatResponse):
    """Chat response with messages included"""
    messages: List[MessageResponse]


class ChatStatusUpdate(BaseModel):
    """Schema for updating chat status"""
    status: ChatStatus

    class Config:
        json_schema_extra = {
            "example": {
                "status": "resolved"
            }
        }


class ChatAssignRequest(BaseModel):
    """Schema for assigning chat to agent"""
    agent_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "507f1f77bcf86cd799439011"
            }
        }


class ChatRateRequest(BaseModel):
    """Schema for rating a chat"""
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "rating": 5,
                "comment": "Excellent support, very helpful!"
            }
        }


# Agent-specific schemas

class AgentStatusUpdate(BaseModel):
    """Schema for updating agent status"""
    status: str  # online, away, offline

    class Config:
        json_schema_extra = {
            "example": {
                "status": "online"
            }
        }


class ChatTransferRequest(BaseModel):
    """Schema for transferring chat to another agent"""
    agent_id: str
    reason: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "507f1f77bcf86cd799439011",
                "reason": "Requires specialist knowledge"
            }
        }


class ChatEscalateRequest(BaseModel):
    """Schema for escalating a chat"""
    reason: str
    priority: Optional[str] = "high"

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Customer is requesting refund",
                "priority": "high"
            }
        }


class ChatReleaseRequest(BaseModel):
    """Schema for releasing a chat back to queue"""
    reason: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Unable to assist further"
            }
        }


class ChatResolveRequest(BaseModel):
    """Schema for resolving a chat"""
    resolution_note: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "resolution_note": "Issue resolved, customer satisfied"
            }
        }


class ChatPriorityUpdate(BaseModel):
    """Schema for updating chat priority"""
    priority: str  # low, normal, high, urgent

    class Config:
        json_schema_extra = {
            "example": {
                "priority": "high"
            }
        }

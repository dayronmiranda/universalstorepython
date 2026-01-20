from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class EmailTemplateType(str, Enum):
    MAGIC_LINK = "magic_link"
    EMAIL_VERIFICATION = "email_verification"
    WELCOME = "welcome"
    PASSWORD_RESET = "password_reset"
    ORDER_CONFIRMATION = "order_confirmation"
    ORDER_READY = "order_ready"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_SHIPPED = "order_shipped"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    ACCOUNT_DEACTIVATED = "account_deactivated"


class EmailTemplateVariable(BaseModel):
    name: str  # e.g., "{{userName}}"
    description: str
    example: str


class EmailTemplate(BaseModel):
    type: EmailTemplateType
    name: str
    description: Optional[str] = None
    subject: str
    htmlBody: str
    textBody: Optional[str] = None
    availableVariables: Optional[List[EmailTemplateVariable]] = []
    isActive: bool = True
    isDefault: bool = False
    previewData: Optional[Dict[str, str]] = {}
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

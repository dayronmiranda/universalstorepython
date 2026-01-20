from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from app.models.email_template import EmailTemplateType


class EmailTemplateVariableResponse(BaseModel):
    name: str
    description: str
    example: str


class CreateEmailTemplateRequest(BaseModel):
    type: EmailTemplateType
    name: str
    description: Optional[str] = None
    subject: str
    htmlBody: str
    textBody: Optional[str] = None
    isActive: bool = True


class UpdateEmailTemplateRequest(BaseModel):
    type: Optional[EmailTemplateType] = None
    name: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    htmlBody: Optional[str] = None
    textBody: Optional[str] = None
    isActive: Optional[bool] = None


class EmailTemplateResponse(BaseModel):
    id: str
    type: EmailTemplateType
    name: str
    description: Optional[str] = None
    subject: str
    htmlBody: str
    textBody: Optional[str] = None
    availableVariables: Optional[List[EmailTemplateVariableResponse]] = []
    isActive: bool
    isDefault: bool
    previewData: Optional[Dict[str, str]] = {}
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class EmailTemplatePreviewRequest(BaseModel):
    previewData: Dict[str, str]


class EmailTemplatePreviewResponse(BaseModel):
    subject: str
    htmlBody: str
    textBody: Optional[str] = None


class SendTestEmailTemplateRequest(BaseModel):
    template_id: str
    to_email: str
    preview_data: Optional[Dict[str, str]] = {}


class EmailTemplateListResponse(BaseModel):
    templates: List[EmailTemplateResponse]
    total: int

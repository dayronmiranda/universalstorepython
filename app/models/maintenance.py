"""Maintenance and configuration models"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class MaintenanceConfig(BaseModel):
    """Maintenance mode configuration"""
    id: Optional[str] = Field(None, alias="_id")
    enabled: bool = False
    message: str = "We are currently performing maintenance. Please check back soon."
    allowed_ips: list[str] = []  # IPs that can bypass maintenance
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "enabled": False,
                "message": "We are upgrading our systems. Back at 3 PM EST.",
                "allowed_ips": ["192.168.1.1"],
                "scheduled_start": "2024-01-20T14:00:00",
                "scheduled_end": "2024-01-20T15:00:00"
            }
        }


class JobAudit(BaseModel):
    """Job audit log model"""
    id: Optional[str] = Field(None, alias="_id")
    job_type: str  # "email", "payment_sync", "stock_update", etc.
    status: str  # "started", "completed", "failed"
    details: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None
    triggered_by: Optional[str] = None  # "system", "user", "cron"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "job_type": "email_notification",
                "status": "completed",
                "details": {"emails_sent": 150},
                "duration_ms": 5230,
                "triggered_by": "system"
            }
        }

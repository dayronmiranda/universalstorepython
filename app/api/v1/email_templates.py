"""Admin Email Templates Management Endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId
from typing import Optional, Dict, List
import asyncio

from app.database import get_database
from app.api.deps import require_admin
from app.schemas.email_template_schema import (
    CreateEmailTemplateRequest,
    UpdateEmailTemplateRequest,
    EmailTemplateResponse,
    EmailTemplateListResponse,
    EmailTemplatePreviewRequest,
    EmailTemplatePreviewResponse,
    SendTestEmailTemplateRequest,
    EmailTemplateVariableResponse,
)
from app.models.email_template import EmailTemplateType, EmailTemplateVariable
from app.utils.validators import validate_object_id

router = APIRouter()


# Default template variables by type
TEMPLATE_VARIABLES: Dict[str, List[EmailTemplateVariable]] = {
    "magic_link": [
        EmailTemplateVariable(
            name="{{magicLink}}",
            description="Magic link URL for authentication",
            example="https://example.com/verify?token=abc123"
        ),
        EmailTemplateVariable(
            name="{{userName}}",
            description="User's full name",
            example="John Doe"
        ),
        EmailTemplateVariable(
            name="{{userEmail}}",
            description="User's email address",
            example="john@example.com"
        ),
        EmailTemplateVariable(
            name="{{storeName}}",
            description="Store name",
            example="Universal Store"
        ),
        EmailTemplateVariable(
            name="{{expiryTime}}",
            description="Link expiry time",
            example="15 minutes"
        ),
    ],
    "email_verification": [
        EmailTemplateVariable(
            name="{{verificationLink}}",
            description="Email verification URL",
            example="https://example.com/verify-email?token=xyz789"
        ),
        EmailTemplateVariable(
            name="{{userName}}",
            description="User's full name",
            example="John Doe"
        ),
        EmailTemplateVariable(
            name="{{storeName}}",
            description="Store name",
            example="Universal Store"
        ),
    ],
    "welcome": [
        EmailTemplateVariable(
            name="{{userName}}",
            description="User's full name",
            example="John Doe"
        ),
        EmailTemplateVariable(
            name="{{storeName}}",
            description="Store name",
            example="Universal Store"
        ),
        EmailTemplateVariable(
            name="{{storeUrl}}",
            description="Store URL",
            example="https://example.com"
        ),
    ],
    "order_confirmation": [
        EmailTemplateVariable(
            name="{{orderNumber}}",
            description="Order number",
            example="ORD-12345"
        ),
        EmailTemplateVariable(
            name="{{userName}}",
            description="Customer's name",
            example="John Doe"
        ),
        EmailTemplateVariable(
            name="{{orderTotal}}",
            description="Order total amount",
            example="$99.99"
        ),
        EmailTemplateVariable(
            name="{{orderDate}}",
            description="Order date",
            example="January 20, 2026"
        ),
        EmailTemplateVariable(
            name="{{orderUrl}}",
            description="Link to order details",
            example="https://example.com/orders/12345"
        ),
        EmailTemplateVariable(
            name="{{storeName}}",
            description="Store name",
            example="Universal Store"
        ),
    ],
    "order_ready": [
        EmailTemplateVariable(
            name="{{orderNumber}}",
            description="Order number",
            example="ORD-12345"
        ),
        EmailTemplateVariable(
            name="{{userName}}",
            description="Customer's name",
            example="John Doe"
        ),
        EmailTemplateVariable(
            name="{{pickupLocation}}",
            description="Pickup location name",
            example="Downtown Store"
        ),
        EmailTemplateVariable(
            name="{{pickupAddress}}",
            description="Pickup location address",
            example="123 Main St, New York, NY"
        ),
        EmailTemplateVariable(
            name="{{pickupTime}}",
            description="Pickup time slot",
            example="2:00 PM - 3:00 PM"
        ),
    ],
    "order_cancelled": [
        EmailTemplateVariable(
            name="{{orderNumber}}",
            description="Order number",
            example="ORD-12345"
        ),
        EmailTemplateVariable(
            name="{{userName}}",
            description="Customer's name",
            example="John Doe"
        ),
        EmailTemplateVariable(
            name="{{cancellationReason}}",
            description="Reason for cancellation",
            example="Customer request"
        ),
        EmailTemplateVariable(
            name="{{refundAmount}}",
            description="Refund amount",
            example="$99.99"
        ),
    ],
    "payment_received": [
        EmailTemplateVariable(
            name="{{orderNumber}}",
            description="Order number",
            example="ORD-12345"
        ),
        EmailTemplateVariable(
            name="{{userName}}",
            description="Customer's name",
            example="John Doe"
        ),
        EmailTemplateVariable(
            name="{{paymentAmount}}",
            description="Payment amount",
            example="$99.99"
        ),
        EmailTemplateVariable(
            name="{{paymentMethod}}",
            description="Payment method",
            example="Visa ending in 4242"
        ),
    ],
}


# Default templates
DEFAULT_TEMPLATES = {
    "magic_link": {
        "type": "magic_link",
        "name": "Magic Link Authentication",
        "description": "Email sent when user requests passwordless login",
        "subject": "Sign in to {{storeName}}",
        "htmlBody": """
        <html>
          <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #333;">Welcome back to {{storeName}}!</h1>
            <p>Click the button below to sign in to your account:</p>
            <a href="{{magicLink}}" style="display: inline-block; background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin: 16px 0;">Sign In</a>
            <p style="color: #666; font-size: 14px;">This link will expire in {{expiryTime}}.</p>
            <p style="color: #666; font-size: 14px;">If you didn't request this email, you can safely ignore it.</p>
          </body>
        </html>
        """,
        "textBody": "Welcome back! Click this link to sign in: {{magicLink}}\n\nThis link will expire in {{expiryTime}}.",
        "isDefault": True,
        "isActive": True
    },
    "order_confirmation": {
        "type": "order_confirmation",
        "name": "Order Confirmation",
        "description": "Email sent when order is confirmed",
        "subject": "Order {{orderNumber}} Confirmed - {{storeName}}",
        "htmlBody": """
        <html>
          <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #333;">Thank you for your order, {{userName}}!</h1>
            <p>Your order has been confirmed and will be processed shortly.</p>
            <div style="background-color: #f5f5f5; padding: 16px; border-radius: 4px; margin: 16px 0;">
              <p style="margin: 8px 0;"><strong>Order Number:</strong> {{orderNumber}}</p>
              <p style="margin: 8px 0;"><strong>Order Date:</strong> {{orderDate}}</p>
              <p style="margin: 8px 0;"><strong>Total:</strong> {{orderTotal}}</p>
            </div>
            <a href="{{orderUrl}}" style="display: inline-block; background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin: 16px 0;">View Order Details</a>
            <p style="color: #666; font-size: 14px;">Thank you for shopping with {{storeName}}!</p>
          </body>
        </html>
        """,
        "textBody": "Thank you for your order, {{userName}}!\n\nOrder Number: {{orderNumber}}\nOrder Date: {{orderDate}}\nTotal: {{orderTotal}}\n\nView your order: {{orderUrl}}",
        "isDefault": True,
        "isActive": True
    },
}


def convert_template_for_response(template: dict) -> dict:
    """Convert MongoDB template document to response format"""
    template_type = template.get("type")
    available_vars = TEMPLATE_VARIABLES.get(template_type, [])

    return {
        "id": str(template["_id"]),
        "type": template.get("type"),
        "name": template.get("name"),
        "description": template.get("description"),
        "subject": template.get("subject"),
        "htmlBody": template.get("htmlBody"),
        "textBody": template.get("textBody"),
        "availableVariables": [
            {
                "name": var.name,
                "description": var.description,
                "example": var.example
            }
            for var in available_vars
        ],
        "isActive": template.get("isActive", True),
        "isDefault": template.get("isDefault", False),
        "previewData": template.get("previewData", {}),
        "createdAt": template.get("createdAt"),
        "updatedAt": template.get("updatedAt"),
    }


def replace_variables(text: str, variables: Dict[str, str]) -> str:
    """Replace template variables with values"""
    for var_name, var_value in variables.items():
        text = text.replace(var_name, str(var_value))
    return text


# 1. GET /admin/store/email-templates - List email templates
@router.get("")
async def list_email_templates(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    template_type: Optional[str] = None,
    active: Optional[bool] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List email templates with pagination (Admin only).
    """
    query = {}
    if template_type:
        query["type"] = template_type
    if active is not None:
        query["isActive"] = active

    skip = (page - 1) * limit
    cursor = db.email_templates.find(query).sort("createdAt", -1).skip(skip).limit(limit)
    templates = await cursor.to_list(length=limit)
    total = await db.email_templates.count_documents(query)

    return {
        "success": True,
        "data": {
            "templates": [convert_template_for_response(tpl) for tpl in templates],
            "total": total
        }
    }


# 2. POST /admin/store/email-templates - Create email template
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_email_template(
    template_data: CreateEmailTemplateRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create new email template (Admin only).
    """
    # Check if active template of this type already exists
    if template_data.isActive:
        await db.email_templates.update_many(
            {"type": template_data.type, "isActive": True},
            {"$set": {"isActive": False}}
        )

    # Build template document
    template_dict = template_data.model_dump(exclude_unset=True)
    template_dict["isDefault"] = False
    template_dict["previewData"] = {}
    template_dict["createdAt"] = datetime.utcnow()
    template_dict["updatedAt"] = datetime.utcnow()

    result = await db.email_templates.insert_one(template_dict)
    template = await db.email_templates.find_one({"_id": result.inserted_id})

    return {
        "success": True,
        "message": "Email template created successfully",
        "data": convert_template_for_response(template)
    }


# 11. GET /admin/store/email-templates/variables - Get all template variables
@router.get("/variables")
async def get_template_variables(
    current_user: dict = Depends(require_admin)
):
    """
    Get available template variables for all template types (Admin only).
    """
    variables_response = {}

    for template_type, variables in TEMPLATE_VARIABLES.items():
        variables_response[template_type] = [
            {
                "name": var.name,
                "description": var.description,
                "example": var.example
            }
            for var in variables
        ]

    return {
        "success": True,
        "data": variables_response
    }

# 8. GET /admin/store/email-templates/by-type/{type} - Get template by type
@router.get("/by-type/{template_type}")
async def get_email_template_by_type(
    template_type: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get active email template by type (Admin only).
    """
    # Validate template type
    try:
        EmailTemplateType(template_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template type: {template_type}"
        )

    # Find active template of this type
    template = await db.email_templates.find_one({"type": template_type, "isActive": True})

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active template found for type: {template_type}"
        )

    return {
        "success": True,
        "data": convert_template_for_response(template)
    }


# 9. POST /admin/store/email-templates/by-type/{type}/reset - Reset to default
@router.post("/by-type/{template_type}/reset")
async def reset_template_to_default(
    template_type: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Reset template to default (Admin only).
    """
    if template_type not in DEFAULT_TEMPLATES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No default template available for type: {template_type}"
        )

    default = DEFAULT_TEMPLATES[template_type]

    # Deactivate all existing templates of this type
    await db.email_templates.update_many(
        {"type": template_type},
        {"$set": {"isActive": False}}
    )

    # Upsert default template
    await db.email_templates.update_one(
        {"type": template_type, "isDefault": True},
        {
            "$set": {
                **default,
                "updatedAt": datetime.utcnow()
            },
            "$setOnInsert": {
                "createdAt": datetime.utcnow()
            }
        },
        upsert=True
    )

    template = await db.email_templates.find_one({"type": template_type, "isDefault": True})

    return {
        "success": True,
        "message": "Template reset to default successfully",
        "data": convert_template_for_response(template)
    }


# 10. POST /admin/store/email-templates/test - Send test email
@router.post("/test")
async def send_test_email(
    test_data: SendTestEmailTemplateRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Send test email using template (Admin only).
    """
    if not validate_object_id(test_data.template_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid template ID"
        )

    # Get template
    template = await db.email_templates.find_one({"_id": ObjectId(test_data.template_id)})
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found"
        )

    # Get SMTP config
    config = await db.store_config.find_one({"key": "main"})
    if not config or not config.get("email", {}).get("smtp"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No SMTP configuration found. Please configure SMTP first."
        )

    smtp_config = config["email"]["smtp"]
    if not smtp_config.get("enabled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMTP is not enabled"
        )

    try:
        # Import required libraries
        try:
            from aiosmtplib import SMTP
            from email.message import EmailMessage
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SMTP library not available. Please install aiosmtplib."
            )

        # Replace variables in template
        preview_data = test_data.preview_data or {}
        html_body = replace_variables(template["htmlBody"], preview_data)
        subject = replace_variables(template["subject"], preview_data)
        text_body = replace_variables(template.get("textBody", ""), preview_data) if template.get("textBody") else "Test email"

        # Create email message
        message = EmailMessage()
        auth = smtp_config.get("auth", {})
        from_email = config.get("email", {}).get("fromEmail", auth.get("user"))
        message["From"] = from_email
        message["To"] = test_data.to_email
        message["Subject"] = subject

        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        # Send email
        smtp = SMTP(
            hostname=smtp_config["host"],
            port=smtp_config.get("port", 587),
            use_tls=smtp_config.get("secure", False)
        )
        await asyncio.wait_for(smtp.connect(), timeout=10.0)

        if auth.get("user") and auth.get("pass_"):
            await smtp.login(auth["user"], auth["pass_"])

        await smtp.send_message(message)
        await smtp.quit()

        return {
            "success": True,
            "message": f"Test email sent successfully to {test_data.to_email}"
        }

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Connection timeout while sending email"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test email: {str(e)}"
        )


# 3. GET /admin/store/email-templates/{id} - Get single email template
@router.get("/{template_id}")
async def get_email_template(
    template_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get email template by ID (Admin only).
    """
    if not validate_object_id(template_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid template ID"
        )

    template = await db.email_templates.find_one({"_id": ObjectId(template_id)})

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found"
        )

    return {
        "success": True,
        "data": convert_template_for_response(template)
    }


# 4. PUT /admin/store/email-templates/{id} - Update email template
@router.put("/{template_id}")
async def update_email_template(
    template_id: str,
    template_data: UpdateEmailTemplateRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update email template (Admin only).
    """
    if not validate_object_id(template_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid template ID"
        )

    # Check if template exists
    template = await db.email_templates.find_one({"_id": ObjectId(template_id)})
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found"
        )

    update_dict = template_data.model_dump(exclude_unset=True, exclude_none=False)

    # If activating this template, deactivate others of same type
    if update_dict.get("isActive"):
        template_type = template.get("type")
        await db.email_templates.update_many(
            {"type": template_type, "_id": {"$ne": ObjectId(template_id)}, "isActive": True},
            {"$set": {"isActive": False}}
        )

    update_dict["updatedAt"] = datetime.utcnow()

    await db.email_templates.update_one(
        {"_id": ObjectId(template_id)},
        {"$set": update_dict}
    )

    updated_template = await db.email_templates.find_one({"_id": ObjectId(template_id)})

    return {
        "success": True,
        "message": "Email template updated successfully",
        "data": convert_template_for_response(updated_template)
    }


# 5. DELETE /admin/store/email-templates/{id} - Delete email template
@router.delete("/{template_id}")
async def delete_email_template(
    template_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete email template (Admin only).
    """
    if not validate_object_id(template_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid template ID"
        )

    template = await db.email_templates.find_one({"_id": ObjectId(template_id)})

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found"
        )

    # Prevent deletion of default templates
    if template.get("isDefault"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete default template. You can deactivate it instead."
        )

    await db.email_templates.delete_one({"_id": ObjectId(template_id)})

    return {
        "success": True,
        "message": "Email template deleted successfully"
    }


# 6. POST /admin/store/email-templates/{id}/activate - Activate template
@router.post("/{template_id}/activate")
async def activate_email_template(
    template_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Activate email template (deactivates other templates of same type) (Admin only).
    """
    if not validate_object_id(template_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid template ID"
        )

    template = await db.email_templates.find_one({"_id": ObjectId(template_id)})

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found"
        )

    # Deactivate all other templates of this type
    template_type = template.get("type")
    await db.email_templates.update_many(
        {"type": template_type, "_id": {"$ne": ObjectId(template_id)}},
        {"$set": {"isActive": False}}
    )

    # Activate this template
    await db.email_templates.update_one(
        {"_id": ObjectId(template_id)},
        {"$set": {"isActive": True, "updatedAt": datetime.utcnow()}}
    )

    return {
        "success": True,
        "message": "Email template activated successfully"
    }


# 7. POST /admin/store/email-templates/{id}/preview - Preview template
@router.post("/{template_id}/preview")
async def preview_email_template(
    template_id: str,
    preview_data: EmailTemplatePreviewRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Preview email template with sample data (Admin only).
    """
    if not validate_object_id(template_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid template ID"
        )

    template = await db.email_templates.find_one({"_id": ObjectId(template_id)})

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found"
        )

    # Replace variables in subject, HTML, and text
    html_preview = replace_variables(template["htmlBody"], preview_data.previewData)
    subject_preview = replace_variables(template["subject"], preview_data.previewData)
    text_preview = replace_variables(template.get("textBody", ""), preview_data.previewData) if template.get("textBody") else None

    return {
        "success": True,
        "data": {
            "subject": subject_preview,
            "htmlBody": html_preview,
            "textBody": text_preview
        }
    }



"""Admin Store Configuration Endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import Optional
import asyncio

from app.database import get_database
from app.api.deps import require_admin
from app.schemas.store_config_schema import (
    StoreConfigResponse,
    UpdateStoreConfigRequest,
    UpdateBrandingRequest,
    UpdateContactRequest,
    UpdateLocaleRequest,
    UpdateEmailConfigRequest,
    UpdateSmtpConfigRequest,
    UpdatePaymentConfigRequest,
    UpdateSocialLinksRequest,
    TestSmtpRequest,
    SendTestEmailRequest,
)
from app.models.store_config import StoreConfig, LocaleConfig, BrandingConfig, ContactInfo, SocialLinks, EmailConfig, PaymentConfig, SmtpConfig

router = APIRouter()


# Helper function to get default config
def get_default_config():
    """Return default store configuration"""
    return {
        "key": "main",
        "name": None,
        "tagline": None,
        "description": None,
        "domain": None,
        "frontendUrl": None,
        "adminUrl": None,
        "supportUrl": None,
        "locale": {
            "country": None,
            "countryCode": None,
            "currency": "USD",
            "currencySymbol": "$",
            "timezone": "UTC",
            "locale": "en-US",
            "phoneCountryCode": None
        },
        "branding": {
            "logo": None,
            "logoLight": None,
            "favicon": None,
            "primaryColor": "#000000",
            "secondaryColor": "#FFFFFF"
        },
        "contact": {
            "email": None,
            "phone": None,
            "address": None,
            "city": None,
            "country": None
        },
        "socialLinks": {
            "facebook": None,
            "instagram": None,
            "twitter": None,
            "tiktok": None,
            "youtube": None,
            "whatsapp": None
        },
        "email": {
            "fromName": None,
            "fromEmail": None,
            "replyTo": None,
            "footerText": None,
            "smtp": {
                "host": None,
                "port": 587,
                "secure": False,
                "auth": None,
                "enabled": False,
                "verified": False,
                "lastTestedAt": None,
                "lastTestResult": None
            }
        },
        "payment": {
            "stripeStatementDescriptor": None,
            "stripeCurrency": "usd",
            "stripeCustomDomain": None,
            "taxRate": 0.0,
            "taxIncluded": False
        },
        "createdAt": None,
        "updatedAt": None
    }


def convert_config_for_response(config: dict) -> dict:
    """Convert MongoDB config to response format"""
    if not config:
        return get_default_config()

    # Convert _id to string if exists
    if "_id" in config:
        config.pop("_id")

    return config


# 1. GET /admin/store/config - Get full store configuration
@router.get("/config")
async def get_store_config(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get full store configuration (Admin only).
    """
    config = await db.store_config.find_one({"key": "main"})

    if not config:
        return {
            "success": True,
            "data": get_default_config()
        }

    return {
        "success": True,
        "data": convert_config_for_response(config)
    }


# 2. PUT /admin/store/config - Update store configuration
@router.put("/config")
async def update_store_config(
    config_data: UpdateStoreConfigRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update store configuration (Admin only).
    """
    update_dict = config_data.model_dump(exclude_unset=True, exclude_none=False)
    update_dict["updatedAt"] = datetime.utcnow()

    result = await db.store_config.update_one(
        {"key": "main"},
        {
            "$set": update_dict,
            "$setOnInsert": {"key": "main", "createdAt": datetime.utcnow()}
        },
        upsert=True
    )

    config = await db.store_config.find_one({"key": "main"})

    return {
        "success": True,
        "message": "Store configuration updated successfully",
        "data": convert_config_for_response(config)
    }


# 3. GET /admin/store/config/branding - Get branding config
@router.get("/config/branding")
async def get_branding_config(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get branding configuration (Admin only).
    """
    config = await db.store_config.find_one({"key": "main"})
    branding = config.get("branding", {}) if config else get_default_config()["branding"]

    return {
        "success": True,
        "data": branding
    }


# 4. PUT /admin/store/config/branding - Update branding config
@router.put("/config/branding")
async def update_branding_config(
    branding_data: UpdateBrandingRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update branding configuration (Admin only).
    """
    update_dict = branding_data.model_dump(exclude_unset=True)

    # Build nested update
    nested_update = {f"branding.{k}": v for k, v in update_dict.items()}
    nested_update["updatedAt"] = datetime.utcnow()

    await db.store_config.update_one(
        {"key": "main"},
        {
            "$set": nested_update,
            "$setOnInsert": {"key": "main", "createdAt": datetime.utcnow()}
        },
        upsert=True
    )

    config = await db.store_config.find_one({"key": "main"})
    branding = config.get("branding", {}) if config else {}

    return {
        "success": True,
        "message": "Branding configuration updated successfully",
        "data": branding
    }


# 5. GET /admin/store/config/contact - Get contact info
@router.get("/config/contact")
async def get_contact_config(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get contact information (Admin only).
    """
    config = await db.store_config.find_one({"key": "main"})
    contact = config.get("contact", {}) if config else get_default_config()["contact"]

    return {
        "success": True,
        "data": contact
    }


# 6. PUT /admin/store/config/contact - Update contact info
@router.put("/config/contact")
async def update_contact_config(
    contact_data: UpdateContactRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update contact information (Admin only).
    """
    update_dict = contact_data.model_dump(exclude_unset=True)

    # Build nested update
    nested_update = {f"contact.{k}": v for k, v in update_dict.items()}
    nested_update["updatedAt"] = datetime.utcnow()

    await db.store_config.update_one(
        {"key": "main"},
        {
            "$set": nested_update,
            "$setOnInsert": {"key": "main", "createdAt": datetime.utcnow()}
        },
        upsert=True
    )

    config = await db.store_config.find_one({"key": "main"})
    contact = config.get("contact", {}) if config else {}

    return {
        "success": True,
        "message": "Contact information updated successfully",
        "data": contact
    }


# 7. GET /admin/store/config/email - Get email config
@router.get("/config/email")
async def get_email_config(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get email configuration (Admin only).
    """
    config = await db.store_config.find_one({"key": "main"})
    email = config.get("email", {}) if config else get_default_config()["email"]

    return {
        "success": True,
        "data": email
    }


# 8. PUT /admin/store/config/email - Update email config
@router.put("/config/email")
async def update_email_config(
    email_data: UpdateEmailConfigRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update email configuration (Admin only).
    """
    update_dict = email_data.model_dump(exclude_unset=True, exclude_none=False)

    # Build nested update - handle nested smtp config separately
    nested_update = {}
    for k, v in update_dict.items():
        if k == "smtp" and isinstance(v, dict):
            for smtp_k, smtp_v in v.items():
                nested_update[f"email.smtp.{smtp_k}"] = smtp_v
        else:
            nested_update[f"email.{k}"] = v

    nested_update["updatedAt"] = datetime.utcnow()

    await db.store_config.update_one(
        {"key": "main"},
        {
            "$set": nested_update,
            "$setOnInsert": {"key": "main", "createdAt": datetime.utcnow()}
        },
        upsert=True
    )

    config = await db.store_config.find_one({"key": "main"})
    email = config.get("email", {}) if config else {}

    return {
        "success": True,
        "message": "Email configuration updated successfully",
        "data": email
    }


# 9. GET /admin/store/config/locale - Get locale config
@router.get("/config/locale")
async def get_locale_config(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get locale configuration (Admin only).
    """
    config = await db.store_config.find_one({"key": "main"})
    locale = config.get("locale", {}) if config else get_default_config()["locale"]

    return {
        "success": True,
        "data": locale
    }


# 10. PUT /admin/store/config/locale - Update locale config
@router.put("/config/locale")
async def update_locale_config(
    locale_data: UpdateLocaleRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update locale configuration (Admin only).
    """
    update_dict = locale_data.model_dump(exclude_unset=True)

    # Build nested update
    nested_update = {f"locale.{k}": v for k, v in update_dict.items()}
    nested_update["updatedAt"] = datetime.utcnow()

    await db.store_config.update_one(
        {"key": "main"},
        {
            "$set": nested_update,
            "$setOnInsert": {"key": "main", "createdAt": datetime.utcnow()}
        },
        upsert=True
    )

    config = await db.store_config.find_one({"key": "main"})
    locale = config.get("locale", {}) if config else {}

    return {
        "success": True,
        "message": "Locale configuration updated successfully",
        "data": locale
    }


# 11. GET /admin/store/config/payment - Get payment config
@router.get("/config/payment")
async def get_payment_config(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get payment configuration (Admin only).
    """
    config = await db.store_config.find_one({"key": "main"})
    payment = config.get("payment", {}) if config else get_default_config()["payment"]

    return {
        "success": True,
        "data": payment
    }


# 12. PUT /admin/store/config/payment - Update payment config
@router.put("/config/payment")
async def update_payment_config(
    payment_data: UpdatePaymentConfigRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update payment configuration (Admin only).
    """
    update_dict = payment_data.model_dump(exclude_unset=True)

    # Build nested update
    nested_update = {f"payment.{k}": v for k, v in update_dict.items()}
    nested_update["updatedAt"] = datetime.utcnow()

    await db.store_config.update_one(
        {"key": "main"},
        {
            "$set": nested_update,
            "$setOnInsert": {"key": "main", "createdAt": datetime.utcnow()}
        },
        upsert=True
    )

    config = await db.store_config.find_one({"key": "main"})
    payment = config.get("payment", {}) if config else {}

    return {
        "success": True,
        "message": "Payment configuration updated successfully",
        "data": payment
    }


# 13. GET /admin/store/config/smtp - Get SMTP config
@router.get("/config/smtp")
async def get_smtp_config(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get SMTP configuration (Admin only).
    """
    config = await db.store_config.find_one({"key": "main"})
    email_config = config.get("email", {}) if config else {}
    smtp = email_config.get("smtp", {}) if email_config else get_default_config()["email"]["smtp"]

    return {
        "success": True,
        "data": smtp
    }


# 14. PUT /admin/store/config/smtp - Update SMTP config
@router.put("/config/smtp")
async def update_smtp_config(
    smtp_data: UpdateSmtpConfigRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update SMTP configuration (Admin only).
    """
    update_dict = smtp_data.model_dump(exclude_unset=True, exclude_none=False)

    # Build nested update for smtp config
    nested_update = {}
    for k, v in update_dict.items():
        if k == "auth" and isinstance(v, dict):
            for auth_k, auth_v in v.items():
                nested_update[f"email.smtp.auth.{auth_k}"] = auth_v
        else:
            nested_update[f"email.smtp.{k}"] = v

    nested_update["updatedAt"] = datetime.utcnow()

    await db.store_config.update_one(
        {"key": "main"},
        {
            "$set": nested_update,
            "$setOnInsert": {"key": "main", "createdAt": datetime.utcnow()}
        },
        upsert=True
    )

    config = await db.store_config.find_one({"key": "main"})
    email_config = config.get("email", {}) if config else {}
    smtp = email_config.get("smtp", {}) if email_config else {}

    return {
        "success": True,
        "message": "SMTP configuration updated successfully",
        "data": smtp
    }


# 15. POST /admin/store/config/smtp/test - Test SMTP connection
@router.post("/config/smtp/test")
async def test_smtp_connection(
    smtp_data: TestSmtpRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Test SMTP connection (Admin only).
    """
    try:
        # Import aiosmtplib for async SMTP
        try:
            from aiosmtplib import SMTP
        except ImportError:
            return {
                "success": False,
                "message": "SMTP library not available. Please install aiosmtplib.",
                "data": {"connected": False, "error": "aiosmtplib not installed"}
            }

        # Test connection
        smtp = SMTP(hostname=smtp_data.host, port=smtp_data.port, use_tls=smtp_data.secure)

        try:
            await asyncio.wait_for(smtp.connect(), timeout=10.0)

            if smtp_data.user and smtp_data.pass_:
                await smtp.login(smtp_data.user, smtp_data.pass_)

            await smtp.quit()

            # Update lastTestedAt in database
            await db.store_config.update_one(
                {"key": "main"},
                {
                    "$set": {
                        "email.smtp.lastTestedAt": datetime.utcnow(),
                        "email.smtp.lastTestResult": "success",
                        "email.smtp.verified": True,
                        "updatedAt": datetime.utcnow()
                    }
                },
                upsert=True
            )

            return {
                "success": True,
                "message": "SMTP connection successful",
                "data": {"connected": True}
            }
        except asyncio.TimeoutError:
            await db.store_config.update_one(
                {"key": "main"},
                {
                    "$set": {
                        "email.smtp.lastTestedAt": datetime.utcnow(),
                        "email.smtp.lastTestResult": "Connection timeout",
                        "email.smtp.verified": False,
                        "updatedAt": datetime.utcnow()
                    }
                },
                upsert=True
            )
            return {
                "success": False,
                "message": "SMTP connection timeout",
                "data": {"connected": False, "error": "Connection timeout"}
            }
    except Exception as e:
        # Update lastTestResult in database
        await db.store_config.update_one(
            {"key": "main"},
            {
                "$set": {
                    "email.smtp.lastTestedAt": datetime.utcnow(),
                    "email.smtp.lastTestResult": str(e),
                    "email.smtp.verified": False,
                    "updatedAt": datetime.utcnow()
                }
            },
            upsert=True
        )

        return {
            "success": False,
            "message": f"SMTP connection failed: {str(e)}",
            "data": {"connected": False, "error": str(e)}
        }


# 16. POST /admin/store/config/smtp/send-test - Send test email
@router.post("/config/smtp/send-test")
async def send_test_email(
    test_data: SendTestEmailRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Send test email using SMTP configuration (Admin only).
    """
    try:
        # Import required libraries
        try:
            from aiosmtplib import SMTP
            from email.message import EmailMessage
        except ImportError:
            return {
                "success": False,
                "message": "SMTP library not available. Please install aiosmtplib."
            }

        # Get SMTP config
        if test_data.use_saved_config:
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

            host = smtp_config.get("host")
            port = smtp_config.get("port", 587)
            secure = smtp_config.get("secure", False)
            auth = smtp_config.get("auth", {})
            from_email = config.get("email", {}).get("fromEmail", auth.get("user"))
        else:
            if not test_data.smtp_config:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="SMTP configuration required when use_saved_config is False"
                )

            host = test_data.smtp_config.host
            port = test_data.smtp_config.port
            secure = test_data.smtp_config.secure or False
            auth = {"user": test_data.smtp_config.user, "pass_": test_data.smtp_config.pass_}
            from_email = test_data.smtp_config.user

        # Create email message
        message = EmailMessage()
        message["From"] = from_email
        message["To"] = test_data.to_email
        message["Subject"] = "Test Email from Universal Store"

        # Set content
        text_content = "This is a test email from Universal Store admin panel."
        html_content = """
        <html>
            <body>
                <h2>Test Email</h2>
                <p>This is a test email from Universal Store admin panel.</p>
                <p>If you received this email, your SMTP configuration is working correctly!</p>
            </body>
        </html>
        """

        message.set_content(text_content)
        message.add_alternative(html_content, subtype="html")

        # Send email
        smtp = SMTP(hostname=host, port=port, use_tls=secure)
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


# 17. GET /admin/store/config/social - Get social links
@router.get("/config/social")
async def get_social_config(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get social media links (Admin only).
    """
    config = await db.store_config.find_one({"key": "main"})
    social = config.get("socialLinks", {}) if config else get_default_config()["socialLinks"]

    return {
        "success": True,
        "data": social
    }


# 18. PUT /admin/store/config/social - Update social links
@router.put("/config/social")
async def update_social_config(
    social_data: UpdateSocialLinksRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update social media links (Admin only).
    """
    update_dict = social_data.model_dump(exclude_unset=True)

    # Build nested update
    nested_update = {f"socialLinks.{k}": v for k, v in update_dict.items()}
    nested_update["updatedAt"] = datetime.utcnow()

    await db.store_config.update_one(
        {"key": "main"},
        {
            "$set": nested_update,
            "$setOnInsert": {"key": "main", "createdAt": datetime.utcnow()}
        },
        upsert=True
    )

    config = await db.store_config.find_one({"key": "main"})
    social = config.get("socialLinks", {}) if config else {}

    return {
        "success": True,
        "message": "Social media links updated successfully",
        "data": social
    }

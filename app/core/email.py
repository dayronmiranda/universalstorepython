"""Email service for sending magic links and notifications"""

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
import logging

logger = logging.getLogger(__name__)


async def send_email(to_email: str, subject: str, html_content: str, text_content: str = None):
    """
    Send an email using SMTP

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        text_content: Plain text content (optional)
    """
    message = MIMEMultipart("alternative")
    message["From"] = settings.email_from
    message["To"] = to_email
    message["Subject"] = subject

    # Add text and HTML parts
    if text_content:
        message.attach(MIMEText(text_content, "plain"))
    message.attach(MIMEText(html_content, "html"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        logger.info(f"Email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        raise


async def send_magic_link_email(email: str, token: str, frontend_url: str = "http://localhost:3000"):
    """
    Send magic link email for passwordless authentication

    Args:
        email: User's email address
        token: Magic link token
        frontend_url: Frontend URL for constructing the magic link
    """
    magic_link = f"{frontend_url}/auth/verify?token={token}"

    subject = "Your Magic Link for JollyTienda"

    text_content = f"""
    Hello,

    Click the link below to sign in to JollyTienda:
    {magic_link}

    This link will expire in {settings.magic_link_expire_minutes} minutes.

    If you didn't request this link, you can safely ignore this email.

    Best regards,
    JollyTienda Team
    """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{
                display: inline-block;
                padding: 12px 24px;
                background-color: #4CAF50;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                margin: 20px 0;
            }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Sign in to JollyTienda</h2>
            <p>Hello,</p>
            <p>Click the button below to sign in to your account:</p>
            <a href="{magic_link}" class="button">Sign In</a>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all;">{magic_link}</p>
            <p>This link will expire in {settings.magic_link_expire_minutes} minutes.</p>
            <div class="footer">
                <p>If you didn't request this link, you can safely ignore this email.</p>
                <p>Best regards,<br>JollyTienda Team</p>
            </div>
        </div>
    </body>
    </html>
    """

    await send_email(email, subject, html_content, text_content)

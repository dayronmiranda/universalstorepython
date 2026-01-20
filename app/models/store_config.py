from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class LocaleConfig(BaseModel):
    country: Optional[str] = None
    countryCode: Optional[str] = None
    currency: Optional[str] = "USD"
    currencySymbol: Optional[str] = "$"
    timezone: Optional[str] = "UTC"
    locale: Optional[str] = "en-US"
    phoneCountryCode: Optional[str] = None


class BrandingConfig(BaseModel):
    logo: Optional[str] = None
    logoLight: Optional[str] = None
    favicon: Optional[str] = None
    primaryColor: Optional[str] = "#000000"
    secondaryColor: Optional[str] = "#FFFFFF"


class ContactInfo(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class SocialLinks(BaseModel):
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    twitter: Optional[str] = None
    tiktok: Optional[str] = None
    youtube: Optional[str] = None
    whatsapp: Optional[str] = None


class SmtpAuth(BaseModel):
    user: str
    pass_: str  # Note: Use pass_ to avoid Python keyword


class SmtpConfig(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = 587
    secure: Optional[bool] = False
    auth: Optional[SmtpAuth] = None
    enabled: Optional[bool] = False
    verified: Optional[bool] = False
    lastTestedAt: Optional[datetime] = None
    lastTestResult: Optional[str] = None


class EmailConfig(BaseModel):
    fromName: Optional[str] = None
    fromEmail: Optional[EmailStr] = None
    replyTo: Optional[EmailStr] = None
    footerText: Optional[str] = None
    smtp: Optional[SmtpConfig] = None


class PaymentConfig(BaseModel):
    stripeStatementDescriptor: Optional[str] = None
    stripeCurrency: Optional[str] = "usd"
    stripeCustomDomain: Optional[str] = None
    taxRate: Optional[float] = 0.0
    taxIncluded: Optional[bool] = False


class StoreConfig(BaseModel):
    key: str = "main"  # Singleton identifier
    name: Optional[str] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    frontendUrl: Optional[str] = None
    adminUrl: Optional[str] = None
    supportUrl: Optional[str] = None
    locale: Optional[LocaleConfig] = LocaleConfig()
    branding: Optional[BrandingConfig] = BrandingConfig()
    contact: Optional[ContactInfo] = ContactInfo()
    socialLinks: Optional[SocialLinks] = SocialLinks()
    email: Optional[EmailConfig] = EmailConfig()
    payment: Optional[PaymentConfig] = PaymentConfig()
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

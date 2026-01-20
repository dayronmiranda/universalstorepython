from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# Request schemas for nested config updates
class UpdateLocaleRequest(BaseModel):
    country: Optional[str] = None
    countryCode: Optional[str] = None
    currency: Optional[str] = None
    currencySymbol: Optional[str] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None
    phoneCountryCode: Optional[str] = None


class UpdateBrandingRequest(BaseModel):
    logo: Optional[str] = None
    logoLight: Optional[str] = None
    favicon: Optional[str] = None
    primaryColor: Optional[str] = None
    secondaryColor: Optional[str] = None


class UpdateContactRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class UpdateSocialLinksRequest(BaseModel):
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    twitter: Optional[str] = None
    tiktok: Optional[str] = None
    youtube: Optional[str] = None
    whatsapp: Optional[str] = None


class SmtpAuthRequest(BaseModel):
    user: str
    pass_: str


class UpdateSmtpConfigRequest(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    secure: Optional[bool] = None
    auth: Optional[SmtpAuthRequest] = None
    enabled: Optional[bool] = None


class UpdateEmailConfigRequest(BaseModel):
    fromName: Optional[str] = None
    fromEmail: Optional[EmailStr] = None
    replyTo: Optional[EmailStr] = None
    footerText: Optional[str] = None
    smtp: Optional[UpdateSmtpConfigRequest] = None


class UpdatePaymentConfigRequest(BaseModel):
    stripeStatementDescriptor: Optional[str] = None
    stripeCurrency: Optional[str] = None
    stripeCustomDomain: Optional[str] = None
    taxRate: Optional[float] = None
    taxIncluded: Optional[bool] = None


class UpdateStoreConfigRequest(BaseModel):
    name: Optional[str] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    frontendUrl: Optional[str] = None
    adminUrl: Optional[str] = None
    supportUrl: Optional[str] = None
    locale: Optional[UpdateLocaleRequest] = None
    branding: Optional[UpdateBrandingRequest] = None
    contact: Optional[UpdateContactRequest] = None
    socialLinks: Optional[UpdateSocialLinksRequest] = None
    email: Optional[UpdateEmailConfigRequest] = None
    payment: Optional[UpdatePaymentConfigRequest] = None


# SMTP test schemas
class TestSmtpRequest(BaseModel):
    host: str
    port: int
    secure: Optional[bool] = False
    user: Optional[str] = None
    pass_: Optional[str] = None


class SendTestEmailRequest(BaseModel):
    to_email: EmailStr
    use_saved_config: bool = True
    smtp_config: Optional[TestSmtpRequest] = None


# Response schemas
class SmtpAuthResponse(BaseModel):
    user: str
    pass_: str


class SmtpConfigResponse(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    secure: Optional[bool] = None
    auth: Optional[SmtpAuthResponse] = None
    enabled: Optional[bool] = None
    verified: Optional[bool] = None
    lastTestedAt: Optional[datetime] = None
    lastTestResult: Optional[str] = None


class EmailConfigResponse(BaseModel):
    fromName: Optional[str] = None
    fromEmail: Optional[EmailStr] = None
    replyTo: Optional[EmailStr] = None
    footerText: Optional[str] = None
    smtp: Optional[SmtpConfigResponse] = None


class LocaleConfigResponse(BaseModel):
    country: Optional[str] = None
    countryCode: Optional[str] = None
    currency: Optional[str] = None
    currencySymbol: Optional[str] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None
    phoneCountryCode: Optional[str] = None


class BrandingConfigResponse(BaseModel):
    logo: Optional[str] = None
    logoLight: Optional[str] = None
    favicon: Optional[str] = None
    primaryColor: Optional[str] = None
    secondaryColor: Optional[str] = None


class ContactInfoResponse(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class SocialLinksResponse(BaseModel):
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    twitter: Optional[str] = None
    tiktok: Optional[str] = None
    youtube: Optional[str] = None
    whatsapp: Optional[str] = None


class PaymentConfigResponse(BaseModel):
    stripeStatementDescriptor: Optional[str] = None
    stripeCurrency: Optional[str] = None
    stripeCustomDomain: Optional[str] = None
    taxRate: Optional[float] = None
    taxIncluded: Optional[bool] = None


class StoreConfigResponse(BaseModel):
    key: str
    name: Optional[str] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    frontendUrl: Optional[str] = None
    adminUrl: Optional[str] = None
    supportUrl: Optional[str] = None
    locale: Optional[LocaleConfigResponse] = None
    branding: Optional[BrandingConfigResponse] = None
    contact: Optional[ContactInfoResponse] = None
    socialLinks: Optional[SocialLinksResponse] = None
    email: Optional[EmailConfigResponse] = None
    payment: Optional[PaymentConfigResponse] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

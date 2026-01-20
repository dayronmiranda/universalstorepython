"""Application configuration using Pydantic Settings"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # App
    app_name: str = "JollyTienda API"
    debug: bool = False

    # Database
    mongodb_url: str
    mongodb_db_name: str = "jollytienda"

    # Security
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    magic_link_expire_minutes: int = 15

    # Stripe
    stripe_secret_key: str
    stripe_webhook_secret: str

    # Email
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    email_from: str

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

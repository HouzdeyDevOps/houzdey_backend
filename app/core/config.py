from typing import Annotated, Any, Literal
from pydantic import (
    AnyUrl,
    BeforeValidator,
    computed_field,
)
from pydantic_settings import BaseSettings, SettingsConfigDict # type: ignore
import os
from pathlib import Path


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 60 minutes (1 hour)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days
    
    # MongoDB Settings
    MONGO_URL: str
    
    # Environment Settings
    DOMAIN: str = "localhost"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    
    # Cloudinary Settings
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    CLOUDINARY_URL: str
    
    # Google OAuth Settings
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str 

    FACEBOOK_APP_ID: str = ""
    FACEBOOK_APP_SECRET: str = ""
    APPLE_CLIENT_ID: str = ""
    APPLE_TEAM_ID: str = ""
    APPLE_KEY_ID: str = ""
    APPLE_PRIVATE_KEY: str = ""
    
    @computed_field
    @property
    def server_host(self) -> str:
        if self.ENVIRONMENT == "local":
            return f"http://{self.DOMAIN}"
        return f"https://{self.DOMAIN}"
    
    # CORS Settings
    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []
    
    # Project Settings
    PROJECT_NAME: str = "houzdey"
    FRONTEND_URL: AnyUrl = "https://houzdey.com/"
    
    # JWT Settings
    ALGORITHM: str = "HS256"

    
    # Email Settings
    EMAIL_RESET_PASSWORD_EXPIRE_MINUTES: int = 10
    EMAIL_VERIFY_EMAIL_EXPIRE_MINUTES: int = 60 * 24 * 8
    EMAILS_FROM_NAME: str = "houzdey"
    
    # SendGrid Settings
    SENDGRID_API_KEY: str
    EMAIL_FROM: str

    DESCRIPTION: str = "Houzdey APIs"

    # Company branding
    COMPANY_LOGO_URL: str = os.getenv("COMPANY_LOGO_URL", "https://res.cloudinary.com/disbboeb4/image/upload/v1762463832/houzdey-logo_aqofgf.png")
    
    # Social media links
    FACEBOOK_URL: str = os.getenv("FACEBOOK_URL", "https://www.facebook.com/people/Houzdey/61583662165446/")
    LINKEDIN_URL: str = os.getenv("LINKEDIN_URL", "https://twitter.com/your-company")
    INSTAGRAM_URL: str = os.getenv("INSTAGRAM_URL", "https://www.instagram.com/houzdey/")

    # Media Storage Settings
    MEDIA_ROOT: Path = Path("media")
    UPLOAD_DIR: Path = MEDIA_ROOT / "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES: set = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    ALLOWED_AUDIO_TYPES: set = {"audio/webm", "audio/mp3", "audio/wav", "audio/ogg"}

    # Scraper Settings (for n8n property import)
    SCRAPER_API_KEY: str = "a997dc64c1fde3007acf6a4ea4e658f09c87cce064eb0c5df381c03a15c3b86b"  # API key for scraper authentication
    SCRAPER_BOT_USER_ID: str = "67b6abe496f181cd5b8f2424"  # User ID to assign as owner for imported properties

    def initialize(self):
        """Initialize application settings"""
        # Create media directories if they don't exist
        self.MEDIA_ROOT.mkdir(exist_ok=True)
        self.UPLOAD_DIR.mkdir(exist_ok=True)
        
        # Create subdirectories for different file types
        (self.UPLOAD_DIR / "images").mkdir(exist_ok=True)
        (self.UPLOAD_DIR / "voice").mkdir(exist_ok=True)


settings = Settings()

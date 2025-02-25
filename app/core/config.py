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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    
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

    FACEBOOK_APP_ID: str
    FACEBOOK_APP_SECRET: str
    APPLE_CLIENT_ID: str
    APPLE_TEAM_ID: str
    APPLE_KEY_ID: str
    APPLE_PRIVATE_KEY: str
    
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
    
    # SMTP Settings
    EMAIL_HOST: str
    EMAIL_PORT: int
    EMAIL_SECURE: bool = True
    EMAIL_USER: str
    EMAIL_PASS: str
    EMAIL_FROM: str
    EMAIL_TO: str

    DESCRIPTION: str = "Houzdey APIs"

    # Company branding
    COMPANY_LOGO_URL: str = os.getenv("COMPANY_LOGO_URL", "https://your-company-logo-url.com/logo.png")
    
    # Social media links
    FACEBOOK_URL: str = os.getenv("FACEBOOK_URL", "https://facebook.com/your-company")
    TWITTER_URL: str = os.getenv("TWITTER_URL", "https://twitter.com/your-company")
    INSTAGRAM_URL: str = os.getenv("INSTAGRAM_URL", "https://instagram.com/your-company")

    # Media Storage Settings
    MEDIA_ROOT: Path = Path("media")
    UPLOAD_DIR: Path = MEDIA_ROOT / "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES: set = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    ALLOWED_AUDIO_TYPES: set = {"audio/webm", "audio/mp3", "audio/wav", "audio/ogg"}

    def initialize(self):
        """Initialize application settings"""
        # Create media directories if they don't exist
        self.MEDIA_ROOT.mkdir(exist_ok=True)
        self.UPLOAD_DIR.mkdir(exist_ok=True)
        
        # Create subdirectories for different file types
        (self.UPLOAD_DIR / "images").mkdir(exist_ok=True)
        (self.UPLOAD_DIR / "voice").mkdir(exist_ok=True)


settings = Settings()

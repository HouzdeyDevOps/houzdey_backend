import secrets
from typing import Annotated, Any, Literal
import app.config
from pydantic import (
    AnyUrl,
    BeforeValidator,
    computed_field,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    PROJECT_NAME: str = "myHome"
    FRONTEND_URL: AnyUrl = "https://homely.com.ng/"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    DOMAIN: str = "localhost"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = (
        []
    )

    ALGORITHM: str = "HS256"
    EMAIL_RESET_PASSWORD_EXPIRE_MINUTES: int = 10
    EMAIL_VERIFY_EMAIL_EXPIRE_MINUTES: int = 60 * 24 * 8
    EMAILS_FROM_NAME: str = "Homely"
    EMAILS_FROM_EMAIL: str = "support@homely.com.ng"

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 465
    SMTP_HOST: str = "smtp.zeptomail.com"
    SMTP_USER: str = "emailapikey"
    SMTP_PASSWORD: str = "wSsVR61+8kTyBq54yDL8J79ukF5VAF6nEE8pjFqi7SOpH/vA8sc8kEbLDQSjFKQcEDZvF2RA8LgtzBwGh2UPjNsqzF9SXCiF9mqRe1U4J3x17qnvhDzKWmhelheOLIwOxQVvnGNhFc0g+g=="


settings = Settings()  # type: ignore

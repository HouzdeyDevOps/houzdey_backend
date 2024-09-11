import secrets
from typing import Annotated, Any, Literal
from pydantic import (
    AnyUrl,
    BeforeValidator,
    computed_field,
)
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
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    DOMAIN: str = "localhost"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def server_host(self) -> str:
        # Use HTTPS for anything other than local development
        if self.ENVIRONMENT == "local":
            return f"http://{self.DOMAIN}"
        return f"https://{self.DOMAIN}"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    # BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = (
    #     []
    # )

    PROJECT_NAME: str = "houzdey"
    FRONTEND_URL: AnyUrl = "https://houzdey.com/"

    ALGORITHM: str = "HS256"
    EMAIL_RESET_PASSWORD_EXPIRE_MINUTES: int = 10
    EMAIL_VERIFY_EMAIL_EXPIRE_MINUTES: int = 60 * 24 * 8
    EMAILS_FROM_NAME: str = "houzdey"
    EMAILS_FROM_EMAIL: str = "support@houzdey.com"

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 465
    SMTP_HOST: str = "smtp.zeptomail.com"
    SMTP_USER: str = "emailapikey"
    SMTP_PASSWORD: str = "wSsVR61+8kTyBq54yDL8J79ukF5VAF6nEE8pjFqi7SOpH/vA8sc8kEbLDQSjFKQcEDZvF2RA8LgtzBwGh2UPjNsqzF9SXCiF9mqRe1U4J3x17qnvhDzKWmhelheOLIwOxQVvnGNhFc0g+g=="


settings = Settings()  # type: ignore

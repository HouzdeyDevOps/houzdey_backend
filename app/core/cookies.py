from typing import Optional
from fastapi import Response
from app.core.config import settings


def set_auth_cookies(response: Response, access_token: str, refresh_token: Optional[str] = None) -> None:
    """Set httpOnly auth cookies on the response. Called on login, token refresh, and social auth."""
    secure = settings.ENVIRONMENT != "local"
    domain = settings.COOKIE_DOMAIN or None

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
        domain=domain,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    if refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/",
            domain=domain,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        )


def clear_auth_cookies(response: Response) -> None:
    """Clear auth cookies on logout / logout-all."""
    domain = settings.COOKIE_DOMAIN or None
    response.delete_cookie(key="access_token", path="/", domain=domain)
    response.delete_cookie(key="refresh_token", path="/", domain=domain)

# Backend Security Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the Critical/High/Medium findings from the 2026-09-28 security audit in `houzdey_backend` without breaking any existing endpoint contract that non-browser clients rely on.

**Architecture:** Nine independent-but-ordered tasks against the existing FastAPI/MongoDB app. Task 2 (cookie-based auth) is the load-bearing one — several later tasks touch functions it introduces, so it goes first among the code changes.

**Tech Stack:** FastAPI 0.110, Pydantic 2.7, Motor/MongoDB, `python-jose`, `slowapi`, Poetry.

**Spec:** `docs/superpowers/specs/2026-09-28-security-hardening-spec.md` (repo-relative: `../../../../docs/superpowers/specs/2026-09-28-security-hardening-spec.md` from this file, since the spec lives one level up at the shared `houzdey/` root — both `houzdey_backend` and `houzdey_frontend` are separate repos under it).

## Global Constraints

- No new runtime dependency may be added unless it's already in `pyproject.toml` — this environment cannot verify `poetry install`/`poetry lock` succeed against a package index, so every fix below is written using only what's already a dependency.
- **No test framework exists in this repo** (no pytest, no test dependency, no `tests/` directory). Per the spec's scope decision, this plan does not introduce one — each task's verification step is a manual `curl`/Python REPL check instead of an automated test. This is a deliberate, stated deviation from the default TDD step shape.
- Every task ends with its own commit. Do not batch multiple tasks into one commit.
- `ENVIRONMENT` (local/staging/production) and `COOKIE_DOMAIN` (new in Task 2) drive cookie `Secure`/`Domain` attributes — verify against whichever `.env` is active before testing cookie behavior locally (`ENVIRONMENT=local` is required for `Secure=False` so cookies work over plain HTTP in dev).

## Review Focus

- A stolen/blacklisted access token must be rejected the same way whether it arrives via `Authorization` header or `access_token` cookie — Task 2's `get_access_token` must not accidentally make the cookie path bypass the blacklist check that the header path already gets.
- The `iat`-based invalidation check (Task 2) must not reject *new* tokens issued after `logout-all` — only tokens issued *before* the invalidation marker. An off-by-one on the comparison direction locks every user out after their own `logout-all` call.
- The admin-role-escalation fix (Task 5) must still let a super-admin edit their own or another admin's role — the fix is "requires super-admin," not "role can never change."
- The regex-escaping fix (Task 6) must not change the *result set* for a plain alphanumeric search term — only searches containing regex metacharacters should behave differently (no longer as a pattern).
- The magic-byte upload check (Task 7) must accept every one of the 8 currently-allowed MIME types (4 image, 4 audio) — a false rejection of a legitimate `image/webp` or `audio/ogg` upload is a functional regression, not just a missed vuln.

---

### Task 1: Remove hardcoded scraper API key/user ID defaults

**Files:**
- Modify: `app/core/config.py:108-110`

**Interfaces:**
- Consumes: nothing new.
- Produces: `Settings.SCRAPER_API_KEY: str` and `Settings.SCRAPER_BOT_USER_ID: str` become required fields (no default) — `app/api/routes/properties.py:36-45` already handles a missing/unset value gracefully via `getattr(settings, 'SCRAPER_API_KEY', None)`, but since the field will now be required at `Settings()` construction time, the app fails fast at startup instead of at request time if it's missing.

- [ ] **Step 1: Remove the hardcoded defaults**

```python
# app/core/config.py — replace lines 108-110
    # Scraper Settings (for n8n property import)
    SCRAPER_API_KEY: str  # API key for scraper authentication — set via env, no default
    SCRAPER_BOT_USER_ID: str  # User ID to assign as owner for imported properties — set via env, no default
```

- [ ] **Step 2: Verify the app fails fast without the env vars, and starts with them**

Run (from `houzdey_backend/`):
```bash
python -c "from app.core.config import Settings; Settings()"
```
Expected: fails with a Pydantic validation error naming `SCRAPER_API_KEY` and `SCRAPER_BOT_USER_ID` as missing, *given the rest of the required env vars are also unset* (this repo has no `.env` checked in — this simply confirms these two fields now behave like every other required setting such as `SECRET_KEY`). With a real `.env` present that defines both, the same command should succeed silently.

- [ ] **Step 3: Commit**

```bash
git add app/core/config.py
git commit -m "security: remove hardcoded scraper API key/user ID defaults"
```

**Manual follow-up (not part of this diff, tell the user explicitly):** the key that was hardcoded in source (`a997dc64c1fde3007acf6a4ea4e658f09c87cce064eb0c5df381c03a15c3b86b`) must be treated as compromised and rotated in every deployed `.env`.

---

### Task 2: Cookie-based auth + fix token invalidation (`iat` claim)

**Files:**
- Create: `app/core/cookies.py`
- Modify: `app/core/config.py` (add `COOKIE_DOMAIN`)
- Modify: `app/core/security.py:28-48` (`create_token` — add `iat`)
- Modify: `app/api/deps.py` (new token extraction, fixed invalidation check)
- Modify: `app/api/routes/users.py` (`login_user`, `login_for_access_token`, `refresh_access_token`, `logout_user`, `logout_all_devices`)
- Modify: `app/models/user.py:76-77` (`TokenRefreshRequest.refresh_token` becomes optional)
- Modify: `app/api/routes/social_auth.py` (`google_callback`)

**Interfaces:**
- Produces: `set_auth_cookies(response: Response, access_token: str, refresh_token: Optional[str] = None) -> None` and `clear_auth_cookies(response: Response) -> None` in `app/core/cookies.py` — every later step in this task, and Task 2 only, calls these.
- Produces: `get_access_token(request: Request, credentials: Optional[HTTPAuthorizationCredentials]) -> str` in `app/api/deps.py`, replacing direct use of `oauth2_scheme` wherever the raw token string (not just the resolved user) is needed.
- Consumes: `settings.ENVIRONMENT`, `settings.COOKIE_DOMAIN`, `settings.ACCESS_TOKEN_EXPIRE_MINUTES`, `settings.REFRESH_TOKEN_EXPIRE_DAYS` (all already exist except `COOKIE_DOMAIN`).

- [ ] **Step 1: Add `COOKIE_DOMAIN` setting**

```python
# app/core/config.py — add near the JWT Settings block (after line 73, ALGORITHM)
    COOKIE_DOMAIN: str = ""  # e.g. ".houzdey.com" in production if frontend/backend are on different subdomains; "" = host-only cookie (correct for local dev)
```

- [ ] **Step 2: Add `iat` claim to every issued token**

```python
# app/core/security.py — replace line 47
    to_encode = {"exp": expire, "iat": datetime.utcnow(), "sub": str(subject), "type": type_ops}
```

- [ ] **Step 3: Create the cookie helper module**

```python
# app/core/cookies.py
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
```

- [ ] **Step 4: Rewrite `app/api/deps.py` to accept header or cookie, and to actually enforce `logout-all`**

```python
# app/api/deps.py — full file replacement
from datetime import datetime
from fastapi import Depends, HTTPException, status, Request  # type: ignore
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from jose import JWTError, jwt
from app.core.security import verify_token
from app.core.config import settings
from app.services.user_service import UserService
from app.models.user import User, UserRole
from app.core.dependencies import get_user_service
from app.repositories.token_repository import TokenRepository

# Optional bearer scheme: does not auto-error, so we can fall back to the cookie
optional_oauth2_scheme = HTTPBearer(auto_error=False)


async def get_access_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_oauth2_scheme),
) -> str:
    """
    Extract the access token from the Authorization header if present (non-browser
    clients), else from the access_token cookie (browser clients, set by login/refresh).
    """
    if credentials:
        return credentials.credentials

    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: str = Depends(get_access_token),
    user_service: UserService = Depends(get_user_service)
) -> dict:
    """
    Retrieves the current user from the provided access token (header or cookie).
    """
    token_repo = TokenRepository()

    is_blacklisted = await token_repo.is_token_blacklisted(token)
    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )

    payload = verify_token(token, expected_type="access", raise_exception=True)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired token"
        )

    try:
        user = await user_service.get_user_by_email(payload)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Enforce "logout from all devices": reject tokens issued before the invalidation marker
    invalidation_time = await token_repo.get_user_invalidation_time(user["email"])
    if invalidation_time:
        try:
            token_data = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            issued_at = datetime.utcfromtimestamp(token_data["iat"])
        except (JWTError, KeyError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked"
            )
        if issued_at < invalidation_time:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked"
            )

    return user


async def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    """Dependency to check if current user is admin or super admin"""
    if current_user["role"] not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_current_super_admin_user(current_user: dict = Depends(get_current_user)):
    """Dependency to check if current user is super admin"""
    if current_user["role"] != UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_oauth2_scheme),
    user_service: UserService = Depends(get_user_service)
) -> Optional[dict]:
    """
    Retrieves the current user if a valid token is provided (header or cookie),
    otherwise returns None. Used for endpoints that work both authenticated and not.
    """
    token = credentials.credentials if credentials else request.cookies.get("access_token")
    if not token:
        return None

    token_repo = TokenRepository()
    try:
        is_blacklisted = await token_repo.is_token_blacklisted(token)
        if is_blacklisted:
            return None

        payload = verify_token(token, expected_type="access", raise_exception=False)
        if payload is None:
            return None

        user = await user_service.get_user_by_email(payload)
        return user
    except Exception:
        return None
```

- [ ] **Step 5: Make `refresh_token` optional in the request model**

```python
# app/models/user.py — replace lines 76-77
class TokenRefreshRequest(BaseModel):
    refresh_token: Optional[str] = None
```

Add `Optional` to the existing `typing` import at the top of `app/models/user.py` if not already imported (check line 2: `from typing import List, Annotated` → change to `from typing import List, Annotated, Optional`).

- [ ] **Step 6: Set/clear cookies in `app/api/routes/users.py`**

Add to the imports at the top of the file:
```python
from fastapi import APIRouter, Depends, HTTPException, status, Form, Query, File, UploadFile, Request, Response
from app.core.cookies import set_auth_cookies, clear_auth_cookies
from app.api.deps import get_current_user, get_access_token
```
(`Response` is new in the `fastapi` import line; `get_access_token` is new in the `app.api.deps` import line — both replace the existing corresponding import lines rather than duplicating them.)

Replace `login_user` (lines 96-123):
```python
@router.post("/login")
@limiter.limit("10/minute")
async def login_user(
    request: Request,
    user_login: UserLogin,
    response: Response,
    user_service: UserService = Depends(get_user_service)
):
    """Authenticate user and return access token."""
    try:
        user = await user_service.authenticate_user(user_login.email, user_login.password)

        access_token = create_token(user["email"], "access")
        refresh_token = create_refresh_token(user["email"])
        set_auth_cookies(response, access_token, refresh_token)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user
        }
    except AuthenticationError as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
```

Replace `login_for_access_token` (lines 126-150):
```python
@router.post("/token")
@limiter.limit("10/minute")
async def login_for_access_token(
    request: Request,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: UserService = Depends(get_user_service)
):
    """OAuth2 compatible token endpoint."""
    try:
        user = await user_service.authenticate_user(form_data.username, form_data.password)

        access_token = create_token(user["email"], "access")
        refresh_token = create_refresh_token(user["email"])
        set_auth_cookies(response, access_token, refresh_token)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
```

Replace `refresh_access_token` (lines 153-202):
```python
@router.post("/refresh")
@limiter.limit("20/minute")
async def refresh_access_token(
    request: Request,
    response: Response,
    token_request: TokenRefreshRequest = TokenRefreshRequest(),
    user_service: UserService = Depends(get_user_service)
):
    """Refresh access token using refresh token (from cookie, or body for non-browser clients)."""
    try:
        refresh_token = request.cookies.get("refresh_token") or token_request.refresh_token
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No refresh token provided"
            )

        token_repo = TokenRepository()

        is_blacklisted = await token_repo.is_token_blacklisted(refresh_token)
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        email = verify_refresh_token(refresh_token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        try:
            user = await user_service.get_user_by_email(email)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        new_access_token = create_token(email, "access")
        set_auth_cookies(response, new_access_token)

        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh token: {str(e)}"
        )
```

Replace `logout_user` (lines 205-226):
```python
@router.post("/logout")
async def logout_user(
    response: Response,
    current_user: dict = Depends(get_current_user),
    token: str = Depends(get_access_token)
):
    """Logout user by blacklisting their current access token and clearing auth cookies."""
    try:
        token_repo = TokenRepository()

        await token_repo.blacklist_token(
            token=token,
            user_email=current_user["email"],
            token_type="access"
        )
        clear_auth_cookies(response)

        return {"message": "Successfully logged out"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to logout: {str(e)}"
        )
```

Replace `logout_all_devices` (lines 229-245):
```python
@router.post("/logout-all")
async def logout_all_devices(
    response: Response,
    current_user: dict = Depends(get_current_user)
):
    """Logout user from all devices by invalidating all their tokens and clearing auth cookies."""
    try:
        token_repo = TokenRepository()

        await token_repo.blacklist_all_user_tokens(current_user["email"])
        clear_auth_cookies(response)

        return {"message": "Successfully logged out from all devices"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to logout from all devices: {str(e)}"
        )
```

- [ ] **Step 7: Set cookies on Google social login**

```python
# app/api/routes/social_auth.py — top imports: add Response
from fastapi import APIRouter, HTTPException, Body, Depends, Response
from app.core.cookies import set_auth_cookies
```

```python
# app/api/routes/social_auth.py — replace the google_callback function (lines 82-105)
@router.post("/google/callback")
async def google_callback(
    response: Response,
    code: str = Body(..., embed=True),
    user_service: UserService = Depends(get_user_service)
):
    """Handle Google OAuth callback"""
    try:
        token_data = await get_google_oauth_token(code)
        user_info = await get_google_user_info(token_data["access_token"])
        user_info["password"] = secrets.token_urlsafe(32)

        result = await handle_social_auth(user_info, "google", user_service)
        set_auth_cookies(response, result["access_token"], result["refresh_token"])
        return result

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
```

- [ ] **Step 8: Verify manually**

With the server running (`ENVIRONMENT=local` in `.env`) and a real user account:
```bash
# Login — check cookies are set
curl -i -c cookies.txt -X POST http://localhost:8000/api/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<test-email>","password":"<test-password>"}'
# Expect: Set-Cookie: access_token=...; HttpOnly; SameSite=lax  and  Set-Cookie: refresh_token=...

# Use the cookie jar for an authenticated request, no Authorization header
curl -i -b cookies.txt http://localhost:8000/api/v1/users/me
# Expect: 200 with the user profile

# Confirm the header path still works independently (no cookie jar)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/users/login -H "Content-Type: application/json" -d '{"email":"<test-email>","password":"<test-password>"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -i http://localhost:8000/api/v1/users/me -H "Authorization: Bearer $TOKEN"
# Expect: 200 with the user profile

# Logout-all then retry the OLD access token
curl -i -b cookies.txt -X POST http://localhost:8000/api/v1/users/logout-all
curl -i -b cookies.txt http://localhost:8000/api/v1/users/me
# Expect: 401 "Token has been revoked" (the cookie still holds the pre-invalidation token)

# A fresh login after logout-all works again
curl -i -c cookies2.txt -X POST http://localhost:8000/api/v1/users/login -H "Content-Type: application/json" -d '{"email":"<test-email>","password":"<test-password>"}'
curl -i -b cookies2.txt http://localhost:8000/api/v1/users/me
# Expect: 200
```

- [ ] **Step 9: Commit**

```bash
git add app/core/cookies.py app/core/config.py app/core/security.py app/api/deps.py app/api/routes/users.py app/api/routes/social_auth.py app/models/user.py
git commit -m "security: httpOnly cookie auth + enforce logout-all-devices invalidation"
```

---

### Task 3: Rate-limit password-reset and OTP endpoints

**Files:**
- Modify: `app/api/routes/users.py` (`/forgot-password`, `/reset-password`, `/verify`, `/verify-code`, `/phone/send-otp`, `/phone/verify`)

**Interfaces:**
- Consumes: the `limiter` object already created at the top of this file (`limiter = Limiter(key_func=get_remote_address)`).

- [ ] **Step 1: Add `request: Request` + `@limiter.limit(...)` to each endpoint**

```python
# app/api/routes/users.py — /verify (lines 46-59)
@router.post("/verify")
@limiter.limit("5/minute")
async def verify_user_email(
    request: Request,
    user_verify: UserVerify,
    user_service: UserService = Depends(get_user_service)
):
```

```python
# /verify-code (lines 62-75)
@router.post("/verify-code")
@limiter.limit("5/minute")
async def verify_code(
    request: Request,
    user_verify: UserVerify,
    user_service: UserService = Depends(get_user_service)
):
```

```python
# /forgot-password (lines 325-336)
@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    email: str = Form(...),
    user_service: UserService = Depends(get_user_service)
):
```

```python
# /reset-password (lines 339-354)
@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    email: str = Form(...),
    reset_code: str = Form(...),
    new_password: str = Form(...),
    user_service: UserService = Depends(get_user_service)
):
```

```python
# /phone/send-otp (lines 420-431)
@router.post("/phone/send-otp")
@limiter.limit("5/minute")
async def send_phone_otp(
    request: Request,
    phone_number: str = Form(...),
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
```

```python
# /phone/verify (lines 432-445)
@router.post("/phone/verify")
@limiter.limit("5/minute")
async def verify_phone_number(
    request: Request,
    phone_number: str = Form(...),
    otp: str = Form(...),
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
```

Only the function *signatures* change (adding `request: Request` as the first parameter and the `@limiter.limit("5/minute")` decorator line) — the body of each function is untouched.

- [ ] **Step 2: Verify manually**

```bash
for i in $(seq 1 6); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/v1/users/reset-password \
    -F "email=test@example.com" -F "reset_code=000000" -F "new_password=whatever123"
done
# Expect: first 5 calls return 400 (invalid code), the 6th returns 429
```

- [ ] **Step 3: Commit**

```bash
git add app/api/routes/users.py
git commit -m "security: rate-limit password-reset and OTP endpoints"
```

---

### Task 4: Harden Google OAuth account linking

**Files:**
- Modify: `app/api/routes/social_auth.py:1-54`

**Interfaces:**
- Consumes: `user_service.get_user_by_email` (raises `NotFoundError` when absent — import from `app.core.exceptions`), `user_service.user_repo.update_by_id` (already used elsewhere in the codebase, e.g. `app/services/user_service.py:99`).

- [ ] **Step 1: Rewrite `handle_social_auth`**

```python
# app/api/routes/social_auth.py — top imports: add NotFoundError
from app.core.exceptions import NotFoundError
```

```python
# app/api/routes/social_auth.py — replace handle_social_auth (lines 17-54)
async def handle_social_auth(user_info: dict, auth_provider: str, user_service: UserService):
    if not user_info.get("email_verified", False):
        raise HTTPException(
            status_code=400,
            detail="Your Google account's email is not verified. Please verify it with Google, or sign up with a password instead."
        )

    try:
        existing_user = await user_service.get_user_by_email(user_info["email"])
    except NotFoundError:
        existing_user = None

    if existing_user:
        if not existing_user.get("email_verified", False):
            raise HTTPException(
                status_code=400,
                detail="An account with this email already exists but is not verified. Please verify your email, or sign in with a password first."
            )
        if not existing_user.get(f"{auth_provider}_id"):
            await user_service.user_repo.update_by_id(
                existing_user["id"], {f"{auth_provider}_id": user_info["sub"]}
            )
        user = existing_user
    else:
        user_data = {
            "email": user_info["email"],
            "first_name": user_info.get("given_name", ""),
            "last_name": user_info.get("family_name", ""),
            "password": user_info["password"],
            f"{auth_provider}_id": user_info["sub"],
            "email_verified": True,
            "status": UserStatus.VERIFIED.value,
            "profile_picture": user_info.get("picture", ""),
        }
        user = await user_service.create_user(user_data)

    access_token = create_token(subject=user["email"], type_ops="access")
    refresh_token = create_refresh_token(subject=user["email"])

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "status": user["status"],
            "profile_picture": user["profile_picture"],
            "phone_number": user.get("phone_number"),
            "phone_verified": user.get("phone_verified", False),
        }
    }
```

- [ ] **Step 2: Verify manually**

Reasoning-level check (no automated harness available): read through the rewritten function against these three cases and confirm by inspection, since exercising real Google OAuth end-to-end requires live Google credentials outside this environment:
1. `user_info["email_verified"] = False` → raises 400 immediately, never reaches the lookup.
2. `user_info["email_verified"] = True`, no existing user with that email → falls to the `else` branch, creates a new user exactly as before.
3. `user_info["email_verified"] = True`, existing user found with `email_verified: True` and no `google_id` set → `update_by_id` is called once, then proceeds to issue tokens for that user.

Then exercise it live once against the real Google popup flow (`GoogleAuthButton.tsx`) after Task 2/3 of the frontend plan ship, confirming a normal Google sign-in still succeeds end-to-end.

- [ ] **Step 3: Commit**

```bash
git add app/api/routes/social_auth.py
git commit -m "security: require verified email and persist google_id when linking Google sign-in"
```

---

### Task 5: Fix admin privilege-escalation via user-update endpoint

**Files:**
- Modify: `app/models/admin.py:69-78` (`UserUpdateRequest`)
- Modify: `app/api/routes/admin.py:231-271` (`update_user`)

- [ ] **Step 1: Type `role` against the enum**

```python
# app/models/admin.py — add import at top
from app.models.user import UserRole
```

```python
# app/models/admin.py — replace lines 69-78
class UserUpdateRequest(BaseModel):
    """Request model for updating user by admin"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    status: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    plan: Optional[str] = None
```

- [ ] **Step 2: Require super-admin for role/email/status changes**

```python
# app/api/routes/admin.py — replace update_user (lines 231-271)
@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    user_update: UserUpdateRequest,
    current_admin: User = Depends(get_current_admin_user)
):
    """Update user information"""
    try:
        existing_user = await user_collection.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")

        update_data = {k: v for k, v in user_update.model_dump().items() if v is not None}

        privileged_fields = {"role", "email", "status"}
        if privileged_fields & update_data.keys() and current_admin["role"] != UserRole.SUPER_ADMIN.value:
            raise HTTPException(
                status_code=403,
                detail="Only super admins can change role, email, or status"
            )

        if "role" in update_data and isinstance(update_data["role"], UserRole):
            update_data["role"] = update_data["role"].value

        if update_data:
            update_data["updated_at"] = datetime.utcnow()

            result = await user_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                await log_admin_action(
                    get_admin_id(current_admin), "UPDATE", "user", user_id,
                    f"Updated user {existing_user.get('email', 'unknown')}",
                    {"updated_fields": list(update_data.keys())}
                )
                return {"message": "User updated successfully"}
            else:
                return {"message": "No changes made"}
        else:
            return {"message": "No update data provided"}

    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update user")
```

(Added `except HTTPException: raise` before the generic `except Exception` so the new 403 isn't swallowed into a 500 — the original function had this gap too since it never raised its own `HTTPException` mid-try before this change.)

- [ ] **Step 3: Verify manually**

```bash
# As a plain admin, attempt to self-promote
curl -i -b admin_cookies.txt -X PUT http://localhost:8000/api/v1/admin/users/<own_user_id> \
  -H "Content-Type: application/json" -d '{"role":"super_admin"}'
# Expect: 403

# As a plain admin, change a non-privileged field
curl -i -b admin_cookies.txt -X PUT http://localhost:8000/api/v1/admin/users/<some_user_id> \
  -H "Content-Type: application/json" -d '{"plan":"Premium"}'
# Expect: 200

# As a super admin, change role
curl -i -b super_admin_cookies.txt -X PUT http://localhost:8000/api/v1/admin/users/<some_user_id> \
  -H "Content-Type: application/json" -d '{"role":"admin"}'
# Expect: 200

# Invalid role value is rejected by Pydantic before reaching the handler
curl -i -b super_admin_cookies.txt -X PUT http://localhost:8000/api/v1/admin/users/<some_user_id> \
  -H "Content-Type: application/json" -d '{"role":"not_a_real_role"}'
# Expect: 422
```

- [ ] **Step 4: Commit**

```bash
git add app/models/admin.py app/api/routes/admin.py
git commit -m "security: require super-admin for role/email/status changes, validate role enum"
```

---

### Task 6: Stop leaking raw exception text to clients

**Files:**
- Modify: `app/api/routes/users.py` (11 sites: lines 39-43, 55-59, 71-75, 89-93, 117-123, 145-150, 198-202, 222-226, 241-245, 318-322, 350-354 — line numbers as of *before* Task 2/3's edits to this file; re-locate each by the surrounding function name if they've shifted)
- Modify: `app/api/routes/wishlist.py:29-30, 46-47, 74-75`
- Modify: `app/services/upload.py:57-58`
- Modify: `app/utils/google_auth.py:44-48, 82-86`

**Interfaces:**
- Consumes: nothing new. Adds a module-level `logger = logging.getLogger(__name__)` to `users.py`, `wishlist.py`, and `services/upload.py` (the other two files already have one, or don't need one — `google_auth.py` gets its own).

- [ ] **Step 1: Add logging import + logger to files that lack one**

```python
# app/api/routes/users.py — add near the top imports
import logging
logger = logging.getLogger(__name__)
```

```python
# app/api/routes/wishlist.py — add near the top imports
import logging
logger = logging.getLogger(__name__)
```

```python
# app/services/upload.py — add near the top imports
import logging
logger = logging.getLogger(__name__)
```

```python
# app/utils/google_auth.py — add near the top imports
import logging
logger = logging.getLogger(__name__)
```

- [ ] **Step 2: Replace each `detail=str(e)` / `detail=f"...{str(e)}"` catch-all with a logged, generic message**

The transformation is the same at every site below: keep the `except Exception as e:` clause, add a `logger.error(...)` call that captures the real message server-side, and change the client-facing `detail` to a generic string. Apply it at each location:

`app/api/routes/users.py`, function `create_new_user` (register, originally lines 39-43):
```python
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )
```

`verify_user_email` (originally lines 55-59):
```python
    except Exception as e:
        logger.error(f"Email verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification failed. Please check your code and try again."
        )
```

`verify_code` (originally lines 71-75) — same replacement text as `verify_user_email` above.

`resend_verification_code` (originally lines 89-93):
```python
    except Exception as e:
        logger.error(f"Resend verification code failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to resend verification code. Please try again."
        )
```

`login_user` (originally lines 117-123, now inside Task 2's rewritten version):
```python
    except AuthenticationError as e:
        raise e
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
```

`refresh_access_token` (inside Task 2's rewritten version, final `except Exception`):
```python
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )
```

`logout_user` (inside Task 2's rewritten version):
```python
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout"
        )
```

`logout_all_devices` (inside Task 2's rewritten version):
```python
    except Exception as e:
        logger.error(f"Logout-all failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout from all devices"
        )
```

`update_current_user_profile` (originally lines 318-322):
```python
    except Exception as e:
        logger.error(f"Profile update failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )
```

`reset_password` (originally lines 350-354):
```python
    except Exception as e:
        logger.error(f"Password reset failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to reset password. Please check your reset code and try again."
        )
```

`app/api/routes/wishlist.py`, `add_wishlist` (lines 29-30):
```python
    except Exception as e:
        logger.error(f"Add to wishlist failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to add property to wishlist")
```

`remove_wishlist` (lines 46-47):
```python
    except Exception as e:
        logger.error(f"Remove from wishlist failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to remove property from wishlist")
```

`get_from_wishlist` (lines 74-75):
```python
    except Exception as e:
        logger.error(f"Get wishlist failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch wishlist")
```

`app/services/upload.py`, `UploadService.upload_file` (lines 57-58):
```python
        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            raise HTTPException(status_code=500, detail="File upload failed. Please try again.")
```

`app/utils/google_auth.py`, `get_google_oauth_token` (lines 44-48):
```python
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google token exchange failed: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Failed to authenticate with Google"
        )
```

`get_google_user_info` (lines 82-86):
```python
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google user info fetch failed: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Failed to get user info from Google"
        )
```

- [ ] **Step 3: Verify manually**

Trigger at least one of these paths with a deliberately broken input (e.g. `/verify-code` with a non-existent email) and confirm the HTTP response body's `detail` no longer contains raw internal text — only the generic message — while the server log line (stdout, or wherever logging is configured) shows the real exception.

- [ ] **Step 4: Commit**

```bash
git add app/api/routes/users.py app/api/routes/wishlist.py app/services/upload.py app/utils/google_auth.py
git commit -m "security: stop leaking raw exception text in API error responses"
```

---

### Task 7: Escape regex metacharacters in search filters

**Files:**
- Modify: `app/repositories/property_repository.py:1-62`
- Modify: `app/api/routes/admin.py:160-166`

- [ ] **Step 1: Escape in `PropertyRepository.find_with_filters`**

```python
# app/repositories/property_repository.py — add import at top
import re
```

```python
# app/repositories/property_repository.py — replace lines 39-46
        if search:
            escaped_search = re.escape(search)
            filter_query["$or"] = [
                {"title": {"$regex": escaped_search, "$options": "i"}},
                {"address": {"$regex": escaped_search, "$options": "i"}},
                {"description": {"$regex": escaped_search, "$options": "i"}},
                {"state": {"$regex": escaped_search, "$options": "i"}},
                {"lga": {"$regex": escaped_search, "$options": "i"}},
            ]
```

```python
# app/repositories/property_repository.py — replace lines 59-62
        if location_state:
            filter_query["state"] = {"$regex": f"^{re.escape(location_state)}$", "$options": "i"}
        if location_area:
            filter_query["lga"] = {"$regex": f"^{re.escape(location_area)}$", "$options": "i"}
```

- [ ] **Step 2: Escape in admin user search**

```python
# app/api/routes/admin.py — add import at top
import re
```

```python
# app/api/routes/admin.py — replace lines 161-166
        if search:
            escaped_search = re.escape(search)
            filter_query["$or"] = [
                {"first_name": {"$regex": escaped_search, "$options": "i"}},
                {"last_name": {"$regex": escaped_search, "$options": "i"}},
                {"email": {"$regex": escaped_search, "$options": "i"}}
            ]
```

- [ ] **Step 3: Verify manually**

```python
# Quick standalone check of the escaping behavior (no app context needed)
import re
assert re.escape("(a+)+$") == "\\(a\\+\\)\\+\\$"
```
Then, with a running app and a real property in the DB, confirm `GET /properties?search=<plain text substring of a real title>` still returns that property (regression check on normal search), and `GET /properties?search=(a+)+$` returns a normal (likely empty) result instead of hanging or erroring.

- [ ] **Step 4: Commit**

```bash
git add app/repositories/property_repository.py app/api/routes/admin.py
git commit -m "security: escape regex metacharacters in property and admin search filters"
```

---

### Task 8: Validate uploaded file content and enforce size limit

**Files:**
- Modify: `app/services/upload.py`

- [ ] **Step 1: Add a magic-byte sniffer and wire it in**

```python
# app/services/upload.py — full file
from typing import Optional
from fastapi import UploadFile, HTTPException
import cloudinary  # type: ignore
import cloudinary.uploader  # type: ignore
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)


def _sniff_content_type(header: bytes) -> Optional[str]:
    """Identify a file's real type from its leading bytes, ignoring the client-supplied Content-Type header."""
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return "image/gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    if header[:4] == b"RIFF" and header[8:12] == b"WAVE":
        return "audio/wav"
    if header.startswith(b"OggS"):
        return "audio/ogg"
    if header.startswith(b"\x1aE\xdf\xa3"):
        return "audio/webm"
    if header.startswith(b"ID3") or header[:2] == b"\xff\xfb":
        return "audio/mp3"
    return None


class UploadService:
    @staticmethod
    async def upload_file(
        file: UploadFile,
        file_type: str,
        user_id: str,
        context: str = "chat"
    ) -> str:
        try:
            if file_type not in ['image', 'voice']:
                raise HTTPException(status_code=400, detail="Invalid file type")

            allowed_types = settings.ALLOWED_IMAGE_TYPES if file_type == 'image' else settings.ALLOWED_AUDIO_TYPES

            if file.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid {file_type} type. Allowed: {', '.join(allowed_types)}"
                )

            contents = await file.read()

            if len(contents) > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB size limit"
                )

            sniffed_type = _sniff_content_type(contents[:16])
            if sniffed_type is None or sniffed_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"File content does not match a supported {file_type} format"
                )

            folder_path = f"{context}/{file_type}/{user_id}" if context == "chat" else f"{context}/{file_type}"

            upload_result = cloudinary.uploader.upload(
                contents,
                folder=folder_path,
                resource_type="auto",
                public_id=None,
                overwrite=False,
                access_mode="public",
                tags=[f"user_{user_id}", file_type, context]
            )

            return upload_result['secure_url']

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            raise HTTPException(status_code=500, detail="File upload failed. Please try again.")
```

(This also folds in Task 6's fix for this file — writing it once here since the whole function body changes anyway.)

- [ ] **Step 2: Verify manually**

```python
# Confirm the sniffer recognizes every currently-allowed type
from app.services.upload import _sniff_content_type
assert _sniff_content_type(b"\xff\xd8\xff\xe0\x00\x10JFIF") == "image/jpeg"
assert _sniff_content_type(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR") == "image/png"
assert _sniff_content_type(b"GIF89a\x01\x00\x01\x00") == "image/gif"
assert _sniff_content_type(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"
assert _sniff_content_type(b"RIFF\x00\x00\x00\x00WAVEfmt ") == "audio/wav"
assert _sniff_content_type(b"OggS\x00\x02\x00\x00") == "audio/ogg"
assert _sniff_content_type(b"\x1aE\xdf\xa3\x01\x00\x00\x00") == "audio/webm"
assert _sniff_content_type(b"ID3\x03\x00\x00\x00") == "audio/mp3"
assert _sniff_content_type(b"<?php echo 1; ?>") is None
```
Then upload a real `.jpg` through the app's chat/profile-picture upload UI and confirm it still succeeds, and try renaming a `.php`/`.html` file to `image.jpg` and re-uploading it to confirm it's now rejected with 400.

- [ ] **Step 3: Commit**

```bash
git add app/services/upload.py
git commit -m "security: validate uploaded file content by magic bytes, enforce max upload size"
```

---

### Task 9: Add baseline security headers (backend)

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add a lightweight header middleware**

```python
# main.py — add after the CORSMiddleware block (after line 57)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    if settings.ENVIRONMENT != "local":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response
```

- [ ] **Step 2: Verify manually**

```bash
curl -sI http://localhost:8000/api/v1/users/me | grep -i "x-content-type-options"
# Expect: X-Content-Type-Options: nosniff
```

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "security: add X-Content-Type-Options and HSTS response headers"
```

---

## After all tasks

Per the chosen execution approach (native, single session), run a fresh-context review of the full diff (`superpowers:requesting-code-review`) before considering this plan complete, then hand off to the frontend plan — Tasks 2–4 there depend on this plan's Task 2 (cookie contract) already being live.

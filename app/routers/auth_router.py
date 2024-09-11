from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore
from fastapi.security import OAuth2PasswordRequestForm  # type: ignore
from app.auth_handler import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token
)

from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from app.database import get_db_client, user_collection
from app.dependencies import get_current_user
from app.models import Message, NewPassword, User  # noqa
from fastapi.security import OAuth2PasswordRequestForm
from app.utils import (
    get_password_hash,
    create_token,
    verify_token,
    generate_reset_password_email,
    generate_verification_email,
    send_email,
)
from app.crud import get_user
from datetime import timedelta
from app.config import settings


# Initialize the APIRouter with a prefix of "/auth" and a tag of "auth"
router = APIRouter(prefix="/api", tags=["login"])


# Route for user login
@router.post("/login")
async def login_user_route(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    Authenticates a user using the provided email and password, and returns a new access token.
    :param form_data: The UserLogin data containing the user's email and password.
    :return: The access token and token type if the authentication is successful, an HTTPException otherwise.
    """
    user_info = await authenticate_user(form_data.username, form_data.password)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data=user_info, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/password-recovery/{email}")
async def recover_password(email: str, db: Annotated[Session, Depends(get_db_client)]):
    "Forgot password flow"
    user = await get_user(email=email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    password_reset_token = create_token(subject=email, type_ops="reset")

    # create email data
    email_data = generate_reset_password_email(
        email_to=user["email"], email=email, token=password_reset_token
    )
    send_email(
        email_to=user["email"],
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Password recovery email sent")


@router.post("/reset-password/")
async def reset_password(
    db: Annotated[Session, Depends(get_db_client)], body: NewPassword
) -> Message:
    """
    Reset password
    """
    email = verify_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")

    # Await the get_user coroutine to get the user object
    user = await get_user(email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )
    print(user, "testing")
    if not user.get("is_active"):
        raise HTTPException(status_code=400, detail="Inactive user")
    hashed_password = get_password_hash(password=body.new_password)

    await user_collection.update_one({"email": email}, {"$set": {"password": hashed_password}})

    return Message(message="Password updated successfully")

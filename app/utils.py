from datetime import datetime, timedelta
from typing import Any
from app.config import settings
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.models import TokenData
from pydantic import ValidationError
from fastapi import HTTPException, status
from jinja2 import Template
from dataclasses import dataclass
from pathlib import Path
import smtplib
import ssl
from email.message import EmailMessage

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class EmailData:
    html_content: str
    subject: str


def create_token(subject: str | Any, type_ops: str):
    if type_ops == "verify":
        hours = settings.EMAIL_VERIFY_EMAIL_EXPIRE_MINUTES
    elif type_ops == "reset":
        hours = settings.EMAIL_RESET_PASSWORD_EXPIRE_MINUTES
    elif type_ops == "access":
        hours = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    expire = datetime.utcnow() + timedelta(
        hours=hours
    )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_token_access(token: str):
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=settings.ALGORITHM
        )  # noqa
        token_data = TokenData(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    return token_data


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def verify_token(token: str) -> str | None:
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=settings.ALGORITHM
        )  # noqa
        print(decoded_token, "decoded_token")
        return str(decoded_token["sub"])
    except JWTError:
        return None


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent / "email-templates" / "build" / template_name
    ).read_text()
    html_content = Template(template_str).render(context)
    return html_content


def generate_verification_email(email_to: str, email: str, token: str):
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Email verification for user {email}"
    link = f"{settings.FRONTEND_URL}verify-email?token={token}"

    html_content = render_email_template(
        template_name="verify_email.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_VERIFY_EMAIL_EXPIRE_MINUTES,
            "link": link,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_reset_password_email(email_to: str, email: str, token: str):
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Password recovery for user {email}"
    link = f"{settings.FRONTEND_URL}reset-password?token={token}"

    html_content = render_email_template(
        template_name="reset_password.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_RESET_PASSWORD_EXPIRE_MINUTES,
            "link": link,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def send_email(email_to: str, subject: str, html_content: str):
    port = 587

    smtp_server = "smtp.zeptomail.com"
    username = "emailapikey"
    password = "wSsVR61+8kTyBq54yDL8J79ukF5VAF6nEE8pjFqi7SOpH/vA8sc8kEbLDQSjFKQcEDZvF2RA8LgtzBwGh2UPjNsqzF9SXCiF9mqRe1U4J3x17qnvhDzKWmhelheOLIwOxQVvnGNhFc0g+g=="
    message = html_content
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = "noreply@homely.com.ng"
    msg['To'] = email_to
    msg.add_alternative(message, subtype="html")
    try:
        if port == 587:
            with smtplib.SMTP(smtp_server, port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
        elif port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
                server.login(username, password)
                server.send_message(msg)
        else:
            print("use 465 / 587 as port value")
            exit()
        print("successfully sent")
    except Exception as e:
        print(e)
from dataclasses import dataclass
from pathlib import Path
import ssl
from email.message import EmailMessage
from app.core.config import settings
from jinja2 import Template
from typing import Any
import aiosmtplib # type: ignore
from datetime import datetime

@dataclass
class EmailData:
    html_content: str
    subject: str

def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent.parent / "email-templates" / "build" / template_name
    ).read_text()
    html_content = Template(template_str).render(context)
    return html_content

def generate_verification_email(email_to: str, email: str, token: str):
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Email verification for user {email}"
    link = f"{settings.FRONTEND_URL}/verify-email?token={token}"

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

async def send_email(email_to: str, subject: str, html_content: str):
    """Send email asynchronously using aiosmtplib"""
    smtp_server = settings.EMAIL_HOST
    port = settings.EMAIL_PORT
    username = settings.EMAIL_USER
    password = settings.EMAIL_PASS
    sender_email = settings.EMAIL_FROM

    message = EmailMessage()
    message["From"] = sender_email
    message["To"] = email_to
    message["Subject"] = subject
    message.add_alternative(html_content, subtype="html")

    try:
        # Configure TLS context
        tls_context = ssl.create_default_context()
        
        # Connect and send
        async with aiosmtplib.SMTP(hostname=smtp_server, port=port, use_tls=True, tls_context=tls_context) as server:
            await server.login(username, password)
            await server.send_message(message)
            print(f"Email sent successfully to {email_to}")
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        print(error_msg)
        raise Exception(error_msg)

def generate_verification_code_email(email_to: str, code: str, purpose: str = "verification") -> EmailData:
    """Generate verification code email"""
    project_name = settings.PROJECT_NAME
    
    if purpose == "reset":
        subject = f"{project_name} - Password Reset Code"
        title = "Password Reset Code"
        message = "You requested to reset your password. Use this code to complete the process:"
        button_text = "Reset Password"
    else:
        subject = f"{project_name} - Your Verification Code"
        title = "Verify Your Email"
        message = "Thanks for signing up! Use this code to verify your email address:"
        button_text = "Verify Email"

    # Template context
    context = {
        "project_name": project_name,
        "title": title,
        "message": message,
        "code": code,
        "button_text": button_text,
        "year": datetime.utcnow().year,
        "logo_url": settings.COMPANY_LOGO_URL,  # Add to your settings
        "social_links": {
            "Facebook": settings.FACEBOOK_URL,  # Add to your settings
            "Twitter": settings.TWITTER_URL,    # Add to your settings
            "Instagram": settings.INSTAGRAM_URL  # Add to your settings
        }
    }
    
    html_content = render_email_template(
        template_name="verification_code.html",
        context=context
    )
    
    return EmailData(html_content=html_content, subject=subject)

async def send_verification_code(email_to: str, code: str, purpose: str = "verification"):
    """Send verification code email"""
    email_data = generate_verification_code_email(email_to, code, purpose)
    
    await send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content
    )
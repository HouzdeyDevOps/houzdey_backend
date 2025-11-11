from dataclasses import dataclass
from pathlib import Path
from app.core.config import settings
from jinja2 import Template
from typing import Any
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import logging

logger = logging.getLogger(__name__)

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
    """Send email using SendGrid API"""
    try:
        # Create SendGrid message
        message = Mail(
            from_email=Email(settings.EMAIL_FROM, "Houzdey"),
            to_emails=To(email_to),
            subject=subject,
            html_content=Content("text/html", html_content)
        )
        
        # Send email using SendGrid API
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        
        logger.info(f"Email sent successfully to {email_to} - Status: {response.status_code}")
        print(f"Email sent successfully to {email_to} - Status: {response.status_code}")
        
        return response
        
    except Exception as e:
        error_msg = f"Failed to send email via SendGrid: {str(e)}"
        logger.error(error_msg)
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
            "Twitter": settings.LINKEDIN_URL,    # Add to your settings
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

def generate_chat_notification_email(email_to: str, sender_name: str, recipient_name: str, message_preview: str, property_title: str, chat_url: str) -> EmailData:
    """Generate chat notification email"""
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - New message from {sender_name}"

    context = {
        "project_name": project_name,
        "sender_name": sender_name,
        "recipient_name": recipient_name,
        "message_preview": message_preview,
        "property_title": property_title,
        "chat_url": chat_url,
        "year": datetime.utcnow().year,
        "logo_url": settings.COMPANY_LOGO_URL
    }
    
    html_content = render_email_template(
        template_name="chat_notification.html",
        context=context
    )
    
    return EmailData(html_content=html_content, subject=subject)
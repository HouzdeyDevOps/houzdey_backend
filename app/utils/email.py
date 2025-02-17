from dataclasses import dataclass
from pathlib import Path
import smtplib
import ssl
from email.message import EmailMessage
from app.core.config import settings
from jinja2 import Template
from typing import Any

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


def send_email(email_to: str, subject: str, html_content: str):
    smtp_server = settings.EMAIL_HOST
    port = settings.EMAIL_PORT
    username = settings.EMAIL_USER
    password = settings.EMAIL_PASS
    sender_email = settings.EMAIL_FROM

    message = html_content
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = email_to
    msg.add_alternative(message, subtype="html")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(username, password)
            server.send_message(msg)
            print(f"Email sent successfully to {email_to}")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        raise Exception(f"Failed to send email: {str(e)}")
    



def generate_verification_code_email(email_to: str, code: str) -> EmailData:
    """Generate verification code email"""
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Your verification code"
    
    html_content = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Your Verification Code</h2>
        <p>Hello,</p>
        <p>Your verification code is: <strong>{code}</strong></p>
        <p>This code will expire in 10 minutes.</p>
        <p>If you didn't request this code, please ignore this email.</p>
    </div>
    """
    
    return EmailData(html_content=html_content, subject=subject)

def send_verification_code(email_to: str, code: str):
    """Send verification code email"""
    email_data = generate_verification_code_email(email_to, code)
    
    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content
    )
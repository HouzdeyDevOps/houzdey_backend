from typing import Any
from pydantic_settings import BaseSettings  # type: ignore
import os  # Import the os module to interact with the operating system
from dotenv import load_dotenv  # type: ignore # Import the load_dotenv function from the dotenv module to load environment variables from a.env file
from fastapi_mail import ConnectionConfig


load_dotenv()  # Load environment variables from the.env file


class Settings(BaseSettings):
    # The MongoDB connection URL. This is currently set to the default local MongoDB instance.
    # mongodb_url: str = "mongodb://localhost:27017"

    # The secret key used for generating and verifying access tokens.
    secret_key: str = "1c6b3c0e9fbd0fb47fe187b1ee7f8f62ed481366d34f5ca3e667d39accd4b51f"

    # The algorithm used for generating and verifying access tokens. This is currently set to HS256.
    algorithm: str = "HS256"

    # The number of minutes before an access token expires.
    # 8 days access token expire minutes
    access_token_expire_minutes: int = 60 * 24 * 8
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "")
    APP_BASE_URL: str = "http://127.0.0.1:8000"
    SECRET_KEY: str = "cabcf753bc8f56d01e6183fa379e35601118288d148726ee"
    FORGET_PASSWORD_URL: str = 'api/v1/auth/forget-password'
    RESET_PASSWORD_URL: str = 'api/v1/auth/reset-password'

    FORGET_PASSWORD_LINK_EXPIRE_MINUTES: int = 10

    conf: Any = ConnectionConfig(
        MAIL_USERNAME="emailapikey",
        MAIL_PASSWORD="wSsVR61+8kTyBq54yDL8J79ukF5VAF6nEE8pjFqi7SOpH/vA8sc8kEbLDQSjFKQcEDZvF2RA8LgtzBwGh2UPjNsqzF9SXCiF9mqRe1U4J3x17qnvhDzKWmhelheOLIwOxQVvnGNhFc0g+g==",
        MAIL_FROM="noreply@homely.com.ng",
        MAIL_PORT=465,
        MAIL_SERVER="smtp.zeptomail.com",
        MAIL_FROM_NAME="Homely",
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )
    S3_ACCESS_KEY: str = "AKIA47CRU4UEBPPE6H76"
    S3_SECRET_KEY: str = "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"
    BUCKET_NAME: str = "myhome1"


settings = Settings()

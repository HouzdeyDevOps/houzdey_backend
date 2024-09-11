from datetime import datetime, timedelta
from typing import Annotated
from fastapi.security import OAuth2PasswordBearer  # type: ignore
from app.crud import get_user
from app.settings import settings
from passlib.context import CryptContext  # type: ignore
from jose import JWTError, jwt

#   const Usertoken = localStorage.getItem('token')

# Initialize Passlib's CryptContext with the "bcrypt" scheme and auto-deprecation
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Define the secret key, algorithm, and access token expiration time in minutes
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


# Initialize an OAuth2PasswordBearer object with the location of the token endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


# Function to verify a plaintext password against a hashed password
def verify_password(plain_password, hashed_password):
    """
    Verifies if a plaintext password matches a hashed password using the initialized CryptContext.
    :param plain_password: The plaintext password to verify.
    :param hashed_password: The hashed password to compare against.
    :return: True if the plaintext password matches the hashed password, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# Function to authenticate a user using an email and password
# async def authenticate_user(email: str, password: str):
#     """
#     Authenticates a user by retrieving the user from the database using the provided email and verifying the password.
#     :param email: The user's email address.
#     :param password: The user's plaintext password.
#     :return: The user data if the authentication is successful, None otherwise.
#     """
#     user = await get_user(email)
#     if not user or not verify_password(password, user["password"]):
#         return None
#     return user

async def authenticate_user(email: str, password: str):
    user = await get_user(email)
    print(user)
    if not user or not verify_password(password, user["password"]):
        return None
    user_info = {"sub": user["email"], "id": str(user["id"])}
    return user_info



# Function to create a new access token with the provided data and expiration time
def create_access_token(data: dict, expires_delta: Annotated[timedelta, None] = None):
    """
    Creates a new access token with the provided data and expiration time.
    :param data: The data to include in the token.
    :param expires_delta: The expiration time for the token. If not provided, a default expiration time of 15 minutes is used.
    :return: The encoded JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Function to verify JWT token and extract user information
def decode_token(token: str):
    """
    Decodes a JWT token and extracts the user information.
    :param token: The JWT token to decode.
    :return: The decoded token payload if the token is valid, None otherwise.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # return payload.get("sub")
        return payload
    except JWTError:
        return None



def create_reset_password_token(email: str):
    data = {"sub": email, "exp": datetime.utcnow() + timedelta(hours=10)}
    token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_reset_password_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY,
                   algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        return email
    except JWTError:
        return None 

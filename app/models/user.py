from pydantic import BaseModel, Field, EmailStr, StringConstraints, validator  # type: ignore
from typing import List, Annotated
from enum import Enum
from datetime import datetime

class UserStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    SUSPENDED = "suspended"

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class User(BaseModel):
    id: str | None = None
    email: EmailStr = Field(..., min_length=6)
    password: Annotated[str, StringConstraints(min_length=8)]
    first_name: str = ""
    last_name: str = ""
    phone_number: str | None = None
    phone_verified: bool = False
    date_of_birth: datetime | None = None
    email_verified: bool = False
    verification_code: str | None = None
    code_expiry: datetime | None = None
    reset_code: str | None = None
    reset_code_expiry: datetime | None = None
    status: UserStatus = UserStatus.PENDING 
    role: UserRole = UserRole.USER
    is_active: bool = False
    plan: str = "Basic"
    profile_picture: str = ""
    google_id: str | None = None
    facebook_id: str | None = None
    apple_id: str | None = None
    wishlist: List[str] = []
    bio: str | None = None
    company: str | None = None
    # Chat status fields
    chat_status: str = "offline"  # "online" or "offline"
    last_seen: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PlanBase(BaseModel):
    name: str
    price: float
    min_house: int
    max_house: int


class PlanResponse(PlanBase):
    id: str


class UserRegister(User):
    wishlist: List[str] = []
    is_active: bool = Field(
        default=False, description="Is the user active", title="Is Active"
    )


class UserResponse(User):
    id: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    # The email of the user associated with the token
    email: EmailStr


class UserLogin(BaseModel):
    email: EmailStr  # The email of the user to log in
    password: str  # The password of the user to log in


class ForgetPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str


class UserCreate(BaseModel):
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=8)]

    @validator("password")
    def validate_password(cls, value):
        # Check if password is at least 8 characters long
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        # Check if password contains a number
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must include a number")
        # Check if password contains an uppercase letter
        if not any(char.isupper() for char in value):
            raise ValueError("Password must include an uppercase letter")
        # Check if password contains a lowercase letter
        if not any(char.islower() for char in value):
            raise ValueError("Password must include a lowercase letter")
        return value


class UserVerify(BaseModel):
    email: EmailStr
    code: str


class UserPersonalInfo(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: str
    date_of_birth: datetime
    profile_picture: str | None = None

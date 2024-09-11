# Property Listing API Endpoint

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.api.models.property import PropertyModel
from app.api.schemas.property import PropertyCreate, PropertyResponse
from app.db.mongodb import get_database

router = APIRouter()

@router.post("/properties/", response_model=PropertyResponse)
async def create_property(property: PropertyCreate, db=Depends(get_database)):
    property_dict = property.dict()
    new_property = await db["properties"].insert_one(property_dict)
    created_property = await db["properties"].find_one({"_id": new_property.inserted_id})
    return PropertyResponse(**created_property)

@router.get("/properties/", response_model=List[PropertyResponse])
async def list_properties(skip: int = 0, limit: int = 10, db=Depends(get_database)):
    properties = await db["properties"].find().skip(skip).limit(limit).to_list(length=limit)
    return [PropertyResponse(**prop) for prop in properties]

@router.get("/properties/{property_id}", response_model=PropertyResponse)
async def get_property(property_id: str, db=Depends(get_database)):
    property = await db["properties"].find_one({"_id": property_id})
    if property is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return PropertyResponse(**property)

@router.put("/properties/{property_id}", response_model=PropertyResponse)
async def update_property(property_id: str, property: PropertyCreate, db=Depends(get_database)):
    updated_property = await db["properties"].find_one_and_update(
        {"_id": property_id},
        {"$set": property.dict()},
        return_document=True
    )
    if updated_property is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return PropertyResponse(**updated_property)

@router.delete("/properties/{property_id}", response_model=dict)
async def delete_property(property_id: str, db=Depends(get_database)):
    delete_result = await db["properties"].delete_one({"_id": property_id})
    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Property not found")
    return {"message": "Property successfully deleted"}

# User Authentication
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from app.api.models.user import UserModel
from app.api.schemas.user import UserCreate, UserResponse, Token
from app.db.mongodb import get_database
from app.core.config import SECRET_KEY, ALGORITHM

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def authenticate_user(db, email: str, password: str):
    user = await db["users"].find_one({"email": email})
    if not user or not verify_password(password, user["password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate, db=Depends(get_database)):
    db_user = await db["users"].find_one({"email": user.email})
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    user_dict = user.dict()
    user_dict["password"] = hashed_password
    new_user = await db["users"].insert_one(user_dict)
    created_user = await db["users"].find_one({"_id": new_user.inserted_id})
    return UserResponse(**created_user)

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_database)):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}



# app/api/schemas/property.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class PropertyBase(BaseModel):
    title: str
    description: str
    price: float
    location: dict
    property_type: str
    bedrooms: int
    bathrooms: int
    amenities: List[str]
    images: List[str]
    availability_status: str

class PropertyCreate(PropertyBase):
    owner_id: str

class PropertyUpdate(PropertyBase):
    pass

class PropertyInDB(PropertyBase):
    id: str = Field(..., alias="_id")
    owner_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True

class PropertyResponse(PropertyInDB):
    pass

# app/api/schemas/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: EmailStr
    contact_info: str

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None
    profile_picture: Optional[str] = None
    verification_status: Optional[bool] = None

class UserInDB(UserBase):
    id: str = Field(..., alias="_id")
    password: str
    profile_picture: Optional[str] = None
    verification_status: bool = False
    listed_properties: List[str] = []
    saved_searches: List[dict] = []
    favorite_properties: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True

class UserResponse(UserBase):
    id: str
    profile_picture: Optional[str] = None
    verification_status: bool
    listed_properties: List[str]
    favorite_properties: List[str]

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# app/api/schemas/message.py
from pydantic import BaseModel, Field
from datetime import datetime

class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    sender_id: str
    receiver_id: str

class MessageUpdate(MessageBase):
    read_status: bool

class MessageInDB(MessageBase):
    id: str = Field(..., alias="_id")
    sender_id: str
    receiver_id: str
    timestamp: datetime
    read_status: bool

    class Config:
        allow_population_by_field_name = True

class MessageResponse(MessageInDB):
    pass

# app/api/schemas/transaction.py
from pydantic import BaseModel, Field
from datetime import datetime

class TransactionBase(BaseModel):
    property_id: str
    user_id: str
    amount: float
    transaction_type: str
    status: str

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    status: str

class TransactionInDB(TransactionBase):
    id: str = Field(..., alias="_id")
    timestamp: datetime

    class Config:
        allow_population_by_field_name = True

class TransactionResponse(TransactionInDB):
    pass

# Database Connection using asyncio with motor
import motor.motor_asyncio
from config import MONGODB_URL  # Assuming you have a config file with your MongoDB URL

client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
db = client.houzdey_db  # Replace 'houzdey_db' with your actual database name

async def connect_to_mongo():
    try:
        await client.server_info()
        print("Connected to MongoDB")
    except Exception as e:
        print(f"Unable to connect to MongoDB: {e}")

async def close_mongo_connection():
    client.close()
    print("MongoDB connection closed")


# users.py file:
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from bson import ObjectId
from database import db  # Import the db instance from your database connection file
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = "your-secret-key"  # Replace with a secure secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone_number: str

class UserInDB(UserCreate):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_user(email: str):
    user = await db.users.find_one({"email": email})
    if user:
        return UserInDB(**user)

async def authenticate_user(email: str, password: str):
    user = await get_user(email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = await get_user(email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

# Routes
@router.post("/register", response_model=Token)
async def register_user(user: UserCreate):
    db_user = await get_user(user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    user_dict = user.dict()
    user_dict["hashed_password"] = hashed_password
    del user_dict["password"]
    new_user = await db.users.insert_one(user_dict)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me")
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    return current_user

# Email verification
async def send_verification_email(email: str, verification_token: str):
    # Implement your email sending logic here
    # For demonstration purposes, we'll just print the token
    print(f"Verification token for {email}: {verification_token}")

@router.post("/verify-email")
async def request_email_verification(current_user: UserInDB = Depends(get_current_user)):
    verification_token = secrets.token_urlsafe(32)
    await db.users.update_one(
        {"_id": current_user.id},
        {"$set": {"email_verification_token": verification_token}}
    )
    await send_verification_email(current_user.email, verification_token)
    return {"message": "Verification email sent"}

@router.get("/verify-email/{token}")
async def verify_email(token: str):
    user = await db.users.find_one({"email_verification_token": token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"email_verified": True}, "$unset": {"email_verification_token": ""}}
    )
    return {"message": "Email verified successfully"}

# Password reset
async def send_password_reset_email(email: str, reset_token: str):
    # Implement your email sending logic here
    # For demonstration purposes, we'll just print the token
    print(f"Password reset token for {email}: {reset_token}")

@router.post("/forgot-password")
async def forgot_password(email: EmailStr):
    user = await get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    reset_token = secrets.token_urlsafe(32)
    await db.users.update_one(
        {"email": email},
        {"$set": {"password_reset_token": reset_token}}
    )
    await send_password_reset_email(email, reset_token)
    return {"message": "Password reset email sent"}

@router.post("/reset-password/{token}")
async def reset_password(token: str, new_password: str):
    user = await db.users.find_one({"password_reset_token": token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset token")
    hashed_password = get_password_hash(new_password)
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"hashed_password": hashed_password}, "$unset": {"password_reset_token": ""}}
    )
    return {"message": "Password reset successfully"}

# Google Auth (You'll need to implement Google OAuth2 flow)
# This is a placeholder for Google Auth implementation
@router.get("/auth/google")
async def google_auth():
    # Implement Google OAuth2 flow
    pass

@router.get("/auth/google/callback")
async def google_auth_callback():
    # Handle Google OAuth2 callback
    pass
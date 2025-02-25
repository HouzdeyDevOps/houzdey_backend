from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from enum import Enum

def utc_now():
    """Get current UTC time with timezone info"""
    return datetime.now(timezone.utc)

def format_datetime(dt: datetime) -> str:
    """Format datetime to ISO format with UTC timezone"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"

class MessageCreate(BaseModel):
    """Schema for creating a new message"""
    content: str = Field(..., min_length=1, max_length=5000)

class Message(BaseModel):
    """Schema for a chat message"""
    id: Optional[str] = None
    conversation_id: str
    sender_id: str
    content: str
    type: MessageType = MessageType.TEXT
    file_url: Optional[str] = None
    duration: Optional[int] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime
    read: bool = False
    
    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: format_datetime
        }

class Conversation(BaseModel):
    """Schema for a chat conversation"""
    id: Optional[str] = None
    property_id: str
    user_id: str
    owner_id: str
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread_count: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    
    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: format_datetime
        }

class TypingStatus(BaseModel):
    """Schema for typing status updates"""
    conversation_id: str
    user_id: str
    is_typing: bool

class ConversationCreate(BaseModel):
    """Schema for creating a new conversation"""
    property_id: str

class MessageResponse(BaseModel):
    """Schema for message responses"""
    id: str
    conversation_id: str
    sender_id: str
    content: str
    created_at: datetime
    read: bool

    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: format_datetime
        }

class PropertyInConversation(BaseModel):
    """Schema for property details in conversation"""
    id: str
    title: str
    image: Optional[str]
    price: float
    location: str
    type: str
    status: str

class UserInConversation(BaseModel):
    """Schema for user details in conversation"""
    id: str
    first_name: str
    last_name: str
    profile_picture: Optional[str]
    email: str
    phone: Optional[str]

class ConversationResponse(BaseModel):
    """Schema for conversation responses with additional details"""
    id: str
    property_id: str
    property: PropertyInConversation
    user_id: str
    owner_id: str
    other_user: UserInConversation
    last_message: Optional[str]
    last_message_time: Optional[datetime]
    unread_count: int = 0
    created_at: datetime

    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: format_datetime
        }
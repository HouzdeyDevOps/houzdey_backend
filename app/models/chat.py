from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId

class MessageCreate(BaseModel):
    """Schema for creating a new message"""
    content: str = Field(..., min_length=1, max_length=5000)

class Message(BaseModel):
    """Schema for a chat message"""
    id: Optional[str] = None
    conversation_id: str
    sender_id: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    read: bool = False
    
    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
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
            datetime: lambda dt: dt.isoformat()
        }



class PropertyInConversation(BaseModel):
    id: str
    title: str
    image: Optional[str]
    price: float
    location: str
    type: str  # Add property type
    status: str  # Add property status

class UserInConversation(BaseModel):
    id: str
    first_name: str
    last_name: str
    profile_picture: Optional[str]
    email: str  # Add email for contact purposes
    phone: Optional[str]  # Add phone for contact purposes 


class ConversationResponse(BaseModel):
    """Schema for conversation responses with additional details"""
    id: str
    property_id: str
    property: PropertyInConversation
    other_user: UserInConversation
    user_id: str
    owner_id: str
    last_message: Optional[str]
    last_message_time: Optional[datetime]
    unread_count: int = 0
    created_at: datetime

    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
        }
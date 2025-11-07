from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TicketCategory(str, Enum):
    TECHNICAL = "technical"
    BILLING = "billing"
    ACCOUNT = "account"
    LISTING = "listing"
    OTHER = "other"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SupportTicketCreate(BaseModel):
    subject: str = Field(..., min_length=3, max_length=200)
    category: TicketCategory
    description: str = Field(..., min_length=10)
    attachments: Optional[List[str]] = None  # URLs to uploaded files


class SupportTicketUpdate(BaseModel):
    subject: Optional[str] = None
    category: Optional[TicketCategory] = None
    description: Optional[str] = None
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    admin_notes: Optional[str] = None


class SupportTicket(BaseModel):
    id: str
    user_id: str
    user_email: str
    user_name: str
    subject: str
    category: TicketCategory
    description: str
    status: TicketStatus = TicketStatus.OPEN
    priority: TicketPriority = TicketPriority.MEDIUM
    attachments: Optional[List[str]] = None
    admin_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FeedbackCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=10)
    page_url: Optional[str] = None
    category: Optional[str] = None


class Feedback(BaseModel):
    id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    rating: int
    comment: str
    page_url: Optional[str] = None
    category: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TicketResponse(BaseModel):
    id: str
    ticket_id: str
    user_id: str
    user_name: str
    user_email: str
    is_admin: bool = False
    message: str
    attachments: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TicketResponseCreate(BaseModel):
    message: str = Field(..., min_length=1)
    attachments: Optional[List[str]] = None

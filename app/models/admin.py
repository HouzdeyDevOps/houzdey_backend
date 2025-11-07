from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class AdminStats(BaseModel):
    """Admin dashboard statistics"""
    total_users: int
    total_properties: int
    total_conversations: int
    active_users: int
    pending_verifications: int
    total_revenue: float
    properties_by_type: Dict[str, int]
    users_by_status: Dict[str, int]
    monthly_signups: List[Dict[str, Any]]
    recent_activities: List[Dict[str, Any]]

class UserManagementStats(BaseModel):
    """User management statistics"""
    total_users: int
    verified_users: int
    pending_users: int
    suspended_users: int
    users_with_properties: int
    recent_registrations: List[Dict[str, Any]]

class PropertyManagementStats(BaseModel):
    """Property management statistics"""
    total_properties: int
    active_properties: int
    pending_properties: int
    sold_properties: int
    rented_properties: int
    properties_by_location: Dict[str, int]
    recent_listings: List[Dict[str, Any]]

class SystemSettings(BaseModel):
    """System settings model"""
    id: Optional[str] = None
    site_name: str = "Houzdey"
    site_description: str = "Find your perfect home"
    contact_email: str = "admin@houzdey.com"
    support_phone: str = "+234-XXX-XXX-XXXX"
    maintenance_mode: bool = False
    allow_new_registrations: bool = True
    email_verification_required: bool = True
    phone_verification_required: bool = False
    max_properties_per_user: int = 50
    max_images_per_property: int = 10
    max_file_size: int = 5242880  # 5MB in bytes
    allowed_file_types: List[str] = ["jpg", "jpeg", "png", "gif"]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AdminAction(BaseModel):
    """Admin action log model"""
    id: Optional[str] = None
    admin_id: str
    action_type: str
    target_type: str  # user, property, system, etc.
    target_id: Optional[str] = None
    description: str
    metadata: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserUpdateRequest(BaseModel):
    """Request model for updating user by admin"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    status: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    plan: Optional[str] = None

class BulkUserAction(BaseModel):
    """Bulk user action model"""
    user_ids: List[str]
    action: str  # suspend, activate, delete, change_role
    value: Optional[str] = None  # for role changes

class ContentModerationAction(BaseModel):
    """Content moderation action model"""
    content_type: str  # property, review, message
    content_id: str
    action: str  # approve, reject, flag
    reason: Optional[str] = None
    admin_notes: Optional[str] = None

class ReportResponse(BaseModel):
    """Report response model"""
    id: Optional[str] = None
    report_type: str
    reported_by: str
    reported_content_type: str
    reported_content_id: str
    reason: str
    description: Optional[str] = None
    status: str = "pending"  # pending, investigating, resolved, dismissed
    admin_notes: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class NotificationTemplate(BaseModel):
    """Notification template model"""
    id: Optional[str] = None
    name: str
    subject: str
    body: str
    template_type: str  # email, sms, push
    variables: List[str] = []
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow) 
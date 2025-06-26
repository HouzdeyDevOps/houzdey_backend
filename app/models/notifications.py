from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class NotificationType(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"

class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"

class NotificationCategory(str, Enum):
    PROPERTY = "property"
    USER = "user"
    SECURITY = "security"
    MARKETING = "marketing"
    SYSTEM = "system"
    CHAT = "chat"

class NotificationEvent(str, Enum):
    # Property events
    PROPERTY_VIEWED = "property_viewed"
    PROPERTY_INQUIRY = "property_inquiry"
    PROPERTY_APPROVED = "property_approved"
    PROPERTY_REJECTED = "property_rejected"
    PROPERTY_EXPIRED = "property_expired"
    PROPERTY_UPDATED = "property_updated"
    
    # User events
    USER_REGISTERED = "user_registered"
    USER_VERIFIED = "user_verified"
    USER_LOGIN = "user_login"
    PASSWORD_RESET = "password_reset"
    PROFILE_UPDATED = "profile_updated"
    
    # Chat events
    NEW_MESSAGE = "new_message"
    CHAT_STARTED = "chat_started"
    
    # Security events
    SUSPICIOUS_LOGIN = "suspicious_login"
    ACCOUNT_LOCKED = "account_locked"
    
    # Marketing events
    NEWSLETTER = "newsletter"
    PROMOTIONAL = "promotional"
    MARKET_UPDATE = "market_update"
    
    # System events
    MAINTENANCE = "maintenance"
    SYSTEM_UPDATE = "system_update"

class NotificationTemplate(BaseModel):
    """Notification template for different events"""
    id: Optional[str] = None
    name: str
    event: NotificationEvent
    category: NotificationCategory
    type: NotificationType
    
    # Template content
    subject: str
    body: str
    html_body: Optional[str] = None
    
    # Template variables
    variables: List[str] = []
    
    # Configuration
    is_active: bool = True
    priority: int = 1  # 1=low, 2=medium, 3=high, 4=critical
    
    # Scheduling
    send_immediately: bool = True
    delay_minutes: int = 0
    
    # Personalization
    personalized: bool = True
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class NotificationPreference(BaseModel):
    """User notification preferences"""
    id: Optional[str] = None
    user_id: str
    
    # Channel preferences
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    in_app_enabled: bool = True
    
    # Category preferences
    property_notifications: bool = True
    chat_notifications: bool = True
    security_notifications: bool = True
    marketing_notifications: bool = False
    system_notifications: bool = True
    
    # Frequency settings
    instant_notifications: bool = True
    daily_digest: bool = False
    weekly_digest: bool = False
    
    # Contact info
    phone_number: Optional[str] = None
    preferred_time_start: str = "09:00"
    preferred_time_end: str = "18:00"
    timezone: str = "Africa/Lagos"
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Notification(BaseModel):
    """Individual notification record"""
    id: Optional[str] = None
    user_id: str
    template_id: Optional[str] = None
    
    # Notification details
    event: NotificationEvent
    category: NotificationCategory
    type: NotificationType
    
    # Content
    subject: str
    body: str
    html_body: Optional[str] = None
    
    # Delivery info
    recipient_email: Optional[EmailStr] = None
    recipient_phone: Optional[str] = None
    recipient_device_token: Optional[str] = None
    
    # Status tracking
    status: NotificationStatus = NotificationStatus.PENDING
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Priority and scheduling
    priority: int = 1
    scheduled_for: Optional[datetime] = None
    
    # Metadata
    context_data: Dict[str, Any] = {}
    tracking_id: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class NotificationBatch(BaseModel):
    """Batch notification for bulk sending"""
    id: Optional[str] = None
    name: str
    template_id: str
    
    # Target audience
    user_ids: List[str] = []
    user_filters: Dict[str, Any] = {}  # e.g., {"status": "verified", "location": "Lagos"}
    
    # Scheduling
    send_immediately: bool = True
    scheduled_for: Optional[datetime] = None
    
    # Status
    status: str = "draft"  # draft, scheduled, sending, completed, failed
    total_recipients: int = 0
    sent_count: int = 0
    delivered_count: int = 0
    failed_count: int = 0
    
    # Results
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class NotificationAnalytics(BaseModel):
    """Analytics for notification performance"""
    template_id: str
    template_name: str
    event: NotificationEvent
    type: NotificationType
    
    # Period
    period_start: datetime
    period_end: datetime
    
    # Delivery metrics
    total_sent: int
    total_delivered: int
    total_failed: int
    delivery_rate: float
    
    # Engagement metrics
    total_opened: int
    total_clicked: int
    open_rate: float
    click_rate: float
    
    # Performance by time
    hourly_stats: List[Dict[str, Any]]
    daily_stats: List[Dict[str, Any]]
    
    # Demographics
    device_stats: Dict[str, int]
    location_stats: Dict[str, int]
    
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class EmailConfig(BaseModel):
    """Email service configuration"""
    provider: str = "smtp"  # smtp, sendgrid, mailgun, ses
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    api_key: Optional[str] = None
    from_email: EmailStr
    from_name: str = "Houzdey"
    reply_to: Optional[EmailStr] = None

class SMSConfig(BaseModel):
    """SMS service configuration"""
    provider: str = "twilio"  # twilio, nexmo, clickatell
    api_key: str
    api_secret: str
    sender_id: str = "Houzdey"
    webhook_url: Optional[str] = None

class NotificationQueue(BaseModel):
    """Queue item for processing notifications"""
    id: Optional[str] = None
    notification_id: str
    priority: int = 1
    scheduled_for: datetime
    retry_count: int = 0
    status: str = "queued"  # queued, processing, completed, failed
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None 
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from app.services.base_service import BaseService
from app.repositories.base import BaseRepository
from app.core.database import db_manager
from app.core.exceptions import ValidationError, NotFoundError, BusinessLogicError


class NotificationType(str, Enum):
    PROPERTY_INQUIRY = "property_inquiry"
    REVIEW_RECEIVED = "review_received" 
    MESSAGE_RECEIVED = "message_received"


class NotificationService(BaseService):
    """Service for notification-related business logic"""
    
    def __init__(self):
        self.notifications_collection = db_manager.get_collection("notifications")
        self.notification_preferences_collection = db_manager.get_collection("notification_preferences")
        super().__init__()
    
    async def create_notification(self, user_id: str, title: str, message: str) -> Dict[str, Any]:
        """Create a new notification"""
        notification_data = {
            "user_id": user_id,
            "title": title,
            "message": message,
            "status": "unread",
            "created_at": datetime.utcnow()
        }
        
        self.logger.info(f"Notification created for user {user_id}: {title}")
        return notification_data
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import smtplib
import ssl
try:
    from email.mime.text import MIMEText as MimeText
    from email.mime.multipart import MIMEMultipart as MimeMultipart
    from email.mime.base import MIMEBase as MimeBase
    from email import encoders
except ImportError:
    # Fallback for older Python versions
    from email.MIMEText import MIMEText as MimeText
    from email.MIMEMultipart import MIMEMultipart as MimeMultipart  
    from email.MIMEBase import MIMEBase as MimeBase
    from email import Encoders as encoders
import json
import uuid

from app.core.database import (
    notifications_collection,
    notification_preferences_collection,
    notification_templates_collection,
    notification_queue_collection,
    user_collection
)
from app.models.notifications import (
    Notification,
    NotificationTemplate,
    NotificationPreference,
    NotificationEvent,
    NotificationType,
    NotificationStatus,
    NotificationCategory,
    EmailConfig,
    SMSConfig
)
from app.models.user import User

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for handling all notification operations"""
    
    def __init__(self):
        self.email_config: Optional[EmailConfig] = None
        self.sms_config: Optional[SMSConfig] = None
        self._default_templates: Dict[str, Dict] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default notification templates"""
        self._default_templates = {
            "user_registered": {
                "subject": "Welcome to Houzdey! 🏠",
                "body": "Welcome to Houzdey! Your account has been created successfully.",
                "html_body": "<h1>Welcome to Houzdey!</h1><p>Your account has been created successfully.</p>"
            },
            "property_inquiry": {
                "subject": "New Inquiry for Your Property",
                "body": "You have a new inquiry for your property.",
                "html_body": "<h1>New Property Inquiry</h1><p>You have a new inquiry for your property.</p>"
            }
        }
    
    async def setup_email_config(self, config: EmailConfig):
        """Setup email configuration"""
        self.email_config = config
    
    async def setup_sms_config(self, config: SMSConfig):
        """Setup SMS configuration"""
        self.sms_config = config
    
    async def send_notification(
        self,
        user_id: str,
        event: NotificationEvent,
        context_data: Dict[str, Any],
        priority: int = 1,
        scheduled_for: Optional[datetime] = None
    ) -> Optional[str]:
        """Send a notification to a user"""
        try:
            # Get user preferences
            user_prefs = await self._get_user_preferences(user_id)
            if not user_prefs:
                logger.warning(f"No notification preferences found for user {user_id}")
                return None
            
            # Get user details
            user = await user_collection.find_one({"_id": user_id})
            if not user:
                logger.error(f"User {user_id} not found")
                return None
            
            # Check if user wants this type of notification
            if not self._should_send_notification(event, user_prefs):
                logger.info(f"User {user_id} has disabled notifications for {event}")
                return None
            
            # Get or create template
            template = await self._get_template_for_event(event)
            if not template:
                logger.error(f"No template found for event {event}")
                return None
            
            # Determine notification types to send
            notification_types = self._get_notification_types(user_prefs, template)
            
            # Create notifications for each type
            notification_ids = []
            for notif_type in notification_types:
                notification_id = await self._create_notification(
                    user_id=user_id,
                    user=user,
                    template=template,
                    notification_type=notif_type,
                    context_data=context_data,
                    priority=priority,
                    scheduled_for=scheduled_for
                )
                if notification_id:
                    notification_ids.append(notification_id)
            
            # Queue notifications for processing
            for notification_id in notification_ids:
                await self._queue_notification(notification_id, priority, scheduled_for)
            
            return notification_ids[0] if notification_ids else None
            
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return None
    
    async def _get_user_preferences(self, user_id: str) -> Optional[NotificationPreference]:
        """Get user notification preferences"""
        prefs = await notification_preferences_collection.find_one({"user_id": user_id})
        if prefs:
            prefs["id"] = str(prefs["_id"])
            del prefs["_id"]
            return NotificationPreference(**prefs)
        
        # Create default preferences if none exist
        default_prefs = NotificationPreference(user_id=user_id)
        await notification_preferences_collection.insert_one(default_prefs.model_dump())
        return default_prefs
    
    def _should_send_notification(self, event: NotificationEvent, prefs: NotificationPreference) -> bool:
        """Check if notification should be sent based on user preferences"""
        # Map events to preference settings
        event_to_pref = {
            NotificationEvent.PROPERTY_INQUIRY: prefs.property_notifications,
            NotificationEvent.PROPERTY_VIEWED: prefs.property_notifications,
            NotificationEvent.NEW_MESSAGE: prefs.chat_notifications,
            NotificationEvent.CHAT_STARTED: prefs.chat_notifications,
            NotificationEvent.USER_REGISTERED: prefs.system_notifications,
            NotificationEvent.PASSWORD_RESET: prefs.security_notifications,
            NotificationEvent.SUSPICIOUS_LOGIN: prefs.security_notifications,
        }
        
        return event_to_pref.get(event, True)  # Default to True for unknown events
    
    async def _get_template_for_event(self, event: NotificationEvent) -> Optional[NotificationTemplate]:
        """Get template for a specific event"""
        # Try to get from database first
        template_doc = await notification_templates_collection.find_one({
            "event": event,
            "is_active": True
        })
        
        if template_doc:
            template_doc["id"] = str(template_doc["_id"])
            del template_doc["_id"]
            return NotificationTemplate(**template_doc)
        
        # Fall back to default template
        default_template = self._default_templates.get(event)
        if default_template:
            return NotificationTemplate(
                name=f"Default {event}",
                event=event,
                category=NotificationCategory.SYSTEM,
                type=NotificationType.EMAIL,
                **default_template
            )
        
        return None
    
    def _get_notification_types(self, prefs: NotificationPreference, template: NotificationTemplate) -> List[NotificationType]:
        """Determine which notification types to send"""
        types = []
        
        if prefs.email_enabled and template.type in [NotificationType.EMAIL]:
            types.append(NotificationType.EMAIL)
        
        if prefs.sms_enabled and template.type in [NotificationType.SMS]:
            types.append(NotificationType.SMS)
        
        if prefs.in_app_enabled:
            types.append(NotificationType.IN_APP)
        
        return types if types else [NotificationType.EMAIL]  # Default to email
    
    async def _create_notification(
        self,
        user_id: str,
        user: Dict,
        template: NotificationTemplate,
        notification_type: NotificationType,
        context_data: Dict[str, Any],
        priority: int,
        scheduled_for: Optional[datetime]
    ) -> Optional[str]:
        """Create a notification record"""
        try:
            # Render template with context data
            rendered_content = self._render_template(template, context_data, user)
            
            notification = Notification(
                user_id=user_id,
                template_id=getattr(template, 'id', None),
                event=template.event,
                category=template.category,
                type=notification_type,
                subject=rendered_content["subject"],
                body=rendered_content["body"],
                html_body=rendered_content.get("html_body"),
                recipient_email=user.get("email") if notification_type == NotificationType.EMAIL else None,
                recipient_phone=user.get("phone_number") if notification_type == NotificationType.SMS else None,
                priority=priority,
                scheduled_for=scheduled_for,
                context_data=context_data,
                tracking_id=str(uuid.uuid4())
            )
            
            result = await notifications_collection.insert_one(notification.model_dump())
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            return None
    
    def _render_template(self, template: NotificationTemplate, context_data: Dict[str, Any], user: Dict) -> Dict[str, str]:
        """Render template with context data"""
        # Add user data to context
        full_context = {
            **context_data,
            "user_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "user_email": user.get("email", ""),
            "user_first_name": user.get("first_name", ""),
            "user_last_name": user.get("last_name", ""),
        }
        
        # Simple template rendering (replace {{variable}} with values)
        subject = template.subject
        body = template.body
        html_body = template.html_body
        
        for key, value in full_context.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
            if html_body:
                html_body = html_body.replace(placeholder, str(value))
        
        return {
            "subject": subject,
            "body": body,
            "html_body": html_body
        }
    
    async def _queue_notification(self, notification_id: str, priority: int, scheduled_for: Optional[datetime]):
        """Queue notification for processing"""
        if not scheduled_for:
            scheduled_for = datetime.utcnow()
        
        queue_item = {
            "notification_id": notification_id,
            "priority": priority,
            "scheduled_for": scheduled_for,
            "status": "queued",
            "created_at": datetime.utcnow()
        }
        
        await notification_queue_collection.insert_one(queue_item)
    
    async def process_notification_queue(self):
        """Process queued notifications"""
        try:
            # Get notifications ready to be sent
            current_time = datetime.utcnow()
            queue_items = await notification_queue_collection.find({
                "status": "queued",
                "scheduled_for": {"$lte": current_time}
            }).sort("priority", -1).limit(10).to_list(None)
            
            for item in queue_items:
                await self._process_single_notification(item)
                
        except Exception as e:
            logger.error(f"Error processing notification queue: {str(e)}")
    
    async def _process_single_notification(self, queue_item: Dict):
        """Process a single notification"""
        try:
            # Mark as processing
            await notification_queue_collection.update_one(
                {"_id": queue_item["_id"]},
                {"$set": {"status": "processing"}}
            )
            
            # Get notification
            notification = await notifications_collection.find_one({"_id": queue_item["notification_id"]})
            if not notification:
                logger.error(f"Notification {queue_item['notification_id']} not found")
                return
            
            # Send based on type
            success = False
            if notification["type"] == NotificationType.EMAIL:
                success = await self._send_email(notification)
            elif notification["type"] == NotificationType.SMS:
                success = await self._send_sms(notification)
            elif notification["type"] == NotificationType.IN_APP:
                success = await self._send_in_app(notification)
            
            # Update status
            if success:
                await notifications_collection.update_one(
                    {"_id": notification["_id"]},
                    {
                        "$set": {
                            "status": NotificationStatus.SENT,
                            "sent_at": datetime.utcnow()
                        }
                    }
                )
                await notification_queue_collection.update_one(
                    {"_id": queue_item["_id"]},
                    {"$set": {"status": "completed", "processed_at": datetime.utcnow()}}
                )
            else:
                # Handle retry logic
                await self._handle_failed_notification(notification, queue_item)
                
        except Exception as e:
            logger.error(f"Error processing notification {queue_item.get('notification_id')}: {str(e)}")
            await self._handle_failed_notification(notification, queue_item, str(e))
    
    async def _send_email(self, notification: Dict) -> bool:
        """Send email notification"""
        if not self.email_config:
            logger.error("Email configuration not set")
            return False
        
        try:
            # Create message
            msg = MimeMultipart('alternative')
            msg['Subject'] = notification['subject']
            msg['From'] = f"{self.email_config.from_name} <{self.email_config.from_email}>"
            msg['To'] = notification['recipient_email']
            
            if self.email_config.reply_to:
                msg['Reply-To'] = self.email_config.reply_to
            
            # Add text and HTML parts
            text_part = MimeText(notification['body'], 'plain', 'utf-8')
            msg.attach(text_part)
            
            if notification.get('html_body'):
                html_part = MimeText(notification['html_body'], 'html', 'utf-8')
                msg.attach(html_part)
            
            # Send email
            if self.email_config.provider == "smtp":
                context = ssl.create_default_context()
                with smtplib.SMTP(self.email_config.smtp_host, self.email_config.smtp_port) as server:
                    server.starttls(context=context)
                    server.login(self.email_config.smtp_username, self.email_config.smtp_password)
                    server.send_message(msg)
            
            logger.info(f"Email sent successfully to {notification['recipient_email']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    async def _send_sms(self, notification: Dict) -> bool:
        """Send SMS notification"""
        if not self.sms_config:
            logger.error("SMS configuration not set")
            return False
        
        try:
            # For now, just log SMS (implement actual SMS provider integration)
            logger.info(f"SMS would be sent to {notification['recipient_phone']}: {notification['body']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return False
    
    async def _send_in_app(self, notification: Dict) -> bool:
        """Send in-app notification"""
        try:
            # In-app notifications are just stored in database and marked as sent
            logger.info(f"In-app notification created for user {notification['user_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending in-app notification: {str(e)}")
            return False
    
    async def _handle_failed_notification(self, notification: Dict, queue_item: Dict, error_message: str = ""):
        """Handle failed notification with retry logic"""
        retry_count = queue_item.get("retry_count", 0) + 1
        max_retries = notification.get("max_retries", 3)
        
        if retry_count <= max_retries:
            # Schedule for retry
            retry_delay = timedelta(minutes=5 * retry_count)  # Exponential backoff
            await notification_queue_collection.update_one(
                {"_id": queue_item["_id"]},
                {
                    "$set": {
                        "status": "queued",
                        "retry_count": retry_count,
                        "scheduled_for": datetime.utcnow() + retry_delay
                    }
                }
            )
        else:
            # Mark as failed
            await notifications_collection.update_one(
                {"_id": notification["_id"]},
                {
                    "$set": {
                        "status": NotificationStatus.FAILED,
                        "error_message": error_message,
                        "retry_count": retry_count
                    }
                }
            )
            await notification_queue_collection.update_one(
                {"_id": queue_item["_id"]},
                {"$set": {"status": "failed", "processed_at": datetime.utcnow()}}
            )

# Global notification service instance
notification_service = NotificationService() 
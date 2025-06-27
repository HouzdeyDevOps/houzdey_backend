#!/usr/bin/env python3
"""
Setup script for Analytics and Notifications system.
This script creates necessary collections and indexes for the analytics and notifications features.
"""

import asyncio
import logging
from datetime import datetime, timezone
from app.core.database import (
    property_views_collection,
    property_inquiries_collection,
    analytics_cache_collection,
    notifications_collection,
    notification_preferences_collection,
    notification_templates_collection,
    notification_queue_collection,
    notification_batches_collection
)
from app.models.notifications import NotificationTemplate, NotificationEvent, NotificationType, NotificationCategory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_indexes():
    """Create indexes for analytics and notification collections"""
    
    # Analytics indexes
    logger.info("Creating analytics indexes...")
    
    # Property views collection
    await property_views_collection.create_index([("property_id", 1), ("viewed_at", -1)])
    await property_views_collection.create_index([("user_id", 1), ("viewed_at", -1)])
    await property_views_collection.create_index([("ip_address", 1), ("viewed_at", -1)])
    await property_views_collection.create_index([("session_id", 1)])
    
    # Property inquiries collection
    await property_inquiries_collection.create_index([("property_id", 1), ("created_at", -1)])
    await property_inquiries_collection.create_index([("user_id", 1), ("created_at", -1)])
    await property_inquiries_collection.create_index([("inquiry_type", 1)])
    
    # Analytics cache collection
    await analytics_cache_collection.create_index([("cache_key", 1)])
    await analytics_cache_collection.create_index([("expires_at", 1)])
    
    # Notification indexes
    logger.info("Creating notification indexes...")
    
    # Notifications collection
    await notifications_collection.create_index([("user_id", 1), ("created_at", -1)])
    await notifications_collection.create_index([("status", 1), ("created_at", -1)])
    await notifications_collection.create_index([("event", 1)])
    await notifications_collection.create_index([("scheduled_for", 1)])
    await notifications_collection.create_index([("opened_at", 1)])
    
    # Notification preferences collection
    await notification_preferences_collection.create_index([("user_id", 1)], unique=True)
    
    # Notification templates collection
    await notification_templates_collection.create_index([("event", 1), ("type", 1)])
    await notification_templates_collection.create_index([("is_active", 1)])
    
    # Notification queue collection
    await notification_queue_collection.create_index([("status", 1), ("scheduled_for", 1)])
    await notification_queue_collection.create_index([("priority", -1), ("created_at", 1)])
    
    # Notification batches collection
    await notification_batches_collection.create_index([("status", 1), ("created_at", -1)])
    
    logger.info("All indexes created successfully!")

async def create_default_notification_templates():
    """Create default notification templates"""
    
    logger.info("Creating default notification templates...")
    
    # Use notification_templates_collection directly
    
    default_templates = [
        {
            "name": "Welcome Email",
            "event": NotificationEvent.USER_REGISTERED,
            "category": NotificationCategory.USER,
            "type": NotificationType.EMAIL,
            "subject": "Welcome to Houzdey! 🏠",
            "body": "Welcome to Houzdey, {first_name}! We're excited to help you find your dream home.",
            "html_body": "<h1>Welcome to Houzdey! 🏠</h1><p>Welcome to Houzdey, {first_name}! We're excited to help you find your dream home.</p>",
            "variables": ["first_name", "last_name", "email"],
            "is_active": True,
            "priority": 1,
            "send_immediately": True,
            "delay_minutes": 0,
            "personalized": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Property Inquiry Notification",
            "event": NotificationEvent.PROPERTY_INQUIRY,
            "category": NotificationCategory.PROPERTY,
            "type": NotificationType.EMAIL,
            "subject": "New Inquiry for '{property_title}' from {inquirer_name}",
            "body": "You have received a new inquiry for your property '{property_title}' from {inquirer_name}. Contact: {inquirer_email}, Phone: {inquirer_phone}. Message: {inquiry_message}",
            "html_body": """
            <h2>New Property Inquiry</h2>
            <p>Hello,</p>
            <p>You have received a new inquiry for your property:</p>
            <p><strong>Property:</strong> {property_title}</p>
            <p><strong>From:</strong> {inquirer_name}</p>
            <p><strong>Email:</strong> {inquirer_email}</p>
            <p><strong>Phone:</strong> {inquirer_phone}</p>
            <p><strong>Preferred Contact Method:</strong> {preferred_contact_method}</p>
            <p><strong>Inquiry Type:</strong> {inquiry_type}</p>
            
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Message:</strong></p>
                <p>{inquiry_message}</p>
            </div>
            
            <p>
                <a href="{property_url}" style="display: inline-block; padding: 10px 20px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 5px; margin-right: 10px;">
                    View Property
                </a>
                <a href="mailto:{inquirer_email}" style="display: inline-block; padding: 10px 20px; background-color: #059669; color: white; text-decoration: none; border-radius: 5px;">
                    Reply via Email
                </a>
            </p>
            
            <p>Best regards,<br>The Houzdey Team</p>
            """,
            "variables": ["property_title", "inquirer_name", "inquiry_message", "property_id", "inquirer_email", "inquirer_phone", "preferred_contact_method", "inquiry_type", "property_url"],
            "is_active": True,
            "priority": 2,
            "send_immediately": True,
            "delay_minutes": 0,
            "personalized": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "New Message Notification",
            "event": NotificationEvent.NEW_MESSAGE,
            "category": NotificationCategory.CHAT,
            "type": NotificationType.EMAIL,
            "subject": "New message from {sender_name} about {property_title}",
            "body": "You have a new message from {sender_name} regarding your property '{property_title}': {message_preview}",
            "html_body": """
            <h2>New Message Received</h2>
            <p>Hello,</p>
            <p>You have received a new message from <strong>{sender_name}</strong> regarding your property:</p>
            <p><strong>Property:</strong> {property_title}</p>
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>{sender_name}:</strong> {message_preview}</p>
            </div>
            <p>
                <a href="{chat_url}" style="display: inline-block; padding: 10px 20px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 5px;">
                    Reply to Message
                </a>
            </p>
            <p>Best regards,<br>The Houzdey Team</p>
            """,
            "variables": ["sender_name", "message_preview", "conversation_id", "property_title", "chat_url", "property_id", "sender_id"],
            "is_active": True,
            "priority": 2,
            "send_immediately": True,
            "delay_minutes": 0,
            "personalized": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Property Approved",
            "event": NotificationEvent.PROPERTY_APPROVED,
            "category": NotificationCategory.PROPERTY,
            "type": NotificationType.EMAIL,
            "subject": "🎉 Your Property Has Been Approved!",
            "body": "Great news! Your property '{property_title}' has been approved and is now live on Houzdey.",
            "html_body": "<h2>🎉 Your Property Has Been Approved!</h2><p>Great news! Your property '<strong>{property_title}</strong>' has been approved and is now live on Houzdey.</p><p>You can view your property <a href='{property_url}'>here</a>.</p>",
            "variables": ["property_title", "property_url", "property_id"],
            "is_active": True,
            "priority": 2,
            "send_immediately": True,
            "delay_minutes": 0,
            "personalized": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Password Reset",
            "event": NotificationEvent.PASSWORD_RESET,
            "category": NotificationCategory.SECURITY,
            "type": NotificationType.EMAIL,
            "subject": "Reset Your Houzdey Password",
            "body": "Click the link below to reset your password: {reset_link}",
            "html_body": "<h2>Reset Your Password</h2><p>Click the button below to reset your password:</p><p><a href='{reset_link}' style='background-color: #3B82F6; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;'>Reset Password</a></p>",
            "variables": ["reset_link", "expires_at"],
            "is_active": True,
            "priority": 1,
            "send_immediately": True,
            "delay_minutes": 0,
            "personalized": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    for template_data in default_templates:
        # Check if template already exists
        existing = await notification_templates_collection.find_one({
            "event": template_data["event"],
            "type": template_data["type"]
        })
        
        if not existing:
            await notification_templates_collection.insert_one(template_data)
            logger.info(f"Created template: {template_data['name']}")
        else:
            logger.info(f"Template already exists: {template_data['name']}")
    
    logger.info("Default notification templates created successfully!")

async def main():
    """Main setup function"""
    try:
        logger.info("Setting up Analytics and Notifications system...")
        
        # Create indexes
        await create_indexes()
        
        # Create default notification templates
        await create_default_notification_templates()
        
        logger.info("✅ Analytics and Notifications setup completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
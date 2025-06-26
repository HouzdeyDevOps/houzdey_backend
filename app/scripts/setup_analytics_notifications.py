#!/usr/bin/env python3
"""
Setup script for Analytics and Notifications system.
This script creates necessary collections and indexes for the analytics and notifications features.
"""

import asyncio
import logging
from datetime import datetime
from app.core.database import database
from app.models.notifications import NotificationTemplate, NotificationEvent, NotificationType, NotificationCategory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_indexes():
    """Create indexes for analytics and notification collections"""
    
    # Analytics indexes
    logger.info("Creating analytics indexes...")
    
    # Property views collection
    views_collection = database.property_views
    await views_collection.create_index([("property_id", 1), ("viewed_at", -1)])
    await views_collection.create_index([("user_id", 1), ("viewed_at", -1)])
    await views_collection.create_index([("ip_address", 1), ("viewed_at", -1)])
    await views_collection.create_index([("session_id", 1)])
    
    # Property inquiries collection
    inquiries_collection = database.property_inquiries
    await inquiries_collection.create_index([("property_id", 1), ("created_at", -1)])
    await inquiries_collection.create_index([("user_id", 1), ("created_at", -1)])
    await inquiries_collection.create_index([("inquiry_type", 1)])
    
    # Analytics cache collection
    cache_collection = database.analytics_cache
    await cache_collection.create_index([("cache_key", 1)])
    await cache_collection.create_index([("expires_at", 1)])
    
    # Notification indexes
    logger.info("Creating notification indexes...")
    
    # Notifications collection
    notifications_collection = database.notifications
    await notifications_collection.create_index([("user_id", 1), ("created_at", -1)])
    await notifications_collection.create_index([("status", 1), ("created_at", -1)])
    await notifications_collection.create_index([("event", 1)])
    await notifications_collection.create_index([("scheduled_for", 1)])
    await notifications_collection.create_index([("opened_at", 1)])
    
    # Notification preferences collection
    prefs_collection = database.notification_preferences
    await prefs_collection.create_index([("user_id", 1)], unique=True)
    
    # Notification templates collection
    templates_collection = database.notification_templates
    await templates_collection.create_index([("event", 1), ("type", 1)])
    await templates_collection.create_index([("is_active", 1)])
    
    # Notification queue collection
    queue_collection = database.notification_queue
    await queue_collection.create_index([("status", 1), ("scheduled_for", 1)])
    await queue_collection.create_index([("priority", -1), ("created_at", 1)])
    
    # Notification batches collection
    batches_collection = database.notification_batches
    await batches_collection.create_index([("status", 1), ("created_at", -1)])
    
    logger.info("All indexes created successfully!")

async def create_default_notification_templates():
    """Create default notification templates"""
    
    logger.info("Creating default notification templates...")
    
    templates_collection = database.notification_templates
    
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
            "subject": "New Inquiry for Your Property",
            "body": "You have received a new inquiry for your property '{property_title}' from {inquirer_name}.",
            "html_body": "<h2>New Property Inquiry</h2><p>You have received a new inquiry for your property '<strong>{property_title}</strong>' from {inquirer_name}.</p><p><strong>Message:</strong> {inquiry_message}</p>",
            "variables": ["property_title", "inquirer_name", "inquiry_message", "property_id"],
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
            "type": NotificationType.PUSH,
            "subject": "New Message",
            "body": "You have a new message from {sender_name}",
            "variables": ["sender_name", "message_preview", "conversation_id"],
            "is_active": True,
            "priority": 1,
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
        existing = await templates_collection.find_one({
            "event": template_data["event"],
            "type": template_data["type"]
        })
        
        if not existing:
            await templates_collection.insert_one(template_data)
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
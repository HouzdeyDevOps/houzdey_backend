from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId
from bson.errors import InvalidId
import logging

from app.core.database import (
    notifications_collection,
    notification_preferences_collection,
    notification_templates_collection,
    notification_queue_collection,
    user_collection
)
from app.api.deps import get_current_user, get_current_admin_user
from app.models.user import User
from app.models.notifications import (
    Notification,
    NotificationTemplate,
    NotificationPreference,
    NotificationEvent,
    NotificationType,
    NotificationStatus,
    NotificationCategory,
    NotificationBatch
)
from app.services.notification_service import NotificationService
from app.core.dependencies import get_notification_service

logger = logging.getLogger(__name__)
router = APIRouter()

# USER NOTIFICATION ROUTES

@router.get("/preferences")
async def get_notification_preferences(current_user: dict = Depends(get_current_user)):
    """Get user's notification preferences"""
    try:
        prefs = await notification_preferences_collection.find_one({"user_id": str(current_user["id"])})
        
        if not prefs:
            # Create default preferences
            default_prefs = NotificationPreference(user_id=str(current_user["id"]))
            await notification_preferences_collection.insert_one(default_prefs.model_dump())
            return default_prefs
        
        prefs["id"] = str(prefs["_id"])
        del prefs["_id"]
        return NotificationPreference(**prefs)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get notification preferences: {str(e)}")

@router.put("/preferences")
async def update_notification_preferences(
    preferences: NotificationPreference,
    current_user: dict = Depends(get_current_user)
):
    """Update user's notification preferences"""
    try:
        preferences.user_id = str(current_user["id"])
        preferences.updated_at = datetime.utcnow()
        
        # Update or insert preferences
        await notification_preferences_collection.update_one(
            {"user_id": str(current_user["id"])},
            {"$set": preferences.model_dump()},
            upsert=True
        )
        
        return {"message": "Notification preferences updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update notification preferences: {str(e)}")

@router.get("/my-notifications")
async def get_user_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get user's notifications"""
    try:
        skip = (page - 1) * limit
        
        # Get notifications
        notifications = []
        async for notif in notifications_collection.find({"user_id": str(current_user["id"])}).skip(skip).limit(limit).sort("created_at", -1):
            notif["id"] = str(notif["_id"])
            del notif["_id"]
            notifications.append(notif)
        
        # Get total count
        total_count = await notifications_collection.count_documents({"user_id": str(current_user["id"])})
        
        return {
            "notifications": notifications,
            "pagination": {
                "current_page": page,
                "total_count": total_count,
                "has_next": skip + limit < total_count,
                "has_prev": page > 1
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get notifications: {str(e)}")

@router.post("/mark-read/{notification_id}")
async def mark_notification_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a notification as read"""
    try:
        # Verify notification belongs to user
        notification = await notifications_collection.find_one({
            "_id": ObjectId(notification_id),
            "user_id": str(current_user["id"])
        })
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        # Update notification
        await notifications_collection.update_one(
            {"_id": ObjectId(notification_id)},
            {
                "$set": {
                    "opened_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {"message": "Notification marked as read"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")

@router.post("/mark-all-read")
async def mark_all_notifications_as_read(current_user: dict = Depends(get_current_user)):
    """Mark all user notifications as read"""
    try:
        result = await notifications_collection.update_many(
            {
                "user_id": str(current_user["id"]),
                "opened_at": {"$exists": False}
            },
            {
                "$set": {
                    "opened_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {"message": f"Marked {result.modified_count} notifications as read"}
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark notifications as read")

@router.get("/unread-count")
async def get_unread_notification_count(current_user: dict = Depends(get_current_user)):
    """Get count of unread notifications"""
    try:
        count = await notifications_collection.count_documents({
            "user_id": str(current_user["id"]),
            "opened_at": {"$exists": False}
        })
        
        return {"unread_count": count}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get unread count: {str(e)}")

# ADMIN NOTIFICATION ROUTES

@router.get("/templates", dependencies=[Depends(get_current_admin_user)])
async def get_notification_templates(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    event: Optional[str] = None,
    type: Optional[str] = None
):
    """Get notification templates (admin only)"""
    try:
        # Build filter query
        filter_query = {}
        if event:
            filter_query["event"] = event
        if type:
            filter_query["type"] = type
        
        # Calculate pagination
        skip = (page - 1) * limit
        
        # Get templates
        templates = []
        async for template in notification_templates_collection.find(filter_query).skip(skip).limit(limit).sort("created_at", -1):
            template["id"] = str(template["_id"])
            del template["_id"]
            templates.append(template)
        
        return templates
        
    except Exception as e:
        logger.error(f"Error getting notification templates: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get notification templates")

@router.post("/templates", dependencies=[Depends(get_current_admin_user)])
async def create_notification_template(template: NotificationTemplate):
    """Create a new notification template (admin only)"""
    try:
        template.created_at = datetime.utcnow()
        template.updated_at = datetime.utcnow()
        
        result = await notification_templates_collection.insert_one(template.model_dump())
        
        return {"message": "Template created successfully", "template_id": str(result.inserted_id)}
        
    except Exception as e:
        logger.error(f"Error creating notification template: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create notification template")

@router.put("/templates/{template_id}", dependencies=[Depends(get_current_admin_user)])
async def update_notification_template(
    template_id: str,
    template_update: NotificationTemplate
):
    """Update a notification template (admin only)"""
    try:
        template_update.updated_at = datetime.utcnow()
        
        result = await notification_templates_collection.update_one(
            {"_id": ObjectId(template_id)},
            {"$set": template_update.model_dump()}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {"message": "Template updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating notification template: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update notification template")

@router.delete("/templates/{template_id}", dependencies=[Depends(get_current_admin_user)])
async def delete_notification_template(template_id: str):
    """Delete a notification template (admin only)"""
    try:
        result = await notification_templates_collection.delete_one({"_id": ObjectId(template_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {"message": "Template deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification template: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete notification template")

@router.post("/send", dependencies=[Depends(get_current_admin_user)])
async def send_notification_to_user(
    user_id: str = Body(...),
    event: NotificationEvent = Body(...),
    context_data: Dict[str, Any] = Body(default={}),
    priority: int = Body(default=1),
    scheduled_for: Optional[datetime] = Body(default=None),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Send a notification to a specific user (admin only)"""
    try:
        notification_id = await notification_service.send_notification(
            user_id=user_id,
            event=event,
            context_data=context_data,
            priority=priority,
            scheduled_for=scheduled_for
        )
        
        if notification_id:
            return {"message": "Notification sent successfully", "notification_id": notification_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to send notification")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send notification")

@router.post("/broadcast", dependencies=[Depends(get_current_admin_user)])
async def broadcast_notification(
    event: NotificationEvent = Body(...),
    context_data: Dict[str, Any] = Body(default={}),
    user_filters: Dict[str, Any] = Body(default={}),
    priority: int = Body(default=1),
    scheduled_for: Optional[datetime] = Body(default=None),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Send a notification to multiple users (admin only)"""
    try:
        # Get users based on filters
        filter_query = user_filters if user_filters else {}
        
        user_ids = []
        async for user in user_collection.find(filter_query):
            user_ids.append(str(user["_id"]))
        
        if not user_ids:
            raise HTTPException(status_code=400, detail="No users found matching the criteria")
        
        # Send notifications to all users
        sent_count = 0
        for user_id in user_ids:
            notification_id = await notification_service.send_notification(
                user_id=user_id,
                event=event,
                context_data=context_data,
                priority=priority,
                scheduled_for=scheduled_for
            )
            if notification_id:
                sent_count += 1
        
        return {
            "message": f"Broadcast notification sent",
            "total_recipients": len(user_ids),
            "sent_count": sent_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error broadcasting notification: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to broadcast notification")

@router.get("/analytics", dependencies=[Depends(get_current_admin_user)])
async def get_notification_analytics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    event: Optional[str] = None,
    type: Optional[str] = None
):
    """Get notification analytics (admin only)"""
    try:
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Build filter query
        filter_query = {
            "created_at": {"$gte": start_date, "$lte": end_date}
        }
        
        if event:
            filter_query["event"] = event
        if type:
            filter_query["type"] = type
        
        # Get notification statistics
        total_sent = await notifications_collection.count_documents(filter_query)
        
        delivered_filter = {**filter_query, "status": NotificationStatus.DELIVERED}
        total_delivered = await notifications_collection.count_documents(delivered_filter)
        
        failed_filter = {**filter_query, "status": NotificationStatus.FAILED}
        total_failed = await notifications_collection.count_documents(failed_filter)
        
        opened_filter = {**filter_query, "opened_at": {"$exists": True}}
        total_opened = await notifications_collection.count_documents(opened_filter)
        
        # Calculate rates
        delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
        open_rate = (total_opened / total_delivered * 100) if total_delivered > 0 else 0
        
        # Get daily stats
        daily_stats = []
        current_date = start_date
        while current_date <= end_date:
            day_start = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            day_sent = await notifications_collection.count_documents({
                **filter_query,
                "created_at": {"$gte": day_start, "$lt": day_end}
            })
            
            daily_stats.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "sent": day_sent
            })
            
            current_date += timedelta(days=1)
        
        return {
            "period": {
                "start": start_date,
                "end": end_date
            },
            "summary": {
                "total_sent": total_sent,
                "total_delivered": total_delivered,
                "total_failed": total_failed,
                "total_opened": total_opened,
                "delivery_rate": round(delivery_rate, 2),
                "open_rate": round(open_rate, 2)
            },
            "daily_stats": daily_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting notification analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get notification analytics") 
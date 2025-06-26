from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId
from bson.errors import InvalidId
import logging

from app.core.database import (
    user_collection, 
    property_collection, 
    conversation_collection,
    message_collection,
    admin_actions_collection,
    system_settings_collection,
    reports_collection,
    notification_templates_collection
)
from app.api.deps import get_current_admin_user, get_current_super_admin_user
from app.models.user import User, UserRole, UserStatus
from app.models.admin import (
    AdminStats, 
    UserManagementStats, 
    PropertyManagementStats,
    SystemSettings,
    AdminAction,
    UserUpdateRequest,
    BulkUserAction,
    ContentModerationAction,
    ReportResponse,
    NotificationTemplate
)
from app.utils.email import send_verification_code

logger = logging.getLogger(__name__)
router = APIRouter()

# Helper function to log admin actions
async def log_admin_action(admin_id: str, action_type: str, target_type: str, 
                          target_id: str = None, description: str = "", 
                          metadata: Dict[str, Any] = None):
    """Log admin actions for audit trail"""
    try:
        action_log = AdminAction(
            admin_id=admin_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            description=description,
            metadata=metadata or {}
        )
        await admin_actions_collection.insert_one(action_log.model_dump())
    except Exception as e:
        logger.error(f"Failed to log admin action: {str(e)}")

# Basic health check for admin panel
@router.get("/health")
async def admin_health_check(current_admin: User = Depends(get_current_admin_user)):
    """Admin panel health check"""
    return {"status": "ok", "admin": f"{current_admin.first_name} {current_admin.last_name}"}

# DASHBOARD ROUTES
@router.get("/dashboard/stats", response_model=AdminStats)
async def get_dashboard_stats(current_admin: User = Depends(get_current_admin_user)):
    """Get admin dashboard statistics"""
    try:
        # Get basic counts
        total_users = await user_collection.count_documents({})
        total_properties = await property_collection.count_documents({})
        total_conversations = await conversation_collection.count_documents({})
        
        # Get active users (logged in last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_users = await user_collection.count_documents({
            "updated_at": {"$gte": thirty_days_ago}
        })
        
        # Get pending verifications
        pending_verifications = await user_collection.count_documents({
            "status": UserStatus.PENDING
        })
        
        # Calculate total revenue (mock data for now)
        total_revenue = 0.0  # This would come from payment records
        
        # Properties by type
        property_types_pipeline = [
            {"$group": {"_id": {"$ifNull": ["$type", "unknown"]}, "count": {"$sum": 1}}}
        ]
        properties_by_type = {}
        async for doc in property_collection.aggregate(property_types_pipeline):
            type_key = doc["_id"] if doc["_id"] is not None else "unknown"
            properties_by_type[str(type_key)] = doc["count"]
        
        # Users by status
        users_by_status_pipeline = [
            {"$group": {"_id": {"$ifNull": ["$status", "unknown"]}, "count": {"$sum": 1}}}
        ]
        users_by_status = {}
        async for doc in user_collection.aggregate(users_by_status_pipeline):
            status_key = doc["_id"] if doc["_id"] is not None else "unknown"
            users_by_status[str(status_key)] = doc["count"]
        
        # Monthly signups (last 12 months)
        monthly_signups = []
        for i in range(12):
            start_date = datetime.utcnow().replace(day=1) - timedelta(days=30*i)
            end_date = start_date + timedelta(days=30)
            count = await user_collection.count_documents({
                "created_at": {"$gte": start_date, "$lt": end_date}
            })
            monthly_signups.insert(0, {
                "month": start_date.strftime("%B %Y"),
                "count": count
            })
        
        # Recent activities (admin actions)
        recent_activities = []
        async for action in admin_actions_collection.find({}).sort("created_at", -1).limit(10):
            admin_user = await user_collection.find_one({"_id": ObjectId(action["admin_id"])})
            recent_activities.append({
                "admin_name": f"{admin_user.get('first_name', '')} {admin_user.get('last_name', '')}".strip() if admin_user else "Unknown",
                "action": action["description"],
                "time": action["created_at"]
            })
        
        return AdminStats(
            total_users=total_users,
            total_properties=total_properties,
            total_conversations=total_conversations,
            active_users=active_users,
            pending_verifications=pending_verifications,
            total_revenue=total_revenue,
            properties_by_type=properties_by_type,
            users_by_status=users_by_status,
            monthly_signups=monthly_signups,
            recent_activities=recent_activities
        )
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard statistics")

# USER MANAGEMENT ROUTES
@router.get("/users", response_model=List[Dict[str, Any]])
async def get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    role: Optional[str] = None,
    current_admin: User = Depends(get_current_admin_user)
):
    """Get paginated list of users with filters"""
    try:
        # Build filter query
        filter_query = {}
        if search:
            filter_query["$or"] = [
                {"first_name": {"$regex": search, "$options": "i"}},
                {"last_name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}}
            ]
        if status:
            filter_query["status"] = status
        if role:
            filter_query["role"] = role
        
        # Calculate pagination
        skip = (page - 1) * limit
        
        # Get users
        users = []
        async for user in user_collection.find(filter_query).skip(skip).limit(limit).sort("created_at", -1):
            user["id"] = str(user["_id"])
            del user["_id"]
            del user["password"]  # Don't return password
            users.append(user)
        
        await log_admin_action(
            str(current_admin.id), "VIEW", "users", 
            description="Viewed users list"
        )
        
        return users
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get users")

@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user)
):
    """Get detailed user information"""
    try:
        user = await user_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user["id"] = str(user["_id"])
        del user["_id"]
        del user["password"]
        
        # Get user's properties count
        properties_count = await property_collection.count_documents({"owner_id": user_id})
        user["properties_count"] = properties_count
        
        # Get user's conversations count
        conversations_count = await conversation_collection.count_documents({
            "$or": [{"user_id": user_id}, {"owner_id": user_id}]
        })
        user["conversations_count"] = conversations_count
        
        await log_admin_action(
            str(current_admin.id), "VIEW", "user", user_id,
            f"Viewed user details for {user.get('email', 'unknown')}"
        )
        
        return user
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    except Exception as e:
        logger.error(f"Error getting user details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user details")

@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    user_update: UserUpdateRequest,
    current_admin: User = Depends(get_current_admin_user)
):
    """Update user information"""
    try:
        # Check if user exists
        existing_user = await user_collection.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Build update data
        update_data = {k: v for k, v in user_update.model_dump().items() if v is not None}
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            
            # Update user
            result = await user_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                await log_admin_action(
                    str(current_admin.id), "UPDATE", "user", user_id,
                    f"Updated user {existing_user.get('email', 'unknown')}",
                    {"updated_fields": list(update_data.keys())}
                )
                return {"message": "User updated successfully"}
            else:
                return {"message": "No changes made"}
        else:
            return {"message": "No update data provided"}
            
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update user")

@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: str,
    reason: str = Body(..., embed=True),
    current_admin: User = Depends(get_current_admin_user)
):
    """Suspend a user account"""
    try:
        # Check if user exists
        existing_user = await user_collection.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user status
        result = await user_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "status": UserStatus.SUSPENDED,
                "is_active": False,
                "updated_at": datetime.utcnow()
            }}
        )
        
        if result.modified_count > 0:
            await log_admin_action(
                str(current_admin.id), "SUSPEND", "user", user_id,
                f"Suspended user {existing_user.get('email', 'unknown')}: {reason}"
            )
            return {"message": "User suspended successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to suspend user")
            
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    except Exception as e:
        logger.error(f"Error suspending user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to suspend user")

@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user)
):
    """Activate a suspended user account"""
    try:
        # Check if user exists
        existing_user = await user_collection.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user status
        result = await user_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "status": UserStatus.VERIFIED,
                "is_active": True,
                "updated_at": datetime.utcnow()
            }}
        )
        
        if result.modified_count > 0:
            await log_admin_action(
                str(current_admin.id), "ACTIVATE", "user", user_id,
                f"Activated user {existing_user.get('email', 'unknown')}"
            )
            return {"message": "User activated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to activate user")
            
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    except Exception as e:
        logger.error(f"Error activating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to activate user")

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: User = Depends(get_current_super_admin_user)  # Only super admin can delete
):
    """Delete a user account (super admin only)"""
    try:
        # Check if user exists
        existing_user = await user_collection.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete user's properties first
        await property_collection.delete_many({"owner_id": user_id})
        
        # Delete user's conversations and messages
        conversations = await conversation_collection.find({
            "$or": [{"user_id": user_id}, {"owner_id": user_id}]
        }).to_list(None)
        
        for conv in conversations:
            await message_collection.delete_many({"conversation_id": str(conv["_id"])})
        
        await conversation_collection.delete_many({
            "$or": [{"user_id": user_id}, {"owner_id": user_id}]
        })
        
        # Delete user
        result = await user_collection.delete_one({"_id": ObjectId(user_id)})
        
        if result.deleted_count > 0:
            await log_admin_action(
                str(current_admin.id), "DELETE", "user", user_id,
                f"Deleted user {existing_user.get('email', 'unknown')}"
            )
            return {"message": "User deleted successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to delete user")
            
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete user")

# PROPERTY MANAGEMENT ROUTES
@router.get("/properties")
async def get_properties_admin(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    listing_type: Optional[str] = None,
    current_admin: User = Depends(get_current_admin_user)
):
    """Get paginated list of properties for admin"""
    try:
        # Build filter query
        filter_query = {}
        if status:
            filter_query["status"] = status
        if listing_type:
            filter_query["listing_type"] = listing_type
        
        # Calculate pagination
        skip = (page - 1) * limit
        
        # Get properties with owner information
        properties = []
        async for prop in property_collection.find(filter_query).skip(skip).limit(limit).sort("created_at", -1):
            # Get owner information
            owner = await user_collection.find_one({"_id": ObjectId(prop["owner_id"])})
            prop["id"] = str(prop["_id"])
            del prop["_id"]
            
            if owner:
                prop["owner"] = {
                    "id": str(owner["_id"]),
                    "name": f"{owner.get('first_name', '')} {owner.get('last_name', '')}".strip(),
                    "email": owner.get("email", "")
                }
            
            properties.append(prop)
        
        await log_admin_action(
            str(current_admin.id), "VIEW", "properties",
            description="Viewed properties list"
        )
        
        return properties
    except Exception as e:
        logger.error(f"Error getting properties: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get properties")

@router.put("/properties/{property_id}/status")
async def update_property_status_admin(
    property_id: str,
    status: str = Body(..., embed=True),
    current_admin: User = Depends(get_current_admin_user)
):
    """Update property status (admin)"""
    try:
        # Check if property exists
        existing_property = await property_collection.find_one({"_id": ObjectId(property_id)})
        if not existing_property:
            raise HTTPException(status_code=404, detail="Property not found")
        
        # Update property status
        result = await property_collection.update_one(
            {"_id": ObjectId(property_id)},
            {"$set": {
                "status": status,
                "updated_at": datetime.utcnow()
            }}
        )
        
        if result.modified_count > 0:
            await log_admin_action(
                str(current_admin.id), "UPDATE", "property", property_id,
                f"Updated property status to {status}"
            )
            return {"message": "Property status updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update property status")
            
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid property ID")
    except Exception as e:
        logger.error(f"Error updating property status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update property status")

@router.delete("/properties/{property_id}")
async def delete_property_admin(
    property_id: str,
    current_admin: User = Depends(get_current_admin_user)
):
    """Delete a property (admin)"""
    try:
        # Check if property exists
        existing_property = await property_collection.find_one({"_id": ObjectId(property_id)})
        if not existing_property:
            raise HTTPException(status_code=404, detail="Property not found")
        
        # Delete associated images from cloud storage
        if "images" in existing_property:
            for image_url in existing_property["images"]:
                try:
                    from app.utils.cloudinary_config import extract_public_id_from_url, delete_image_from_cloudinary
                    public_id = extract_public_id_from_url(image_url)
                    success = await delete_image_from_cloudinary(public_id)
                    if not success:
                        print(f"Warning: Failed to delete image {image_url}")
                except Exception as e:
                    print(f"Failed to delete image {image_url}: {str(e)}")
                    # Continue deletion even if image cleanup fails
        
        # Delete property
        result = await property_collection.delete_one({"_id": ObjectId(property_id)})
        
        if result.deleted_count > 0:
            await log_admin_action(
                str(current_admin.id), "DELETE", "property", property_id,
                f"Deleted property {existing_property.get('title', 'unknown')}"
            )
            return {"message": "Property deleted successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to delete property")
            
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid property ID")
    except Exception as e:
        logger.error(f"Error deleting property: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete property")

# SYSTEM SETTINGS ROUTES
@router.get("/settings", response_model=SystemSettings)
async def get_system_settings(current_admin: User = Depends(get_current_admin_user)):
    """Get system settings"""
    try:
        settings = await system_settings_collection.find_one({})
        if settings:
            settings["id"] = str(settings["_id"])
            del settings["_id"]
            return SystemSettings(**settings)
        else:
            # Return default settings if none exist
            return SystemSettings()
    except Exception as e:
        logger.error(f"Error getting system settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get system settings")

@router.put("/settings")
async def update_system_settings(
    settings: SystemSettings,
    current_admin: User = Depends(get_current_super_admin_user)  # Only super admin
):
    """Update system settings"""
    try:
        settings_data = settings.model_dump()
        settings_data["updated_at"] = datetime.utcnow()
        
        # Upsert settings
        result = await system_settings_collection.replace_one(
            {},  # Find any document
            settings_data,
            upsert=True
        )
        
        await log_admin_action(
            str(current_admin.id), "UPDATE", "system_settings",
            description="Updated system settings"
        )
        
        return {"message": "System settings updated successfully"}
    except Exception as e:
        logger.error(f"Error updating system settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update system settings")

# ADMIN ACTIONS LOG
@router.get("/actions")
async def get_admin_actions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin_id: Optional[str] = None,
    action_type: Optional[str] = None,
    current_admin: User = Depends(get_current_admin_user)
):
    """Get admin actions log"""
    try:
        # Build filter query
        filter_query = {}
        if admin_id:
            filter_query["admin_id"] = admin_id
        if action_type:
            filter_query["action_type"] = action_type
        
        # Calculate pagination
        skip = (page - 1) * limit
        
        # Get actions with admin information
        actions = []
        async for action in admin_actions_collection.find(filter_query).skip(skip).limit(limit).sort("created_at", -1):
            # Get admin information
            admin_user = await user_collection.find_one({"_id": ObjectId(action["admin_id"])})
            action["id"] = str(action["_id"])
            del action["_id"]
            
            if admin_user:
                action["admin_name"] = f"{admin_user.get('first_name', '')} {admin_user.get('last_name', '')}".strip()
                action["admin_email"] = admin_user.get("email", "")
            
            actions.append(action)
        
        return actions
    except Exception as e:
        logger.error(f"Error getting admin actions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get admin actions") 
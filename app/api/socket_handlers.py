import logging
from datetime import datetime, timedelta
from typing import Dict, Set
from bson import ObjectId
from bson.errors import InvalidId
from jose import JWTError, jwt

from app.core.database import (
    user_collection,
    conversation_collection,
    message_collection,
    property_collection
)
from app.core.config import settings
from app.services.user_service import UserService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

# Track active connections and user status
active_connections: Dict[str, str] = {}  # sid -> user_id
user_sockets: Dict[str, Set[str]] = {}   # user_id -> set of sids
user_statuses: Dict[str, Dict] = {}      # user_id -> {status, last_seen}
active_conversations: Dict[str, datetime] = {}  # conversation_id -> last_activity
user_connection_times: Dict[str, datetime] = {}  # user_id -> datetime

async def authenticate_socket(token: str):
    """Authenticate socket connection using JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_email = payload.get("sub")  # Get email from token

        if user_email is None:
            raise JWTError
        
        # Get user by email to get the user ID
        user_service = UserService()
        user = await user_service.get_user_by_email(user_email)
        if not user:
            raise JWTError
            
        return user["id"]  # Return user ID instead of email
    except JWTError:
        logger.error(f"Socket authentication failed for token")
        return None

async def broadcast_user_status(socket_manager, user_id: str, status: str, last_seen: datetime):
    """Broadcast user status to all connected clients who need to know"""
    status_data = {
        "user_id": user_id,
        "status": status,
        "last_seen": last_seen.isoformat() if last_seen else None
    }
    
    # Broadcast to all connected sockets (they'll filter based on their needs)
    await socket_manager.emit('user_status_update', status_data)

async def check_user_status(socket_manager, user_id: str):
    """Check and update user status"""
    try:
        # Check if user has any active socket connections
        is_online = user_id in user_sockets and len(user_sockets[user_id]) > 0
        
        if is_online:
            status = "online"
            last_seen = datetime.utcnow()
        else:
            # Get last seen from database
            user = await user_collection.find_one({"_id": ObjectId(user_id)})
            status = "offline"
            last_seen = user.get("last_seen", datetime.utcnow()) if user else datetime.utcnow()
        
        # Update status tracking
        user_statuses[user_id] = {"status": status, "last_seen": last_seen}
        
        # Persist to database
        try:
            await user_collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "chat_status": status,
                        "last_seen": last_seen,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        except Exception as e:
            logger.error(f"Failed to persist user status to database: {e}")
        
        # Broadcast status update
        await broadcast_user_status(socket_manager, user_id, status, last_seen)
        
    except Exception as e:
        logger.error(f"Error checking user status for {user_id}: {str(e)}")

async def is_user_online(user_id: str) -> bool:
    """Check if a user is currently online"""
    return user_id in user_sockets and len(user_sockets[user_id]) > 0

async def send_chat_notification(sender_id: str, receiver_id: str, message_content: str, conversation_id: str, property_id: str):
    """Send notification for new chat message"""
    try:
        # Initialize notification service
        notification_service = NotificationService()
        
        # Get sender details
        sender = await user_collection.find_one({"_id": ObjectId(sender_id)})
        if not sender:
            logger.error(f"Sender {sender_id} not found")
            return

        # Get property details
        property_doc = await property_collection.find_one({"_id": ObjectId(property_id)})
        if not property_doc:
            logger.error(f"Property {property_id} not found")
            return

        # Create message preview (truncate if too long)
        message_preview = message_content[:100] + "..." if len(message_content) > 100 else message_content
        
        sender_name = f"{sender.get('first_name', '')} {sender.get('last_name', '')}".strip()
        property_title = property_doc.get('title', 'Unknown Property')

        # Check if receiver is online
        receiver_online = await is_user_online(receiver_id)
        
        # Create notification title and message
        notification_title = f"New message from {sender_name}"
        notification_message = f"{sender_name} sent you a message about {property_title}: {message_preview}"
        
        # Send notification using create_notification
        await notification_service.create_notification(
            user_id=receiver_id,
            title=notification_title,
            message=notification_message
        )

        logger.info(f"Chat notification sent from {sender_id} to {receiver_id} for conversation {conversation_id}")

    except Exception as e:
        logger.error(f"Error sending chat notification: {str(e)}")

def register_socket_handlers(socket_manager):
    """Register all Socket.IO event handlers"""
    
    @socket_manager.on("connect")
    async def connect(sid, environ, auth=None):
        """Handle Socket.IO connections"""
        try:
            # Get token from auth data
            if not auth or "token" not in auth:
                logger.warning(f"Connection attempt without token: {sid}")
                await socket_manager.disconnect(sid)
                return False

            # Authenticate user
            user_id = await authenticate_socket(auth["token"])
            if not user_id:
                logger.warning("Failed to authenticate socket connection")
                await socket_manager.disconnect(sid)
                return False

            # Store the connection
            active_connections[sid] = user_id
            
            # Track user's sockets
            is_new_connection = user_id not in user_sockets or len(user_sockets[user_id]) == 0
            
            if user_id not in user_sockets:
                user_sockets[user_id] = set()
            user_sockets[user_id].add(sid)

            # Track connection time only for the first connection
            if is_new_connection:
                user_connection_times[user_id] = datetime.utcnow()

            # Update and broadcast status
            await check_user_status(socket_manager, user_id)

            # Send confirmation to the connected client
            await socket_manager.emit('connect_confirmed', {'user_id': user_id}, room=sid)
            
            logger.info(f"User {user_id} connected with socket {sid}")
            return True

        except Exception as e:
            logger.error(f"Error in connect handler: {str(e)}")
            await socket_manager.disconnect(sid)
            return False

    @socket_manager.on("disconnect")
    async def disconnect(sid, *args):
        """Handle Socket.IO disconnections"""
        if sid in active_connections:
            try:
                user_id = active_connections[sid]
                
                # Remove this socket from user's tracked sockets
                if user_id in user_sockets:
                    user_sockets[user_id].discard(sid)
                    
                    # Clean up if no more connections
                    if not user_sockets[user_id]:
                        logger.info(f"User {user_id} has no more active connections, marking as offline")
                        del user_sockets[user_id]
                        if user_id in user_connection_times:
                            del user_connection_times[user_id]
                    
                    # Update and broadcast status
                    await check_user_status(socket_manager, user_id)

                del active_connections[sid]
            except Exception as e:
                logger.error(f"Error in disconnect handler: {str(e)}")

    @socket_manager.on("get_user_status")
    async def get_user_status(sid, data):
        """Handle requests for user status"""
        try:
            user_id = data.get("user_id")
            if not user_id:
                logger.warning("Received status request without user_id")
                return
            
            await check_user_status(socket_manager, user_id)
            
        except Exception as e:
            logger.error(f"Error getting user status: {str(e)}")

    @socket_manager.on("send_message")
    async def send_message(sid, data):
        """Handle new messages sent via Socket.IO"""
        try:
            if sid not in active_connections:
                logger.warning("Unauthenticated message attempt")
                return

            user_id = active_connections[sid]
            conversation_id = data.get("conversation_id")
            content = data.get("content")

            if not conversation_id or not content:
                logger.warning(f"Invalid message data from user {user_id}")
                await socket_manager.emit(
                    "error", {"message": "Invalid message data"}, room=sid
                )
                return

            # Verify conversation access
            conversation = await conversation_collection.find_one(
                {
                    "_id": ObjectId(conversation_id),
                    "$or": [{"user_id": user_id}, {"owner_id": user_id}],
                }
            )

            if not conversation:
                logger.warning(
                    f"User {user_id} attempted to message unauthorized conversation: {conversation_id}"
                )
                await socket_manager.emit(
                    "error", {"message": "Conversation access denied"}, room=sid
                )
                return

            # Determine receiver ID
            receiver_id = (
                conversation["owner_id"]
                if user_id == conversation["user_id"]
                else conversation["user_id"]
            )

            # Create and save the message
            message = {
                "conversation_id": conversation_id,
                "sender_id": user_id,
                "receiver_id": receiver_id,
                "content": content,
                "created_at": datetime.utcnow(),
                "read": False,
            }

            result = await message_collection.insert_one(message)
            message["_id"] = str(result.inserted_id)

            # Format message for sending
            formatted_message = {
                "id": message["_id"],
                "conversation_id": message["conversation_id"],
                "sender_id": message["sender_id"],
                "content": message["content"],
                "created_at": message["created_at"].isoformat(),
                "read": message["read"],
            }

            # Determine which user's unread count to increment
            # If sender is the regular user, increment owner's unread count
            # If sender is the owner, increment user's unread count
            unread_field = (
                "unread_count_owner" 
                if user_id == conversation["user_id"] 
                else "unread_count_user"
            )

            # Update conversation with last message info and increment the appropriate unread count
            await conversation_collection.update_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "$set": {
                        "last_message": content,
                        "last_message_time": datetime.utcnow(),
                    },
                    "$inc": {unread_field: 1}
                },
            )

            # Send notification to receiver
            await send_chat_notification(
                sender_id=user_id,
                receiver_id=receiver_id,
                message_content=content,
                conversation_id=conversation_id,
                property_id=conversation["property_id"]
            )

            # Broadcast to the conversation room
            await socket_manager.emit(
                "new_message", formatted_message, room=conversation_id
            )

            # Also send to the sender for acknowledgment
            await socket_manager.emit(
                "message_sent", {"message_id": message["_id"]}, room=sid
            )

            logger.info(f"Message processed successfully: {message['_id']}")

        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            await socket_manager.emit(
                "error", {"message": "Failed to send message"}, room=sid
            )

    @socket_manager.on("join")
    async def join_room(sid, data):
        try:
            conversation_id = data.get("conversation_id")
            if not conversation_id:
                return

            # Get the user who is joining
            user_id = active_connections.get(sid)
            if not user_id:
                return
            
            # Get the conversation to find the other user
            conversation = await conversation_collection.find_one({"_id": ObjectId(conversation_id)})
            if not conversation:
                return
                
            # Get the other user's ID
            other_user_id = conversation["owner_id"] if user_id == conversation["user_id"] else conversation["user_id"]
            
            # Send both users' statuses
            if user_id in user_statuses:
                await broadcast_user_status(
                    socket_manager, 
                    user_id, 
                    user_statuses[user_id]["status"],
                    user_statuses[user_id]["last_seen"]
                )
                
            if other_user_id in user_statuses:
                await broadcast_user_status(
                    socket_manager,
                    other_user_id,
                    user_statuses[other_user_id]["status"],
                    user_statuses[other_user_id]["last_seen"]
                )

            await socket_manager.enter_room(sid, conversation_id)
            await socket_manager.emit("room_joined", {"room": conversation_id}, room=sid)
            
        except Exception as e:
            logger.error(f"Error joining room: {str(e)}")

    @socket_manager.on("typing_status")
    async def typing_status(sid, data):
        try:
            user_id = active_connections.get(sid)
            if not user_id:
                return

            conversation = await conversation_collection.find_one({"_id": ObjectId(data["conversation_id"])})
            if not conversation:
                return

            receiver_id = conversation["owner_id"] if user_id == conversation["user_id"] else conversation["user_id"]

            # Find receiver's socket ID
            receiver_sid = None
            for sid_item, uid in active_connections.items():
                if uid == receiver_id:
                    receiver_sid = sid_item
                    break

            if receiver_sid:
                await socket_manager.emit(
                    "typing_status",
                    {
                        "conversation_id": data["conversation_id"],
                        "user_id": user_id,
                        "is_typing": data["is_typing"]
                    },
                    room=receiver_sid
                )
        except Exception as e:
            logger.error(f"Error updating typing status: {str(e)}")

    @socket_manager.on("leave_conversation")
    async def leave_conversation(sid, conversation_id):
        await socket_manager.leave_room(sid, conversation_id)

async def update_conversation_activity(conversation_id):
    """Update the last activity time for a conversation"""
    active_conversations[conversation_id] = datetime.utcnow()
    
async def cleanup_inactive_conversations():
    """Remove conversation rooms that have been inactive for over 24 hours"""
    current_time = datetime.utcnow()
    inactive_threshold = current_time - timedelta(hours=24)
    
    conversations_to_remove = []
    for conversation_id, last_activity in active_conversations.items():
        if last_activity < inactive_threshold:
            conversations_to_remove.append(conversation_id)
    
    # Clean up inactive conversations
    for conversation_id in conversations_to_remove:
        del active_conversations[conversation_id]
        logger.info(f"Cleaned up inactive conversation: {conversation_id}")
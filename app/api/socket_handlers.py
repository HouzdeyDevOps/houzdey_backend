from app.core.database import message_collection, conversation_collection
from bson import ObjectId
import logging
from datetime import datetime, timedelta
from jose import JWTError, jwt
from app.core.config import settings
from app.crud.user import get_user

logger = logging.getLogger(__name__)

active_connections = {}  # {sid: user_email}
active_conversations = {}
user_sockets = {}  # {user_id: set(sids)} - Track all sockets for each user
user_statuses = {}  # {user_id: {"status": "online"|"offline", "last_seen": datetime}}


async def authenticate_socket(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_email = payload.get("sub")  # Use the same field as in chat.py

        if user_email is None:
            raise JWTError
        return user_email
    except JWTError:
        return None


async def broadcast_user_status(socket_manager, user_id: str, status: str, last_seen: datetime):
    """Helper function to broadcast user status to all connected clients"""
    status_data = {
        "user_id": user_id,
        "status": status,
        "last_seen": last_seen.isoformat()
    }
    # Emit to all clients without specifying a namespace
    await socket_manager.emit("user_status", status_data)


async def check_user_status(socket_manager, user_id: str):
    """Check and broadcast a user's current status"""
    is_online = user_id in user_sockets and len(user_sockets[user_id]) > 0
    current_time = datetime.utcnow()
    
    status = "online" if is_online else "offline"
    user_statuses[user_id] = {
        "status": status,
        "last_seen": current_time
    }
    
    await broadcast_user_status(socket_manager, user_id, status, current_time)


def register_socket_handlers(socket_manager):
    @socket_manager.on("connect")
    async def connect(sid, environ, auth=None):
        """Handle new Socket.IO connections with token authentication"""
        try:
            if not auth or "token" not in auth:
                logger.warning(f"Connection attempt without token: {sid}")
                await socket_manager.disconnect(sid)
                return
            token = auth["token"]
            user_email = await authenticate_socket(token)

            if not user_email:
                logger.warning(f"Authentication failed for connection: {sid}")
                await socket_manager.disconnect(sid)
                return

            user = await get_user(user_email)
            # Store the authenticated user's ID
            active_connections[sid] = user_email
            
            # Track this socket for the user
            if user.id not in user_sockets:
                user_sockets[user.id] = set()
            user_sockets[user.id].add(sid)


            # Update and broadcast status
            await check_user_status(socket_manager, user.id)

            # Send all other users' statuses to the newly connected user
            for uid in user_sockets.keys():
                if uid != user.id:
                    await check_user_status(socket_manager, uid)

            # Emit confirmation of successful connection
            await socket_manager.emit(
                "connect_confirmed", {"user_id": user.id}, room=sid
            )

        except Exception as e:
            logger.error(f"Socket connection error: {str(e)}")
            await socket_manager.disconnect(sid)

    @socket_manager.on("disconnect")
    async def disconnect(sid, *args):
        """Handle Socket.IO disconnections"""
        if sid in active_connections:
            try:
                user_email = active_connections[sid]
                user = await get_user(user_email)
                
                # Remove this socket from user's tracked sockets
                if user.id in user_sockets:
                    user_sockets[user.id].remove(sid)
                    
                    # Clean up if no more connections
                    if not user_sockets[user.id]:
                        logger.info(f"User {user.id} has no more active connections, marking as offline")
                        del user_sockets[user.id]
                    
                    # Update and broadcast status
                    await check_user_status(socket_manager, user.id)

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

            user_email = active_connections[sid]
            user = await get_user(user_email)
            conversation_id = data.get("conversation_id")
            content = data.get("content")

            if not conversation_id or not content:
                logger.warning(f"Invalid message data from user {user.id}")
                await socket_manager.emit(
                    "error", {"message": "Invalid message data"}, room=sid
                )
                return

            # Verify conversation access
            conversation = await conversation_collection.find_one(
                {
                    "_id": ObjectId(conversation_id),
                    "$or": [{"user_id": user.id}, {"owner_id": user.id}],
                }
            )

            if not conversation:
                logger.warning(
                    f"User {user.id} attempted to message unauthorized conversation: {conversation_id}"
                )
                await socket_manager.emit(
                    "error", {"message": "Conversation access denied"}, room=sid
                )
                return

            # Determine receiver ID
            receiver_id = (
                conversation["owner_id"]
                if user.id == conversation["user_id"]
                else conversation["user_id"]
            )

            # Create and save the message
            message = {
                "conversation_id": conversation_id,
                "sender_id": user.id,
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

            # Update conversation with last message info
            await conversation_collection.update_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "$set": {
                        "last_message": content,
                        "last_message_time": datetime.utcnow(),
                    },
                },
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
            user_email = active_connections.get(sid)
            if not user_email:
                return
                
            user = await get_user(user_email)
            
            # Get the conversation to find the other user
            conversation = await conversation_collection.find_one({"_id": ObjectId(conversation_id)})
            if not conversation:
                return
                
            # Get the other user's ID
            other_user_id = conversation["owner_id"] if user.id == conversation["user_id"] else conversation["user_id"]
            
            # Send both users' statuses
            if user.id in user_statuses:
                await broadcast_user_status(
                    socket_manager, 
                    user.id, 
                    user_statuses[user.id]["status"],
                    user_statuses[user.id]["last_seen"]
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
            user_email = active_connections.get(sid)
            if not user_email:
                return

            user = await get_user(user_email)
            conversation = await conversation_collection.find_one({"_id": ObjectId(data["conversation_id"])})
            if not conversation:
                return

            receiver_id = conversation["owner_id"] if user.id == conversation["user_id"] else conversation["user_id"]

            # Find receiver's socket ID
            receiver_sid = None
            for sid, email in active_connections.items():
                if (await get_user(email)).id == receiver_id:
                    receiver_sid = sid
                    break

            if receiver_sid:
                await socket_manager.emit(
                    "typing_status",
                    {
                        "conversation_id": data["conversation_id"],
                        "user_id": user.id,
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
    
    for conversation_id, last_activity in list(active_conversations.items()):
        if last_activity < inactive_threshold:
            # Remove from tracking
            del active_conversations[conversation_id]
            logger.info(f"Cleaned up inactive conversation room: {conversation_id}")
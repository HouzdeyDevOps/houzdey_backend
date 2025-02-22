# from main import app, socket_manager
from app.core.security import verify_token
from fastapi import WebSocket, WebSocketDisconnect
from app.core.database import message_collection, conversation_collection
from bson import ObjectId
import logging
from datetime import datetime
from fastapi import HTTPException
from jose import JWTError, jwt
from app.core.config import settings
from app.crud.user import get_user
from datetime import timedelta, datetime

logger = logging.getLogger(__name__)

active_connections = {}
active_conversations = {}


async def authenticate_socket(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_email = payload.get("sub")  # Use the same field as in chat.py

        if user_email is None:
            raise JWTError
        return user_email
    except JWTError:
        return None


def register_socket_handlers(socket_manager):
    @socket_manager.on("connect")
    async def connect(sid, environ, auth=None):
        print(f"connect: {sid}, {auth}")
        """Handle new Socket.IO connections with token authentication"""
        try:
            if not auth or "token" not in auth:
                logger.warning(f"Connection attempt without token: {sid}")
                await socket_manager.disconnect(sid)
                return
            token = auth["token"]
            user_id = await authenticate_socket(token)


            if not user_id:
                logger.warning(f"Authentication failed for connection: {sid}")
                await socket_manager.disconnect(sid)
                return

            # Store the authenticated user's ID
            active_connections[sid] = user_id
            logger.info(f"User {user_id} connected with socket ID: {sid}")

            # Emit confirmation of successful connection
            await socket_manager.emit(
                "connect_confirmed", {"user_id": user_id}, room=sid
            )

        except Exception as e:
            logger.error(f"Socket connection error: {str(e)}")
            await socket_manager.disconnect(sid)

    @socket_manager.on("disconnect")
    async def disconnect(sid):
        """Handle Socket.IO disconnections"""
        if sid in active_connections:
            user_id = active_connections[sid]
            logger.info(f"User {user_id} disconnected from socket ID: {sid}")
            del active_connections[sid]

    

    @socket_manager.on("send_message")
    async def send_message(sid, data):
        """Handle new messages sent via Socket.IO"""
        print(f"send_message: {data}, {sid}")
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
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            return
        await socket_manager.enter_room(sid, conversation_id)
        await socket_manager.emit("room_joined", {"room": conversation_id}, room=sid)


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
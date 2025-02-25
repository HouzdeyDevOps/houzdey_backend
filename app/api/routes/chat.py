from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from app.core.database import (
    conversation_collection,
    message_collection,
    property_collection,
    user_collection,
)
from app.api.deps import get_current_user
from app.models.chat import ConversationResponse
from app.models.user import User
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
import logging
from fastapi.responses import JSONResponse
import json
import cloudinary # type: ignore
import cloudinary.uploader # type: ignore
from app.api.socket_manager import get_socket_manager

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/conversations", response_model=list[ConversationResponse])
async def get_conversations(current_user: User = Depends(get_current_user)):
    try:
        # Find all conversations where the current user is either the user or owner
        conversations = await conversation_collection.find({
            "$or": [
                {"user_id": str(current_user.id)},
                {"owner_id": str(current_user.id)}
            ]
        }).sort("last_message_time", -1).to_list(None)

        formatted_conversations = []
        for conv in conversations:
            # Get property details
            property = await property_collection.find_one({"_id": ObjectId(conv["property_id"])})
            if not property:
                continue  # Skip if property not found

            # Get other user details (the one who is not the current user)
            other_user_id = conv["owner_id"] if conv["user_id"] == str(current_user.id) else conv["user_id"]
            other_user = await user_collection.find_one({"_id": ObjectId(other_user_id)})
            if not other_user:
                continue  # Skip if other user not found

            # Format the conversation with all required details
            formatted_conversations.append({
                "id": str(conv["_id"]),
                "property_id": conv["property_id"],
                "property": {
                    "id": str(property["_id"]),
                    "title": property["title"],
                    "image": property.get("images", [])[0] if property.get("images") else None,
                    "price": property["price"],
                    "location": property["location"],
                    "type": property.get("type", ""),
                    "status": property.get("status", "active")
                },
                "user_id": conv["user_id"],
                "owner_id": conv["owner_id"],
                "other_user": {
                    "id": str(other_user["_id"]),
                    "first_name": other_user["first_name"],
                    "last_name": other_user["last_name"],
                    "profile_picture": other_user.get("profile_picture"),
                    "email": other_user["email"],
                    "phone": other_user.get("phone_number")  # Note: using phone_number field from user model
                },
                "last_message": conv.get("last_message"),
                "last_message_time": conv.get("last_message_time"),
                "unread_count": conv.get("unread_count", 0),
                "created_at": conv.get("created_at", datetime.utcnow())
            })

        return formatted_conversations
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, current_user: User = Depends(get_current_user)):
    try:
        # Get conversation
        conversation = await conversation_collection.find_one({"_id": ObjectId(conversation_id)})
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Verify user has access to this conversation
        if str(conversation["user_id"]) != str(current_user.id) and str(conversation["owner_id"]) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Get property details
        property = await property_collection.find_one({"_id": ObjectId(conversation["property_id"])})
        if not property:
            raise HTTPException(status_code=404, detail="Property not found")

        # Get other user details
        other_user_id = conversation["owner_id"] if conversation["user_id"] == str(current_user.id) else conversation["user_id"]
        other_user = await user_collection.find_one({"_id": ObjectId(other_user_id)})
        if not other_user:
            raise HTTPException(status_code=404, detail="Other user not found")

        # Format and return conversation with all details
        return {
            "id": str(conversation["_id"]),
            "property_id": conversation["property_id"],
            "property": {
                "id": str(property["_id"]),
                "title": property["title"],
                "image": property.get("images", [])[0] if property.get("images") else None,
                "price": property["price"],
                "location": property["location"],
                "type": property.get("type", ""),
                "status": property.get("status", "active")
            },
            "user_id": conversation["user_id"],
            "owner_id": conversation["owner_id"],
            "other_user": {
                "id": str(other_user["_id"]),
                "first_name": other_user["first_name"],
                "last_name": other_user["last_name"],
                "profile_picture": other_user.get("profile_picture"),
                "email": other_user["email"],
                "phone": other_user.get("phone_number")
            },
            "last_message": conversation.get("last_message"),
            "last_message_time": conversation.get("last_message_time"),
            "unread_count": conversation.get("unread_count", 0),
            "created_at": conversation.get("created_at", datetime.utcnow())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str, current_user: User = Depends(get_current_user)
):
    try:
        # Validate conversation exists and user has access
        conversation = await conversation_collection.find_one(
            {
                "_id": ObjectId(conversation_id),
                "$or": [{"user_id": current_user.id}, {"owner_id": current_user.id}],
            }
        )

        if not conversation:
            return JSONResponse(
                status_code=404, content={"detail": "Conversation not found"}
            )

        # Get messages
        messages = (
            await message_collection.find({"conversation_id": conversation_id})
            .sort("created_at", 1)
            .to_list(None)
        )

        # Format messages
        formatted_messages = [
            {
                "id": str(msg["_id"]),
                "conversation_id": msg["conversation_id"],
                "sender_id": msg["sender_id"],
                "content": msg["content"],
                "created_at": msg["created_at"].isoformat(),
                "read": msg["read"],
            }
            for msg in messages
        ]

        return formatted_messages

    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")


@router.post("/conversations")
async def create_conversation(property_id: str, current_user=Depends(get_current_user)):
    try:
        # Validate property exists
        property = await property_collection.find_one({"_id": ObjectId(property_id)})

        if not property:
            raise HTTPException(status_code=404, detail="Property not found")

        # Check if conversation already exists
        existing_conversation = await conversation_collection.find_one(
            {
                "property_id": property_id,
                "user_id": str(current_user.id),
                "owner_id": str(property["owner_id"]),
            }
        )

        if existing_conversation:
            return {
                "id": str(existing_conversation["_id"]),
                "property_id": property_id,
                "user_id": str(current_user.id),
                "owner_id": str(property["owner_id"]),
                "created_at": existing_conversation["created_at"],
            }

        # Create new conversation
        conversation = {
            "_id": ObjectId(),
            "property_id": property_id,
            "user_id": str(current_user.id),
            "owner_id": str(property["owner_id"]),
            "created_at": datetime.utcnow(),
            "last_message": None,
            "last_message_time": None,
            "unread_count": 0,
        }

        await conversation_collection.insert_one(conversation)

        return {
            "id": str(conversation["_id"]),
            "property_id": property_id,
            "user_id": str(current_user.id),
            "owner_id": str(property["owner_id"]),
            "created_at": conversation["created_at"],
        }

    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid property ID")


@router.post("/conversations/{conversation_id}/read")
async def mark_messages_as_read(
    conversation_id: str, current_user=Depends(get_current_user)
):
    # Mark messages as read
    await message_collection.update_many(
        {"conversation_id": conversation_id, "receiver_id": str(current_user.id)},
        {"$set": {"read": True}},
    )
    
    # Reset unread count
    await conversation_collection.update_one(
        {"_id": ObjectId(conversation_id)},
        {"$set": {"unread_count": 0}}
    )
    
    # Emit socket event to notify other users
    socket_manager = get_socket_manager()
    await socket_manager.emit("messages_read", {"conversation_id": conversation_id}, room=conversation_id)
    
    return {"status": "success"}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str, current_user=Depends(get_current_user)
):
    # Verify user has access to this conversation
    conversation = await conversation_collection.find_one(
        {"_id": ObjectId(conversation_id)}
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if str(current_user.id) not in [conversation["user_id"], conversation["owner_id"]]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Delete all messages in the conversation
    await message_collection.delete_many({"conversation_id": conversation_id})

    # Delete the conversation
    await conversation_collection.delete_one({"_id": ObjectId(conversation_id)})

    return {"status": "success"}


# Helper function that might be used internally
async def get_other_user_id(conversation_id: str, current_user_id: str) -> str:
    conversation = await conversation_collection.find_one(
        {"_id": ObjectId(conversation_id)}
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Return the user ID that is not the current user
    return (
        conversation["user_id"]
        if conversation["owner_id"] == current_user_id
        else conversation["owner_id"]
    )


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a message and its associated file if any"""
    try:
        # Find the message
        message = await message_collection.find_one({"_id": ObjectId(message_id)})
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
            
        # Check if user is the sender
        if str(message["sender_id"]) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own messages"
            )

        # If message has a file, delete it from Cloudinary
        try:
            content = message.get("content")
            if content:
                try:
                    content_data = json.loads(content)
                    if content_data.get("file_url"):
                        # Extract public_id from Cloudinary URL
                        public_id = content_data["file_url"].split("/")[-1].split(".")[0]
                        # Delete from Cloudinary
                        cloudinary.uploader.destroy(public_id)
                except (json.JSONDecodeError, KeyError):
                    pass  # Not a JSON message or doesn't have file_url
        except Exception as e:
            print(f"Error deleting file from Cloudinary: {str(e)}")
            # Continue with message deletion even if file deletion fails

        # Delete the message
        result = await message_collection.delete_one({"_id": ObjectId(message_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
            
        return {"status": "success", "message": "Message deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
#!/usr/bin/env python3
"""
Script to optimize chat database indexes for better performance
"""

import asyncio
import pymongo
from app.core.database import message_collection, conversation_collection


async def create_chat_indexes():
    """Create optimized indexes for chat collections"""
    
    print("Creating message collection indexes...")
    
    # Index for finding messages by conversation
    await message_collection.create_index("conversation_id")
    print("✓ conversation_id index created")
    
    # Index for finding unread messages by receiver
    await message_collection.create_index([("receiver_id", 1), ("read", 1)])
    print("✓ receiver_id + read compound index created")
    
    # Index for message ordering
    await message_collection.create_index([("conversation_id", 1), ("created_at", 1)])
    print("✓ conversation_id + created_at compound index created")
    
    # Index for message sender (for deletion authorization)
    await message_collection.create_index("sender_id")
    print("✓ sender_id index created")
    
    # Conversation collection indexes
    
    print("\nCreating conversation collection indexes...")
    
    # Index for finding user's conversations
    await conversation_collection.create_index("user_id")
    print("✓ user_id index created")
    
    # Index for finding owner's conversations
    await conversation_collection.create_index("owner_id")
    print("✓ owner_id index created")
    
    # Compound index for unique conversation per property-user pair
    await conversation_collection.create_index(
        [("property_id", 1), ("user_id", 1), ("owner_id", 1)],
        unique=True
    )
    print("✓ property_id + user_id + owner_id unique compound index created")
    
    # Index for conversation ordering
    await conversation_collection.create_index([("last_message_time", -1)])
    print("✓ last_message_time index created (for sorting)")
    
    print("\n🎉 All chat indexes created successfully!")
    
    # Print current indexes for verification
    print("\n📊 Current message collection indexes:")
    async for index in message_collection.list_indexes():
        print(f"  - {index}")
        
    print("\n📊 Current conversation collection indexes:")
    async for index in conversation_collection.list_indexes():
        print(f"  - {index}")


if __name__ == "__main__":
    asyncio.run(create_chat_indexes()) 
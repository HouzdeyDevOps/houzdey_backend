#!/usr/bin/env python3
"""
Migration script to add chat status fields to existing users
"""

import asyncio
from datetime import datetime, timezone
from app.core.database import db_manager


async def add_chat_status_fields():
    """Add chat_status and last_seen fields to existing users"""
    user_collection = db_manager.get_collection("users")
    
    print("Adding chat status fields to existing users...")
    
    # Add default chat status fields to users who don't have them
    result = await user_collection.update_many(
        {
            "$or": [
                {"chat_status": {"$exists": False}},
                {"last_seen": {"$exists": False}}
            ]
        },
        {
            "$set": {
                "chat_status": "offline",
                "last_seen": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    print(f"✓ Updated {result.modified_count} users with chat status fields")
    
    # Print summary
    total_users = await user_collection.count_documents({})
    print(f"📊 Total users in database: {total_users}")
    
    users_with_status = await user_collection.count_documents({"chat_status": {"$exists": True}})
    print(f"📊 Users with chat status: {users_with_status}")
    
    print("\n🎉 Chat status fields migration completed!")


if __name__ == "__main__":
    asyncio.run(add_chat_status_fields()) 
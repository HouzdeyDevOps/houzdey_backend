"""
Debug script to check MongoDB connection and property structure
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


async def debug_mongodb():
    """Debug MongoDB connection and property structure"""
    
    try:
        print(f"MONGO_URL: {settings.MONGO_URL[:50]}...")
        print(f"PROJECT_NAME: {settings.PROJECT_NAME}")
        
        # Connect to MongoDB
        print("\nConnecting to MongoDB...")
        client = AsyncIOMotorClient(settings.MONGO_URL)
        db = client.Houzdey  # Database name is "Houzdey" (capital H)
        
        # List all collections
        print("\nCollections in database:")
        collections = await db.list_collection_names()
        for col in collections:
            count = await db[col].count_documents({})
            print(f"  - {col}: {count} documents")
        
        # Get properties collection
        properties_collection = db["properties"]
        
        # Count properties
        total = await properties_collection.count_documents({})
        print(f"\nTotal properties: {total}")
        
        if total > 0:
            # Get one property to see structure
            print("\nSample property structure:")
            property_obj = await properties_collection.find_one({})
            
            if property_obj:
                print(f"  _id: {property_obj.get('_id')}")
                print(f"  _id type: {type(property_obj.get('_id'))}")
                print(f"  title: {property_obj.get('title')}")
                print(f"  slug: {property_obj.get('slug', 'NOT SET')}")
                print(f"  listing_type: {property_obj.get('listing_type')}")
                print(f"  type: {property_obj.get('type')}")
                print(f"  beds: {property_obj.get('beds')}")
                print(f"  lga: {property_obj.get('lga')}")
                print(f"  state: {property_obj.get('state')}")
                
                # Show all keys
                print(f"\n  All keys: {list(property_obj.keys())}")
        
        client.close()
        print("\n✅ Debug complete")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_mongodb())

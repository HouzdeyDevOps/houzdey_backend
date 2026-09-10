"""
Quick script to add slug to a specific property
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from app.core.config import settings
from app.utils.slug import generate_property_slug


async def add_slug_to_property(property_id: str):
    """Add slug to a specific property by ID"""
    
    try:
        # Connect to MongoDB
        print(f"Connecting to MongoDB...")
        client = AsyncIOMotorClient(settings.MONGO_URL)
        db = client.Houzdey  # Database name is "Houzdey" (capital H)
        properties_collection = db["properties"]
        
        # Find the property - try both as ObjectId and as string
        print(f"Looking for property: {property_id}")
        try:
            property_obj = await properties_collection.find_one({"_id": ObjectId(property_id)})
        except:
            # Try as string ID
            property_obj = await properties_collection.find_one({"id": property_id})
        
        if not property_obj:
            print(f"❌ Property not found: {property_id}")
            return
        
        # Show current property details
        print(f"\n{'='*60}")
        print("PROPERTY DETAILS")
        print(f"{'='*60}")
        print(f"ID: {property_obj['_id']}")
        print(f"Title: {property_obj.get('title', 'N/A')}")
        print(f"Type: {property_obj.get('type', 'N/A')}")
        print(f"Listing Type: {property_obj.get('listing_type', 'N/A')}")
        print(f"Beds: {property_obj.get('beds', 0)}")
        print(f"LGA: {property_obj.get('lga', 'N/A')}")
        print(f"State: {property_obj.get('state', 'N/A')}")
        print(f"Current Slug: {property_obj.get('slug', 'None')}")
        print(f"{'='*60}\n")
        
        # Generate slug
        print("Generating slug...")
        slug = generate_property_slug(
            listing_type=property_obj.get("listing_type", "rent"),
            beds=property_obj.get("beds", 0),
            property_type=property_obj.get("type", "property"),
            address=property_obj.get("address", ""),
            state=property_obj.get("state", "unknown"),
            property_id=str(property_obj["_id"])
        )
        
        print(f"Generated slug: {slug}")
        print(f"Full URL: https://houzdey.com/properties/{slug}\n")
        
        # Update property
        result = await properties_collection.update_one(
            {"_id": property_obj["_id"]},
            {"$set": {"slug": slug}}
        )
        
        if result.modified_count > 0:
            print("✅ Slug added successfully!")
            
            # Verify update
            updated_property = await properties_collection.find_one({"_id": ObjectId(property_id)})
            print(f"\nVerified - New slug: {updated_property.get('slug')}")
        else:
            print("⚠️ No changes made (slug may already exist)")
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/add_slug_to_property.py <property_id>")
        print("Example: python scripts/add_slug_to_property.py 690d2078c21cb96f97d3a21c")
        sys.exit(1)
    
    property_id = sys.argv[1]
    asyncio.run(add_slug_to_property(property_id))

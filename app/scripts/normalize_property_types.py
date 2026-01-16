"""
Migration script to normalize property types in the database.

This script maps scraped property types to the standardized PropertyType enum
used in the frontend.

Run with: python -m app.scripts.normalize_property_types
"""

import asyncio
from app.core.database import db_manager
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Valid frontend PropertyType enum values
VALID_PROPERTY_TYPES = {
    "Apartment", "Land", "Bedsitter", "Block of Flats", "Bungalow",
    "Chalet", "Condo", "Duplex", "Farm House", "House", "Maisonette",
    "Mansion", "Mini Flat", "Penthouse", "Room & Parlour",
    "Shared Apartment", "Studio Apartment", "Townhouse / Terrace", "Villa"
}

# Mapping from scraped types to frontend PropertyType enum
PROPERTY_TYPE_MAPPING = {
    # Scraped types -> Frontend enum values
    "flat": "Apartment",
    "apartment": "Apartment",
    "flats-apartments": "Apartment",
    
    "house": "House",
    "detached": "House",
    "semi-detached": "House",
    
    "duplex": "Duplex",
    
    "bungalow": "Bungalow",
    
    "terrace": "Townhouse / Terrace",
    "townhouse": "Townhouse / Terrace",
    "terraced": "Townhouse / Terrace",
    
    "studio": "Studio Apartment",
    "studio apartment": "Studio Apartment",
    
    "penthouse": "Penthouse",
    
    "mini flat": "Mini Flat",
    "miniflat": "Mini Flat",
    "mini-flat": "Mini Flat",
    
    "room and parlour": "Room & Parlour",
    "room & parlour": "Room & Parlour",
    "self contain": "Bedsitter",
    "self-contain": "Bedsitter",
    "bedsitter": "Bedsitter",
    
    "shared apartment": "Shared Apartment",
    "shared": "Shared Apartment",
    
    "block of flats": "Block of Flats",
    "block": "Block of Flats",
    
    "mansion": "Mansion",
    "villa": "Villa",
    "maisonette": "Maisonette",
    "condo": "Condo",
    "chalet": "Chalet",
    "farm house": "Farm House",
    "farmhouse": "Farm House",
    "land": "Land",
}


async def normalize_property_types():
    """Normalize all property types in the database"""
    
    # Initialize database connection
    db_manager.initialize()
    properties_collection = db_manager.get_collection("properties")
    
    try:
        logger.info("🔍 Starting property type normalization...")
        
        # Get all properties
        total_properties = await properties_collection.count_documents({})
        logger.info(f"📊 Found {total_properties} total properties")
        
        # Track statistics
        updated_count = 0
        unchanged_count = 0
        unknown_types = set()
        type_stats = {}
        
        # Process all properties
        cursor = properties_collection.find({})
        
        async for property_doc in cursor:
            property_id = property_doc["_id"]
            current_type = property_doc.get("type", "").strip()
            
            if not current_type:
                logger.warning(f"⚠️  Property {property_id} has no type")
                continue
            
            # Skip if already a valid frontend type
            if current_type in VALID_PROPERTY_TYPES:
                unchanged_count += 1
                type_stats[current_type] = type_stats.get(current_type, 0) + 1
                continue
            
            # Normalize to lowercase for matching
            current_type_lower = current_type.lower()
            
            # Check if type needs normalization
            if current_type_lower in PROPERTY_TYPE_MAPPING:
                new_type = PROPERTY_TYPE_MAPPING[current_type_lower]
                
                # Track statistics
                type_stats[new_type] = type_stats.get(new_type, 0) + 1
                
                # Update to new type
                await properties_collection.update_one(
                    {"_id": property_id},
                    {"$set": {"type": new_type}}
                )
                updated_count += 1
                logger.info(f"✅ Updated: '{current_type}' → '{new_type}' (ID: {property_id})")
            else:
                # Unknown type - needs manual review
                unknown_types.add(current_type)
                logger.warning(f"❓ Unknown type: '{current_type}' (ID: {property_id})")
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("📈 NORMALIZATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total properties: {total_properties}")
        logger.info(f"✅ Updated: {updated_count}")
        logger.info(f"⏭️  Unchanged (already valid): {unchanged_count}")
        logger.info(f"❓ Unknown types: {len(unknown_types)}")
        
        if unknown_types:
            logger.info("\n⚠️  Unknown property types found:")
            for unknown_type in sorted(unknown_types):
                count = await properties_collection.count_documents({"type": unknown_type})
                logger.info(f"   - '{unknown_type}' ({count} properties)")
        
        logger.info("\n📊 Property type distribution:")
        for prop_type, count in sorted(type_stats.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"   - {prop_type}: {count}")
        
        logger.info("\n✅ Normalization complete!")
        
    except Exception as e:
        logger.error(f"❌ Error during normalization: {str(e)}")
        raise


async def preview_changes():
    """Preview what changes will be made without updating"""
    
    db_manager.initialize()
    properties_collection = db_manager.get_collection("properties")
    
    try:
        logger.info("🔍 Previewing property type changes...")
        
        changes = []
        unknown_types = set()
        valid_count = 0
        
        cursor = properties_collection.find({})
        
        async for property_doc in cursor:
            current_type = property_doc.get("type", "").strip()
            
            if not current_type:
                continue
            
            # Skip if already valid
            if current_type in VALID_PROPERTY_TYPES:
                valid_count += 1
                continue
            
            current_type_lower = current_type.lower()
            
            if current_type_lower in PROPERTY_TYPE_MAPPING:
                new_type = PROPERTY_TYPE_MAPPING[current_type_lower]
                changes.append((current_type, new_type))
            else:
                unknown_types.add(current_type)
        
        logger.info(f"\n📊 Preview Results:")
        logger.info(f"   ✅ Already valid: {valid_count}")
        logger.info(f"   🔄 Will be updated: {len(changes)}")
        logger.info(f"   ❓ Unknown types: {len(unknown_types)}")
        
        if changes:
            logger.info("\nSample changes:")
            for old, new in list(set(changes))[:10]:
                count = changes.count((old, new))
                logger.info(f"   '{old}' → '{new}' ({count} properties)")
        
        if unknown_types:
            logger.info(f"\n⚠️  Unknown types found:")
            for unknown_type in sorted(unknown_types):
                count = await properties_collection.count_documents({"type": unknown_type})
                logger.info(f"   - '{unknown_type}' ({count} properties)")
        
    except Exception as e:
        logger.error(f"❌ Error during preview: {str(e)}")
        raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--preview":
        # Preview mode
        asyncio.run(preview_changes())
    else:
        # Actual normalization
        print("\n⚠️  This will update property types in the database.")
        print("Run with --preview to see changes first.\n")
        
        confirm = input("Continue? (yes/no): ")
        if confirm.lower() in ["yes", "y"]:
            asyncio.run(normalize_property_types())
        else:
            print("❌ Cancelled")

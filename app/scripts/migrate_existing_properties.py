#!/usr/bin/env python3
"""
Script to migrate existing properties to support the new listing_type and pricing structure.
This ensures backward compatibility with existing rental properties.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import property_collection

async def migrate_existing_properties():
    """
    Migrate existing properties to include listing_type and separate pricing fields.
    - Sets listing_type to 'rent' for all existing properties
    - Copies existing 'price' to 'rental_price'
    - Sets 'sale_price' to None
    """
    print("Starting migration of existing properties...")
    
    # Find all properties without listing_type field
    properties_to_migrate = []
    async for property_doc in property_collection.find({"listing_type": {"$exists": False}}):
        properties_to_migrate.append(property_doc)
    
    print(f"Found {len(properties_to_migrate)} properties to migrate")
    
    if not properties_to_migrate:
        print("No properties need migration")
        return
    
    # Migrate each property
    migrated_count = 0
    for property_doc in properties_to_migrate:
        try:
            # Update the property with new fields
            update_result = await property_collection.update_one(
                {"_id": property_doc["_id"]},
                {
                    "$set": {
                        "listing_type": "rent",  # Default to rent for existing properties
                        "rental_price": property_doc.get("price", 0),  # Copy existing price to rental_price
                        "sale_price": None,  # Set sale_price to None for existing properties
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if update_result.modified_count > 0:
                migrated_count += 1
                print(f"✓ Migrated property: {property_doc.get('title', 'Unknown')} (ID: {property_doc['_id']})")
            else:
                print(f"✗ Failed to migrate property: {property_doc.get('title', 'Unknown')} (ID: {property_doc['_id']})")
                
        except Exception as e:
            print(f"✗ Error migrating property {property_doc['_id']}: {str(e)}")
    
    print(f"\nMigration completed successfully!")
    print(f"Migrated {migrated_count} out of {len(properties_to_migrate)} properties")

async def verify_migration():
    """
    Verify that the migration was successful by checking the data consistency.
    """
    print("\nVerifying migration...")
    
    # Count properties with and without listing_type
    total_properties = await property_collection.count_documents({})
    properties_with_listing_type = await property_collection.count_documents({"listing_type": {"$exists": True}})
    properties_without_listing_type = await property_collection.count_documents({"listing_type": {"$exists": False}})
    
    print(f"Total properties: {total_properties}")
    print(f"Properties with listing_type: {properties_with_listing_type}")
    print(f"Properties without listing_type: {properties_without_listing_type}")
    
    # Check rental properties
    rental_properties = await property_collection.count_documents({"listing_type": "rent"})
    sale_properties = await property_collection.count_documents({"listing_type": "sale"})
    
    print(f"Rental properties: {rental_properties}")
    print(f"Sale properties: {sale_properties}")
    
    if properties_without_listing_type == 0:
        print("✓ Migration verification successful - All properties have listing_type field")
    else:
        print(f"✗ Migration verification failed - {properties_without_listing_type} properties still missing listing_type")

if __name__ == "__main__":
    print("Property Migration Script")
    print("=" * 50)
    
    # Run migration
    asyncio.run(migrate_existing_properties())
    
    # Verify migration
    asyncio.run(verify_migration())
    
    print("\nMigration script completed!") 
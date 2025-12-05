"""
Migration script to add SEO-friendly slugs to existing properties
Run this after deploying the slug field changes
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.utils.slug import generate_property_slug


async def migrate_property_slugs():
    """Add slugs to existing properties that don't have them"""
    
    try:
        # Connect to MongoDB
        print("Connecting to MongoDB...")
        client = AsyncIOMotorClient(settings.MONGO_URL)
        db = client.Houzdey  # Database name is "Houzdey" (capital H)
        properties_collection = db["properties"]
        
        # Find properties without slugs
        print("\nFinding properties without slugs...")
        properties = await properties_collection.find({
            "$or": [
                {"slug": {"$exists": False}},
                {"slug": None},
                {"slug": ""}
            ]
        }).to_list(None)
        
        total = len(properties)
        print(f"Found {total} properties without slugs\n")
        
        if total == 0:
            print("No properties need migration!")
            return
        
        # Confirm before proceeding
        response = input(f"Proceed with updating {total} properties? (yes/no): ")
        if response.lower() != "yes":
            print("Migration cancelled")
            return
        
        # Migrate each property
        successful = 0
        failed = 0
        
        for index, prop in enumerate(properties, 1):
            try:
                property_id = str(prop["_id"])
                
                # Generate slug
                slug = generate_property_slug(
                    listing_type=prop.get("listing_type", "rent"),
                    beds=prop.get("beds", 0),
                    property_type=prop.get("type", "property"),
                    lga=prop.get("lga", "unknown"),
                    state=prop.get("state", "unknown"),
                    property_id=property_id
                )
                
                # Update property
                result = await properties_collection.update_one(
                    {"_id": prop["_id"]},
                    {"$set": {"slug": slug}}
                )
                
                if result.modified_count > 0:
                    successful += 1
                    print(f"[{index}/{total}] ✓ {prop.get('title', 'Untitled')[:50]}")
                    print(f"         Slug: {slug}")
                else:
                    failed += 1
                    print(f"[{index}/{total}] ✗ Failed to update {property_id}")
                    
            except Exception as e:
                failed += 1
                print(f"[{index}/{total}] ✗ Error: {str(e)}")
        
        # Summary
        print(f"\n{'='*60}")
        print("MIGRATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total properties: {total}")
        print(f"✓ Successful: {successful}")
        print(f"✗ Failed: {failed}")
        print(f"Success rate: {(successful/total*100):.1f}%")
        print(f"{'='*60}\n")
        
        # Close connection
        client.close()
        print("Migration complete!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        sys.exit(1)


async def verify_slugs():
    """Verify that all properties have valid slugs"""
    
    try:
        # Connect to MongoDB
        print("Connecting to MongoDB...")
        client = AsyncIOMotorClient(settings.MONGO_URL)
        db = client.Houzdey  # Database name is "Houzdey" (capital H)
        properties_collection = db["properties"]
        
        # Count total properties
        total = await properties_collection.count_documents({})
        
        # Count properties with slugs
        with_slugs = await properties_collection.count_documents({
            "slug": {"$exists": True, "$ne": None, "$ne": ""}
        })
        
        # Count properties without slugs
        without_slugs = await properties_collection.count_documents({
            "$or": [
                {"slug": {"$exists": False}},
                {"slug": None},
                {"slug": ""}
            ]
        })
        
        print(f"\n{'='*60}")
        print("SLUG VERIFICATION")
        print(f"{'='*60}")
        print(f"Total properties: {total}")
        print(f"✓ With slugs: {with_slugs}")
        print(f"✗ Without slugs: {without_slugs}")
        
        if total > 0:
            print(f"Coverage: {(with_slugs/total*100):.1f}%")
        else:
            print(f"Coverage: N/A (no properties in database)")
        
        print(f"{'='*60}\n")
        
        if without_slugs > 0:
            print(f"⚠️  {without_slugs} properties still need slugs")
            print("Run: python scripts/migrate_property_slugs.py --migrate")
        else:
            print("✅ All properties have slugs!")
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Verification failed: {str(e)}")
        sys.exit(1)


async def show_sample_slugs():
    """Show sample of generated slugs"""
    
    try:
        # Connect to MongoDB
        print("Connecting to MongoDB...")
        client = AsyncIOMotorClient(settings.MONGO_URL)
        db = client.Houzdey  # Database name is "Houzdey" (capital H)
        properties_collection = db["properties"]
        
        # Get sample properties with slugs
        properties = await properties_collection.find({
            "slug": {"$exists": True, "$ne": None}
        }).limit(10).to_list(10)
        
        if not properties:
            print("No properties with slugs found")
            return
        
        print(f"\n{'='*60}")
        print("SAMPLE SEO-FRIENDLY URLS")
        print(f"{'='*60}\n")
        
        for prop in properties:
            title = prop.get("title", "Untitled")[:50]
            slug = prop.get("slug", "")
            url = f"https://houzdey.com/properties/{slug}"
            
            print(f"Title: {title}")
            print(f"URL:   {url}")
            print()
        
        print(f"{'='*60}\n")
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Failed to show samples: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate properties to SEO-friendly slugs")
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Run the migration to add slugs"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify slug coverage"
    )
    parser.add_argument(
        "--samples",
        action="store_true",
        help="Show sample URLs"
    )
    
    args = parser.parse_args()
    
    if args.migrate:
        asyncio.run(migrate_property_slugs())
    elif args.verify:
        asyncio.run(verify_slugs())
    elif args.samples:
        asyncio.run(show_sample_slugs())
    else:
        print("Usage:")
        print("  python scripts/migrate_property_slugs.py --migrate   # Run migration")
        print("  python scripts/migrate_property_slugs.py --verify    # Check coverage")
        print("  python scripts/migrate_property_slugs.py --samples   # Show sample URLs")

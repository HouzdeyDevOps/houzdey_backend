#!/usr/bin/env python3
"""
Script to migrate existing users to include the new role field.
This ensures backward compatibility with existing user accounts.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import db_manager
from app.models.user import UserRole

async def migrate_user_roles():
    """
    Migrate existing users to have the new USER role
    """
    user_collection = db_manager.get_collection("users")
    Migrate existing users to include role field.
    - Sets role to 'user' for all existing users without role field
    - Optionally sets first user as super_admin
    """
    print("Starting migration of user roles...")
    
    # Find all users without role field
    users_to_migrate = []
    async for user_doc in user_collection.find({"role": {"$exists": False}}):
        users_to_migrate.append(user_doc)
    
    print(f"Found {len(users_to_migrate)} users to migrate")
    
    if not users_to_migrate:
        print("No users need migration")
        return
    
    # Migrate each user
    migrated_count = 0
    first_user = True
    
    for user_doc in users_to_migrate:
        try:
            # Set role based on user (first user becomes super_admin)
            role = UserRole.SUPER_ADMIN if first_user else UserRole.USER
            
            # Update the user with new role field
            update_result = await user_collection.update_one(
                {"_id": user_doc["_id"]},
                {
                    "$set": {
                        "role": role,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if update_result.modified_count > 0:
                migrated_count += 1
                role_text = "super_admin" if first_user else "user"
                print(f"✓ Migrated user: {user_doc.get('email', 'Unknown')} (Role: {role_text})")
                first_user = False
            else:
                print(f"✗ Failed to migrate user: {user_doc.get('email', 'Unknown')}")
                
        except Exception as e:
            print(f"✗ Error migrating user {user_doc.get('email', 'Unknown')}: {str(e)}")
    
    print(f"\nMigration completed successfully!")
    print(f"Migrated {migrated_count} out of {len(users_to_migrate)} users")

async def verify_migration():
    """
    Verify that the migration was successful by checking the role distribution.
    """
    print("\nVerifying migration...")
    
    # Count users with and without role
    total_users = await user_collection.count_documents({})
    users_with_role = await user_collection.count_documents({"role": {"$exists": True}})
    users_without_role = await user_collection.count_documents({"role": {"$exists": False}})
    
    print(f"Total users: {total_users}")
    print(f"Users with role: {users_with_role}")
    print(f"Users without role: {users_without_role}")
    
    # Check role distribution
    user_roles = await user_collection.count_documents({"role": UserRole.USER})
    admin_roles = await user_collection.count_documents({"role": UserRole.ADMIN})
    super_admin_roles = await user_collection.count_documents({"role": UserRole.SUPER_ADMIN})
    
    print(f"Users: {user_roles}")
    print(f"Admins: {admin_roles}")
    print(f"Super Admins: {super_admin_roles}")
    
    if users_without_role == 0:
        print("✓ Migration verification successful - All users have role field")
    else:
        print(f"✗ Migration verification failed - {users_without_role} users still missing role field")

async def create_admin_user():
    """
    Create a default admin user if no super admin exists.
    """
    # Check if any super admin exists
    super_admin_count = await user_collection.count_documents({"role": UserRole.SUPER_ADMIN})
    
    if super_admin_count == 0:
        print("\nNo super admin found. Creating default admin user...")
        
        # You would typically create a proper admin user here
        # For now, just promote the first user to super admin
        first_user = await user_collection.find_one({})
        if first_user:
            await user_collection.update_one(
                {"_id": first_user["_id"]},
                {"$set": {"role": UserRole.SUPER_ADMIN, "updated_at": datetime.utcnow()}}
            )
            print(f"✓ Promoted {first_user.get('email', 'Unknown')} to super admin")
        else:
            print("✗ No users found to promote to super admin")
    else:
        print(f"\n✓ Found {super_admin_count} super admin(s)")

if __name__ == "__main__":
    print("User Role Migration Script")
    print("=" * 50)
    
    # Run migration
    asyncio.run(migrate_user_roles())
    
    # Verify migration
    asyncio.run(verify_migration())
    
    # Ensure admin user exists
    asyncio.run(create_admin_user())
    
    print("\nMigration script completed!")
    print("You can now access the admin panel at /admin")
    print("Make sure the first user has super_admin role to access all features.") 
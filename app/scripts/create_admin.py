#!/usr/bin/env python3
"""
Script to create admin users and check current user status.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import getpass

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import db_manager
from app.models.user import UserRole, UserStatus
from app.core.security import get_password_hash

async def check_users():
    user_collection = db_manager.get_collection("users")
    """Check current users and their roles"""
    print("Current User Status:")
    print("=" * 50)
    
    total_users = await user_collection.count_documents({})
    print(f"Total users: {total_users}")
    
    if total_users == 0:
        print("No users found in the database.")
        return False
    
    # Check role distribution
    user_roles = await user_collection.count_documents({"role": UserRole.USER})
    admin_roles = await user_collection.count_documents({"role": UserRole.ADMIN})
    super_admin_roles = await user_collection.count_documents({"role": UserRole.SUPER_ADMIN})
    
    print(f"Regular Users: {user_roles}")
    print(f"Admins: {admin_roles}")
    print(f"Super Admins: {super_admin_roles}")
    
    # List all users
    print("\nExisting Users:")
    print("-" * 50)
    async for user in user_collection.find({}).sort("created_at", 1):
        role = user.get("role", "No role")
        status = user.get("status", "Unknown")
        print(f"Email: {user.get('email', 'Unknown')}")
        print(f"Name: {user.get('first_name', '')} {user.get('last_name', '')}")
        print(f"Role: {role}")
        print(f"Status: {status}")
        print("-" * 30)
    
    return super_admin_roles > 0

async def promote_user_to_admin():
    """Promote an existing user to admin"""
    print("\nPromote Existing User to Admin")
    print("=" * 50)
    
    # List all non-admin users
    users = []
    async for user in user_collection.find({"role": {"$ne": UserRole.SUPER_ADMIN}}):
        users.append(user)
    
    if not users:
        print("No users available to promote.")
        return False
    
    print("Available users to promote:")
    for i, user in enumerate(users, 1):
        print(f"{i}. {user.get('email', 'Unknown')} ({user.get('first_name', '')} {user.get('last_name', '')})")
    
    try:
        choice = int(input("\nEnter user number to promote to Super Admin: ")) - 1
        if 0 <= choice < len(users):
            selected_user = users[choice]
            
            # Update user role
            await user_collection.update_one(
                {"_id": selected_user["_id"]},
                {
                    "$set": {
                        "role": UserRole.SUPER_ADMIN,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            print(f"✓ Successfully promoted {selected_user.get('email')} to Super Admin!")
            return True
        else:
            print("Invalid selection.")
            return False
    except (ValueError, KeyboardInterrupt):
        print("Operation cancelled.")
        return False

async def create_new_admin():
    """Create a new admin user"""
    print("\nCreate New Admin User")
    print("=" * 50)
    
    try:
        email = input("Enter admin email: ")
        first_name = input("Enter first name: ")
        last_name = input("Enter last name: ")
        password = getpass.getpass("Enter password: ")
        
        # Check if user already exists
        existing_user = await user_collection.find_one({"email": email})
        if existing_user:
            print(f"User with email {email} already exists!")
            return False
        
        # Create new admin user
        admin_user = {
            "email": email,
            "password": get_password_hash(password),
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": None,
            "phone_verified": False,
            "date_of_birth": None,
            "email_verified": True,  # Auto-verify admin
            "verification_code": None,
            "code_expiry": None,
            "reset_code": None,
            "reset_code_expiry": None,
            "status": UserStatus.VERIFIED,  # Auto-verify admin
            "role": UserRole.SUPER_ADMIN,
            "is_active": True,
            "plan": "Admin",
            "profile_picture": "",
            "google_id": None,
            "facebook_id": None,
            "apple_id": None,
            "wishlist": [],
            "bio": "System Administrator",
            "company": "Houzdey",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await user_collection.insert_one(admin_user)
        
        if result.inserted_id:
            print(f"✓ Successfully created admin user: {email}")
            print("Admin user is auto-verified and can access the admin panel immediately.")
            return True
        else:
            print("Failed to create admin user.")
            return False
            
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return False
    except Exception as e:
        print(f"Error creating admin user: {e}")
        return False

async def main():
    print("Houzdey Admin User Management")
    print("=" * 50)
    
    # Check current status
    has_admin = await check_users()
    
    if has_admin:
        print("\n✓ You already have admin users!")
        print("You can access the admin panel at: http://localhost:3000/admin")
        return
    
    print("\n❌ No admin users found!")
    print("\nOptions:")
    print("1. Promote existing user to admin")
    print("2. Create new admin user")
    print("3. Exit")
    
    try:
        choice = input("\nChoose an option (1-3): ")
        
        if choice == "1":
            success = await promote_user_to_admin()
        elif choice == "2":
            success = await create_new_admin()
        elif choice == "3":
            print("Goodbye!")
            return
        else:
            print("Invalid choice.")
            return
        
        if success:
            print("\n" + "=" * 50)
            print("🎉 Admin setup complete!")
            print("You can now access the admin panel at:")
            print("http://localhost:3000/admin")
            print("=" * 50)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled.")

if __name__ == "__main__":
    asyncio.run(main()) 
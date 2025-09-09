# scripts/create_initial_admin.py
import asyncio
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.session import create_db_and_tables, get_db_session
from app.services.admin_service import AdminService
from app.services.user_service import UserService

async def create_initial_admin():
    """Create the initial super admin user."""
    print("Creating initial admin setup...")
    
    # This would be run manually to create the first admin
    # You would need to provide the user ID of the first admin
    
    user_id = input("Enter the internal user ID for the first admin: ").strip()
    
    if not user_id:
        print("User ID is required")
        return
    
    async with get_db_session() as db:
        admin_service = AdminService(db)
        user_service = UserService(db)
        
        # Check if user exists
        user = await user_service.get_user_by_id(user_id)
        if not user:
            print(f"User with ID {user_id} not found")
            return
        
        # Check if already an admin
        existing_admin = await admin_service.get_admin_by_user_id(user_id)
        if existing_admin:
            print("User is already an admin")
            return
        
        # Create super admin
        admin_data = {
            "user_id": user_id,
            "role": "super_admin",
            "permissions": ["view_users", "edit_users", "delete_users", "view_analytics", "manage_system"]
        }
        
        try:
            admin = await admin_service.create_admin_user(admin_data)
            print(f"Successfully created super admin: {admin.id}")
            print(f"User: {user.email}")
            print("Permissions: ALL")
            
        except Exception as e:
            print(f"Error creating admin: {str(e)}")

if __name__ == "__main__":
    asyncio.run(create_initial_admin())
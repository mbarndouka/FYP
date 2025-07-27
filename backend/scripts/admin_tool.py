"""
Script to create an admin user for the application.
Run this script after setting up the database to create your first admin user.
"""

import asyncio
import sys
import os
from sqlalchemy.orm import Session

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.config import get_db, SessionLocal
from app.models.user import User, UserRole
from app.schemas.auth import UserCreate
from app.services.auth_service import auth_service


async def create_admin_user():
    """Create an admin user"""
    
    # Get user input
    email = input("Enter admin email: ").strip()
    password = input("Enter admin password: ").strip()
    full_name = input("Enter admin full name: ").strip()
    
    if not email or not password:
        print("Email and password are required!")
        return
    
    # Create user data
    admin_data = UserCreate(
        email=email,
        password=password,
        full_name=full_name,
        role=UserRole.ADMIN,
        department="Administration"
    )
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"User with email {email} already exists!")
            return
        
        # Create the admin user
        result = await auth_service.sign_up(admin_data, db)
        
        print(f"✅ Admin user created successfully!")
        print(f"Email: {email}")
        print(f"Role: {UserRole.ADMIN.value}")
        print(f"User ID: {result['db_user'].id}")
        
        # Note: The user will need to verify their email with Supabase
        print("\n⚠️  Note: The user may need to verify their email address through Supabase.")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
    finally:
        db.close()


async def list_users():
    """List all users in the system"""
    db = SessionLocal()
    
    try:
        users = db.query(User).all()
        
        if not users:
            print("No users found in the system.")
            return
        
        print("\n📋 Users in the system:")
        print("-" * 80)
        print(f"{'Email':<30} {'Role':<20} {'Name':<25} {'Active':<8}")
        print("-" * 80)
        
        for user in users:
            active_status = "Yes" if user.is_active else "No"
            print(f"{user.email:<30} {user.role.value:<20} {user.full_name or 'N/A':<25} {active_status:<8}")
        
        print("-" * 80)
        print(f"Total users: {len(users)}")
        
    except Exception as e:
        print(f"❌ Error listing users: {str(e)}")
    finally:
        db.close()


async def update_user_role():
    """Update a user's role"""
    email = input("Enter user email to update: ").strip()
    
    if not email:
        print("Email is required!")
        return
    
    print("\nAvailable roles:")
    for i, role in enumerate(UserRole, 1):
        print(f"{i}. {role.value}")
    
    try:
        role_choice = int(input("\nSelect role number: ")) - 1
        roles = list(UserRole)
        
        if role_choice < 0 or role_choice >= len(roles):
            print("Invalid role selection!")
            return
        
        new_role = roles[role_choice]
        
    except ValueError:
        print("Invalid input! Please enter a number.")
        return
    
    db = SessionLocal()
    
    try:
        # Find user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"User with email {email} not found!")
            return
        
        # Update role
        old_role = user.role
        updated_user = await auth_service.update_user_role(user.id, new_role, db)
        
        if updated_user:
            print(f"✅ User role updated successfully!")
            print(f"Email: {email}")
            print(f"Old role: {old_role.value}")
            print(f"New role: {new_role.value}")
        else:
            print("❌ Failed to update user role.")
        
    except Exception as e:
        print(f"❌ Error updating user role: {str(e)}")
    finally:
        db.close()


async def main():
    """Main function to run the admin script"""
    
    print("🔧 FastAPI Supabase Admin Tool")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Create admin user")
        print("2. List all users")
        print("3. Update user role")
        print("4. Exit")
        
        choice = input("\nSelect an option (1-4): ").strip()
        
        if choice == "1":
            await create_admin_user()
        elif choice == "2":
            await list_users()
        elif choice == "3":
            await update_user_role()
        elif choice == "4":
            print("👋 Goodbye!")
            break
        else:
            print("Invalid choice! Please select 1-4.")


if __name__ == "__main__":
    print("Starting admin tool...")
    
    # Check if we can import the required modules
    try:
        from app.database.config import SessionLocal
        print("✅ Database connection available")
    except ImportError as e:
        print(f"❌ Error importing modules: {e}")
        print("Make sure you're running this from the project root directory.")
        sys.exit(1)
    
    # Run the main function
    asyncio.run(main())

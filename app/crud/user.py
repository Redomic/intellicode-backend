from typing import Optional, List
from datetime import datetime
from arango.database import StandardDatabase

from app.models.user import UserCreate, UserInDB, UserUpdate
from app.core.security import get_password_hash, verify_password

class UserCRUD:
    """User database operations."""
    
    def __init__(self, db: StandardDatabase):
        self.db = db
        self.collection = db.collection('users')
    
    def create_user(self, user: UserCreate) -> UserInDB:
        """Create a new user account."""
        now = datetime.utcnow()
        user_data = {
            "email": user.email,
            "name": user.name,
            "hashed_password": get_password_hash(user.password),
            "is_active": user.is_active,
            "created_at": now.isoformat(),
            "onboarding_completed": False
        }
        
        result = self.collection.insert(user_data, return_new=True)
        # The result['new'] already contains _key, _id, _rev and our data
        new_user_data = result['new'].copy()
        new_user_data['created_at'] = now  # Use datetime object, not string
        return UserInDB(**new_user_data)
    
    def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Retrieve user by email address."""
        cursor = self.db.aql.execute(
            "FOR user IN users FILTER user.email == @email RETURN user",
            bind_vars={'email': email}
        )
        
        users = list(cursor)
        if users:
            user_data = users[0].copy()
            
            # Ensure active_course field exists (for backward compatibility)
            if 'active_course' not in user_data:
                user_data['active_course'] = None
            
            # Convert datetime strings to datetime objects
            if 'created_at' in user_data and isinstance(user_data['created_at'], str):
                user_data['created_at'] = datetime.fromisoformat(user_data['created_at'].replace('Z', '+00:00'))
            if 'updated_at' in user_data and isinstance(user_data['updated_at'], str):
                user_data['updated_at'] = datetime.fromisoformat(user_data['updated_at'].replace('Z', '+00:00'))
                
            return UserInDB(**user_data)
        return None
    
    def get_user_by_key(self, key: str) -> Optional[UserInDB]:
        """Retrieve user by document key."""
        try:
            user_data = self.collection.get(key)
            if user_data:
                user_data = user_data.copy()
                # The _key should already be in the document, but ensure it's set
                user_data['_key'] = key
                
                # Ensure active_course field exists (for backward compatibility)
                if 'active_course' not in user_data:
                    user_data['active_course'] = None
                
                # Convert datetime strings to datetime objects
                if 'created_at' in user_data and isinstance(user_data['created_at'], str):
                    user_data['created_at'] = datetime.fromisoformat(user_data['created_at'].replace('Z', '+00:00'))
                if 'updated_at' in user_data and isinstance(user_data['updated_at'], str):
                    user_data['updated_at'] = datetime.fromisoformat(user_data['updated_at'].replace('Z', '+00:00'))
                    
                return UserInDB(**user_data)
            return None
        except Exception:
            return None
    
    def authenticate_user(self, email: str, password: str) -> Optional[UserInDB]:
        """Verify user credentials and return user if valid."""
        user = self.get_user_by_email(email)
        
        if not user or not verify_password(password, user.hashed_password):
            return None
            
        return user
    
    def update_user(self, key: str, user_update: UserUpdate) -> Optional[UserInDB]:
        """Update user information."""
        now = datetime.utcnow()
        update_data = {"updated_at": now.isoformat()}
        
        # Only update provided fields
        if user_update.email:
            update_data['email'] = user_update.email
        if user_update.name:
            update_data['name'] = user_update.name
        if user_update.password:
            update_data['hashed_password'] = get_password_hash(user_update.password)
        if user_update.is_active is not None:
            update_data['is_active'] = user_update.is_active
        
        result = self.collection.update(key, update_data, return_new=True)
        if result:
            # Handle datetime conversion
            updated_user_data = result['new'].copy()
            updated_user_data['updated_at'] = now  # Use datetime object, not string
            
            # Convert created_at if it's a string
            if 'created_at' in updated_user_data and isinstance(updated_user_data['created_at'], str):
                updated_user_data['created_at'] = datetime.fromisoformat(updated_user_data['created_at'].replace('Z', '+00:00'))
                
            return UserInDB(**updated_user_data)
        return None
    
    def complete_onboarding(self, key: str, expertise_rank: int, skill_level: str, onboarding_data: dict = None) -> Optional[UserInDB]:
        """Mark user onboarding as completed and update related fields."""
        now = datetime.utcnow()
        update_data = {
            "updated_at": now.isoformat(),
            "onboarding_completed": True,
            "expertise_rank": expertise_rank,
            "initial_rank": expertise_rank,  # Store the initial rank from onboarding
            "skill_level": skill_level
        }
        
        if onboarding_data:
            update_data["onboarding_data"] = onboarding_data
        
        # Update peak rank if this is the first rank or higher than current
        user = self.get_user_by_key(key)
        if user and (not user.peak_rank or expertise_rank > user.peak_rank):
            update_data["peak_rank"] = expertise_rank
        
        try:
            update_document = {"_key": key}
            update_document.update(update_data)
            result = self.collection.update(update_document, return_new=True)
        except Exception as e:
            print(f"Error updating user {key}: {e}")
            return None
        if result:
            # Handle datetime conversion
            updated_user_data = result['new'].copy()
            updated_user_data['updated_at'] = now  # Use datetime object, not string
            
            # Convert created_at if it's a string
            if 'created_at' in updated_user_data and isinstance(updated_user_data['created_at'], str):
                updated_user_data['created_at'] = datetime.fromisoformat(updated_user_data['created_at'].replace('Z', '+00:00'))
                
            return UserInDB(**updated_user_data)
        return None
    
    def activate_course(self, user_key: str, course_id: str) -> Optional[UserInDB]:
        """Activate a course for a user."""
        now = datetime.utcnow()
        update_data = {
            "active_course": course_id,
            "updated_at": now.isoformat()
        }
        
        try:
            result = self.collection.update(user_key, update_data, return_new=True)
            if result:
                updated_user_data = result['new'].copy()
                updated_user_data['updated_at'] = now
                
                if 'created_at' in updated_user_data and isinstance(updated_user_data['created_at'], str):
                    updated_user_data['created_at'] = datetime.fromisoformat(
                        updated_user_data['created_at'].replace('Z', '+00:00')
                    )
                
                return UserInDB(**updated_user_data)
        except Exception as e:
            print(f"Error activating course for user {user_key}: {e}")
        
        return None
    
    def deactivate_course(self, user_key: str, course_id: str) -> Optional[UserInDB]:
        """Deactivate a course for a user."""
        user = self.get_user_by_key(user_key)
        if not user or user.active_course != course_id:
            return None
        
        now = datetime.utcnow()
        update_data = {
            "active_course": None,
            "updated_at": now.isoformat()
        }
        
        try:
            result = self.collection.update(user_key, update_data, return_new=True)
            if result:
                updated_user_data = result['new'].copy()
                updated_user_data['updated_at'] = now
                
                if 'created_at' in updated_user_data and isinstance(updated_user_data['created_at'], str):
                    updated_user_data['created_at'] = datetime.fromisoformat(
                        updated_user_data['created_at'].replace('Z', '+00:00')
                    )
                
                return UserInDB(**updated_user_data)
        except Exception as e:
            print(f"Error deactivating course for user {user_key}: {e}")
        
        return None
    
    def get_user_active_course(self, user_key: str) -> Optional[str]:
        """Get the active course for a user."""
        user = self.get_user_by_key(user_key)
        return user.active_course if user else None
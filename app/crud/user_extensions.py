from typing import Optional, List
from datetime import datetime
from arango.database import StandardDatabase

from app.models.user import UserInDB

class UserCourseExtensions:
    """Extension methods for user course activation management."""
    
    def __init__(self, db: StandardDatabase):
        self.db = db
        self.collection = db.collection('users')
    
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
    
    def activate_course(self, user_key: str, course_id: str) -> Optional[UserInDB]:
        """Activate a course for a user (only one course can be active at a time)."""
        user = self.get_user_by_key(user_key)
        if not user:
            return None
            
        now = datetime.utcnow()
        update_data = {
            "_key": user_key,
            "active_course": course_id,
            "updated_at": now.isoformat()
        }
        
        result = self.collection.update(update_data, return_new=True)
        if result:
            updated_user_data = result['new'].copy()
            updated_user_data['updated_at'] = now
            
            # Ensure active_course field exists
            if 'active_course' not in updated_user_data:
                updated_user_data['active_course'] = None
            
            # Convert created_at if it's a string
            if 'created_at' in updated_user_data and isinstance(updated_user_data['created_at'], str):
                updated_user_data['created_at'] = datetime.fromisoformat(updated_user_data['created_at'].replace('Z', '+00:00'))
                
            return UserInDB(**updated_user_data)
        return None
    
    def deactivate_course(self, user_key: str, course_id: str) -> Optional[UserInDB]:
        """Deactivate the currently active course for a user."""
        user = self.get_user_by_key(user_key)
        if not user:
            return None
        
        # Only deactivate if the specified course is currently active
        if user.active_course != course_id:
            return None
            
        now = datetime.utcnow()
        update_data = {
            "_key": user_key,
            "active_course": None,
            "updated_at": now.isoformat()
        }
        
        result = self.collection.update(update_data, return_new=True)
        if result:
            updated_user_data = result['new'].copy()
            updated_user_data['updated_at'] = now
            
            # Ensure active_course field exists
            if 'active_course' not in updated_user_data:
                updated_user_data['active_course'] = None
            
            # Convert created_at if it's a string
            if 'created_at' in updated_user_data and isinstance(updated_user_data['created_at'], str):
                updated_user_data['created_at'] = datetime.fromisoformat(updated_user_data['created_at'].replace('Z', '+00:00'))
                
            return UserInDB(**updated_user_data)
        return None
    
    def get_user_active_course(self, user_key: str) -> Optional[str]:
        """Get the currently active course for a user."""
        user = self.get_user_by_key(user_key)
        if user:
            return user.active_course
        return None

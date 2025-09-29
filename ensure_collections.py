#!/usr/bin/env python3
"""
Database Collection Setup Script

This script ensures all required collections exist in the database.
Run this if you're having issues with sessions not being saved.

Usage:
    python ensure_collections.py
"""

import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db.database import DatabaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Ensure all database collections exist."""
    print("🔧 Database Collection Setup")
    print("=" * 40)
    
    try:
        # Initialize database manager (this will create collections)
        db_manager = DatabaseManager()
        db = db_manager.get_database()
        
        print("\n📋 Checking collections...")
        
        # Only valid collections as per architecture requirements
        required_collections = [
            'users',         # User data
            'questions',     # All questions/problems
            'assessments',   # User assessments
            'roadmap',       # Roadmap questions (from A2Z, etc.)
            'sessions',      # Active coding sessions
            'submissions',   # Code submissions (LeetCode-style)
            'behavior'       # Behavior tracking data
        ]
        
        existing_collections = db.collections()
        existing_names = [col['name'] for col in existing_collections if not col['name'].startswith('_')]
        
        print(f"📊 Found {len(existing_names)} existing collections:")
        for name in sorted(existing_names):
            status = "✅" if name in required_collections else "ℹ️"
            print(f"   {status} {name}")
        
        print(f"\n🎯 Required collections status:")
        for name in required_collections:
            if name in existing_names:
                print(f"   ✅ {name} - EXISTS")
            else:
                print(f"   ❌ {name} - MISSING")
        
        # Count documents in key collections
        print(f"\n📈 Collection document counts:")
        key_collections = ['users', 'sessions', 'submissions', 'questions', 'roadmap']
        
        for coll_name in key_collections:
            if coll_name in existing_names:
                collection = db.collection(coll_name)
                count = collection.count()
                print(f"   📦 {coll_name}: {count} documents")
            else:
                print(f"   ❌ {coll_name}: Collection missing!")
        
        print("\n" + "=" * 40)
        print("✅ Database setup complete!")
        print("\nNext steps:")
        print("1. Restart your backend server")
        print("2. Try creating a session through the frontend")
        print("3. Check the server logs for session creation messages")
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure ArangoDB is running")
        print("2. Check your database configuration in app/core/config.py")
        print("3. Verify database credentials")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

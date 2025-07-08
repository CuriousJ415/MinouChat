#!/usr/bin/env python3
"""
Clear all user accounts from the database
"""
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from miachat.api.core.database import get_db, engine
from miachat.api.core.models import User
from sqlalchemy.orm import sessionmaker

def clear_all_users():
    """Clear all user accounts from the database"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Delete all users
        deleted_count = db.query(User).delete()
        db.commit()
        print(f"✅ Successfully deleted {deleted_count} user accounts")
        
        # Verify deletion
        remaining_users = db.query(User).count()
        print(f"📊 Remaining users in database: {remaining_users}")
        
    except Exception as e:
        print(f"❌ Error clearing users: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🗑️  Clearing all user accounts...")
    clear_all_users()
    print("✅ Database cleared!") 
#!/usr/bin/env python3
"""
Debug script for database creation.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent / "src"))

def debug_database():
    """Debug database creation."""
    print("Debugging database creation...")
    
    try:
        from miachat.database.config import db_config
        from miachat.database.models import Base
        
        print(f"Database URL: {db_config.database_url}")
        print(f"Database file path: {Path(db_config.database_url.replace('sqlite:///', ''))}")
        
        # Check if the file exists
        db_path = Path(db_config.database_url.replace('sqlite:///', ''))
        print(f"Database file exists: {db_path.exists()}")
        if db_path.exists():
            print(f"Database file size: {db_path.stat().st_size} bytes")
        
        # Try to create tables
        print("Creating tables...")
        Base.metadata.create_all(bind=db_config.engine)
        print("Tables created!")
        
        # Check file size again
        if db_path.exists():
            print(f"Database file size after creation: {db_path.stat().st_size} bytes")
        
        # Try to connect and query
        with db_config.get_session() as session:
            from sqlalchemy import text
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
            print(f"Tables in database: {tables}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_database() 
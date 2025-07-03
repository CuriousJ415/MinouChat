"""
Database initialization script for MiaChat.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from miachat.database.config import db_config
from miachat.database.models import Base
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database with all required tables."""
    try:
        logger.info("Initializing MiaChat database...")
        
        # Create all tables
        db_config.create_tables()
        
        logger.info("Database tables created successfully!")
        
        # Test database connection
        with db_config.get_session() as session:
            # Try a simple query to verify the connection
            session.execute(text("SELECT 1"))
            logger.info("Database connection test successful!")
        
        logger.info("Database initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

def create_default_personality():
    """Create a default personality record for the conversation system."""
    try:
        from miachat.database.models import Personality
        
        with db_config.get_session() as session:
            # Check if default personality exists
            existing = session.query(Personality).filter(Personality.id == 1).first()
            if existing:
                logger.info("Default personality already exists")
                return True
            
            # Create default personality
            default_personality = Personality(
                id=1,
                name="Default",
                version="1.0",
                tone="neutral",
                vocabulary_level="standard",
                formality=0.5,
                humor_level=0.5
            )
            
            session.add(default_personality)
            session.commit()
            
            logger.info("Default personality created successfully!")
            return True
            
    except Exception as e:
        logger.error(f"Error creating default personality: {e}")
        return False

if __name__ == "__main__":
    print("MiaChat Database Initialization")
    print("=" * 40)
    
    if init_database():
        print("✓ Database tables created")
        
        if create_default_personality():
            print("✓ Default personality created")
        else:
            print("✗ Failed to create default personality")
            
        print("\nDatabase initialization completed!")
    else:
        print("✗ Database initialization failed!")
        sys.exit(1) 
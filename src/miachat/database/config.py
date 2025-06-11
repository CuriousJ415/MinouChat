"""
Database configuration and connection management.
"""

import os
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from .models import Base

class DatabaseConfig:
    """Database configuration manager."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database configuration.
        
        Args:
            database_url: Optional database URL. If not provided, will use environment variable
                         or default to SQLite.
        """
        self.database_url = database_url or os.getenv(
            'MIACHAT_DATABASE_URL',
            'sqlite:///miachat.db'
        )
        
        # Configure engine with connection pooling
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800  # Recycle connections after 30 minutes
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a database session.
        
        Returns:
            A new database session.
        """
        return self.SessionLocal()
    
    def init_db(self):
        """Initialize the database.
        
        This method:
        1. Creates all tables
        2. Sets up any initial data
        """
        self.create_tables()
        # TODO: Add any initial data setup here

# Global database configuration instance
db_config = DatabaseConfig()

def get_db():
    """Get a database session.
    
    Yields:
        A database session that will be automatically closed after use.
    """
    db = db_config.get_session()
    try:
        yield db
    finally:
        db.close() 
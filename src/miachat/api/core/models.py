"""
Database models for MiaChat API
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    """User model for authentication"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationship to settings
    settings = relationship("UserSettings", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

class UserSettings(Base):
    """User settings model for storing user preferences"""
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # LLM Provider Settings
    default_llm_provider = Column(String, default="ollama")
    default_model = Column(String, default="llama3:8b")
    privacy_mode = Column(String, default="local_only")  # local_only, cloud_allowed, hybrid
    
    # API Keys (encrypted in production)
    openai_api_key = Column(Text, nullable=True)
    anthropic_api_key = Column(Text, nullable=True)
    openrouter_api_key = Column(Text, nullable=True)
    
    # Provider-specific settings
    ollama_url = Column(String, default="http://localhost:11434")
    openai_model = Column(String, default="gpt-4")
    anthropic_model = Column(String, default="claude-3-opus-20240229")
    openrouter_model = Column(String, default="openai/gpt-4")
    
    # UI Preferences
    theme = Column(String, default="light")  # light, dark, auto
    language = Column(String, default="en")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to user
    user = relationship("User", back_populates="settings")

    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, provider='{self.default_llm_provider}')>" 

class CharacterVersion(BaseModel):
    """Represents a version of a character's persona"""
    character_id: str
    version: int
    system_prompt: str
    persona: str
    traits: Optional[Dict[str, float]] = None
    communication_style: Optional[Dict[str, float]] = None
    created_at: datetime
    is_active: bool = True
    change_reason: Optional[str] = None

class ConversationSession(BaseModel):
    """Represents an active conversation session"""
    session_id: str
    character_id: str
    character_version: int
    user_id: str
    started_at: datetime
    last_activity: datetime
    message_count: int = 0

class ChatMessage(BaseModel):
    """Represents a single chat message"""
    session_id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    character_version: int

class CharacterUpdateEvent(BaseModel):
    """Represents a character update event"""
    character_id: str
    old_version: int
    new_version: int
    updated_at: datetime
    changes: Dict[str, Any]  # What was changed
    migration_required: bool = False 
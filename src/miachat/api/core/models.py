"""
Database models for MiaChat API
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableDict
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

    # Relationship to settings and documents
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    documents = relationship('Document', back_populates='user', cascade='all, delete-orphan')

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

class Document(Base):
    """Enhanced document model with RAG capabilities."""
    __tablename__ = 'documents'

    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    doc_type = Column(String(50), nullable=False)  # pdf, docx, xlsx, txt, etc.
    file_size = Column(Integer, nullable=False)
    text_content = Column(Text)  # Extracted text content
    content_hash = Column(String(64))  # SHA-256 hash for deduplication
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed = Column(DateTime(timezone=True), server_default=func.now())
    access_count = Column(Integer, default=0)
    is_processed = Column(Integer, default=0)  # Boolean: 0=False, 1=True
    processing_status = Column(String(50), default='pending')  # pending, processing, completed, failed
    doc_metadata = Column(MutableDict.as_mutable(JSON), default=dict)

    # Relationships
    user = relationship('User', back_populates='documents')
    chunks = relationship('DocumentChunk', back_populates='document', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'doc_type': self.doc_type,
            'file_size': self.file_size,
            'upload_date': self.upload_date.isoformat(),
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'access_count': self.access_count,
            'is_processed': bool(self.is_processed),
            'processing_status': self.processing_status,
            'metadata': self.doc_metadata
        }

    def mark_accessed(self):
        """Update access tracking."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1

class DocumentChunk(Base):
    """Text chunks from documents with vector embeddings for RAG."""
    __tablename__ = 'document_chunks'

    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey('documents.id'), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Order within document
    text_content = Column(Text, nullable=False)
    chunk_type = Column(String(50), default='paragraph')  # paragraph, table, header, etc.
    start_char = Column(Integer)  # Character position in original document
    end_char = Column(Integer)
    word_count = Column(Integer)
    embedding_vector = Column(Text)  # JSON-serialized vector embedding
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    doc_metadata = Column(MutableDict.as_mutable(JSON), default=dict)

    # Relationships
    document = relationship('Document', back_populates='chunks')

    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'chunk_index': self.chunk_index,
            'text_content': self.text_content,
            'chunk_type': self.chunk_type,
            'start_char': self.start_char,
            'end_char': self.end_char,
            'word_count': self.word_count,
            'created_at': self.created_at.isoformat(),
            'metadata': self.doc_metadata
        } 
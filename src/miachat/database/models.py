"""
Database models for MiaChat.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Table, Text
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.mutable import MutableDict

Base = declarative_base()  # Re-added

# Association tables for many-to-many relationships
personality_trait = Table(
    'personality_trait',
    Base.metadata,
    Column('personality_id', Integer, ForeignKey('personalities.id')),
    Column('trait_id', Integer, ForeignKey('traits.id'))
)

personality_knowledge_domain = Table(
    'personality_knowledge_domain',
    Base.metadata,
    Column('personality_id', Integer, ForeignKey('personalities.id')),
    Column('domain_id', Integer, ForeignKey('knowledge_domains.id'))
)

personality_skill = Table(
    'personality_skill',
    Base.metadata,
    Column('personality_id', Integer, ForeignKey('personalities.id')),
    Column('skill_id', Integer, ForeignKey('skills.id'))
)

personality_interest = Table(
    'personality_interest',
    Base.metadata,
    Column('personality_id', Integer, ForeignKey('personalities.id')),
    Column('interest_id', Integer, ForeignKey('interests.id'))
)

class Personality(Base):
    """Personality model."""
    __tablename__ = 'personalities'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    version = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Style attributes
    tone = Column(String(50), nullable=False)
    vocabulary_level = Column(String(20), nullable=False)
    formality = Column(Float, nullable=False)
    humor_level = Column(Float, nullable=False)

    # Relationships
    traits = relationship('Trait', secondary=personality_trait, back_populates='personalities')
    knowledge_domains = relationship('KnowledgeDomain', secondary=personality_knowledge_domain, back_populates='personalities')
    skills = relationship('Skill', secondary=personality_skill, back_populates='personalities')
    interests = relationship('Interest', secondary=personality_interest, back_populates='personalities')
    backstory = relationship('Backstory', back_populates='personality', uselist=False)
    conversations = relationship('Conversation', back_populates='personality')

class Trait(Base):
    """Trait model."""
    __tablename__ = 'traits'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    value = Column(Float, nullable=False)
    description = Column(Text)

    personalities = relationship('Personality', secondary=personality_trait, back_populates='traits')

class KnowledgeDomain(Base):
    """Knowledge domain model."""
    __tablename__ = 'knowledge_domains'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)

    personalities = relationship('Personality', secondary=personality_knowledge_domain, back_populates='knowledge_domains')

class Skill(Base):
    """Skill model."""
    __tablename__ = 'skills'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)

    personalities = relationship('Personality', secondary=personality_skill, back_populates='skills')

class Interest(Base):
    """Interest model."""
    __tablename__ = 'interests'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)

    personalities = relationship('Personality', secondary=personality_interest, back_populates='interests')

class Backstory(Base):
    """Backstory model."""
    __tablename__ = 'backstories'

    id = Column(Integer, primary_key=True)
    personality_id = Column(Integer, ForeignKey('personalities.id'), nullable=False)
    background = Column(Text, nullable=False)
    experiences = Column(JSON, nullable=False)
    relationships = Column(JSON, nullable=False)
    goals = Column(JSON, nullable=False)

    personality = relationship('Personality', back_populates='backstory')

class Conversation(Base):
    """Conversation model."""
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True)
    personality_id = Column(Integer, ForeignKey('personalities.id'), nullable=False)
    title = Column(String, nullable=True)  # Optional conversation title
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)  # Added for consistency with chat.py
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Added for consistency with chat.py
    conversation_data = Column(MutableDict.as_mutable(JSON), default=dict)

    personality = relationship('Personality', back_populates='conversations')
    messages = relationship('Message', back_populates='conversation', order_by='Message.timestamp')

    @classmethod
    def create(cls, personality_id: int, metadata: Optional[dict] = None) -> 'Conversation':
        """Create a new conversation."""
        conversation = cls(
            personality_id=personality_id,
            conversation_data=metadata or {}
        )
        return conversation

    def end(self) -> None:
        """End the conversation."""
        self.ended_at = datetime.utcnow()

    def is_active(self) -> bool:
        """Check if the conversation is active."""
        return self.ended_at is None

    def get_messages(self, limit: Optional[int] = None) -> List['Message']:
        """Get conversation messages, optionally limited to the most recent ones."""
        messages = self.messages
        if limit:
            messages = messages[-limit:]
        return messages

class Message(Base):
    """Message model."""
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    file_attachments = Column(JSON, nullable=True)  # For document attachments (from chat.py)
    message_data = Column(MutableDict.as_mutable(JSON), default=dict)

    conversation = relationship('Conversation', back_populates='messages')

    @classmethod
    def create(
        cls,
        conversation_id: int,
        content: str,
        role: str,
        metadata: Optional[dict] = None
    ) -> 'Message':
        """Create a new message."""
        message = cls(
            conversation_id=conversation_id,
            content=content,
            role=role,
            message_data=metadata or {}
        )
        return message

    def to_dict(self) -> dict:
        """Convert message to dictionary format."""
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.message_data
        }

class User(Base):
    """User model for authentication."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(120), nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False)
    
    # Relationships
    documents = relationship('Document', back_populates='user', cascade='all, delete-orphan')
    settings = relationship('UserSettings', back_populates='user', cascade='all, delete-orphan', uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email
        }

class File(Base):
    """Model for file attachments."""
    __tablename__ = 'files'
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    url = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'url': self.url,
            'created_at': self.created_at.isoformat()
        }

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
    upload_date = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
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
    created_at = Column(DateTime, default=datetime.utcnow)
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

class UserSettings(Base):
    """User preferences and LLM provider configuration."""
    __tablename__ = 'user_settings'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)

    # LLM Provider Settings
    default_llm_provider = Column(String(50), default='ollama')
    default_model = Column(String(100), default='llama3:8b')
    privacy_mode = Column(String(20), default='local_only')

    # Provider-specific API settings
    ollama_url = Column(String(255), default='http://localhost:11434')
    openai_api_key = Column(String(255))
    openai_model = Column(String(100), default='gpt-4')
    anthropic_api_key = Column(String(255))
    anthropic_model = Column(String(100), default='claude-3-opus-20240229')
    openrouter_api_key = Column(String(255))
    openrouter_model = Column(String(100), default='openai/gpt-4')

    # UI/UX Preferences
    theme = Column(String(20), default='light')
    notifications_enabled = Column(Integer, default=1)  # Boolean: 0=False, 1=True

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', back_populates='settings')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'default_llm_provider': self.default_llm_provider,
            'default_model': self.default_model,
            'privacy_mode': self.privacy_mode,
            'ollama_url': self.ollama_url,
            'openai_model': self.openai_model,
            'anthropic_model': self.anthropic_model,
            'openrouter_model': self.openrouter_model,
            'theme': self.theme,
            'notifications_enabled': bool(self.notifications_enabled),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Reminder(Base):
    """Reminder model for personas."""
    __tablename__ = 'reminders'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    persona_name = Column(String(100), nullable=False)  # Reference to persona
    title = Column(String(200), nullable=False)
    description = Column(Text)
    reminder_time = Column(DateTime, nullable=False)
    is_recurring = Column(Integer, default=0)  # Boolean: 0=False, 1=True
    recurrence_pattern = Column(String(50))  # daily, weekly, monthly, yearly
    recurrence_interval = Column(Integer, default=1)  # Every N units
    recurrence_days = Column(String(20))  # For weekly: mon,tue,wed etc
    is_completed = Column(Integer, default=0)  # Boolean: 0=False, 1=True
    is_active = Column(Integer, default=1)  # Boolean: 0=False, 1=True
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    # Context awareness
    context_type = Column(String(50))  # meeting, task, event, birthday, etc.
    context_data = Column(MutableDict.as_mutable(JSON), default=dict)

    # Relationships
    user = relationship('User', backref='reminders')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'persona_name': self.persona_name,
            'title': self.title,
            'description': self.description,
            'reminder_time': self.reminder_time.isoformat(),
            'is_recurring': bool(self.is_recurring),
            'recurrence_pattern': self.recurrence_pattern,
            'recurrence_interval': self.recurrence_interval,
            'recurrence_days': self.recurrence_days,
            'is_completed': bool(self.is_completed),
            'is_active': bool(self.is_active),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'context_type': self.context_type,
            'context_data': self.context_data
        }

    def mark_completed(self):
        """Mark reminder as completed."""
        self.is_completed = 1
        self.completed_at = datetime.utcnow()

    def is_due(self, check_time: datetime = None) -> bool:
        """Check if reminder is due."""
        if not check_time:
            check_time = datetime.utcnow()
        return self.reminder_time <= check_time and not self.is_completed and self.is_active

class PersonaTimeContext(Base):
    """Time-aware context for personas."""
    __tablename__ = 'persona_time_context'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    persona_name = Column(String(100), nullable=False)

    # Timezone and locale settings
    timezone = Column(String(50), default='UTC')
    date_format = Column(String(20), default='%Y-%m-%d')
    time_format = Column(String(20), default='%H:%M:%S')

    # Schedule and availability
    work_schedule = Column(MutableDict.as_mutable(JSON), default=dict)  # {"monday": {"start": "09:00", "end": "17:00"}}
    availability_status = Column(String(20), default='available')  # available, busy, away

    # Important dates and events
    important_dates = Column(MutableDict.as_mutable(JSON), default=dict)
    recurring_events = Column(MutableDict.as_mutable(JSON), default=dict)

    # Behavioral patterns
    morning_routine_time = Column(String(10))  # e.g., "07:00"
    evening_routine_time = Column(String(10))  # e.g., "22:00"
    preferred_meeting_times = Column(MutableDict.as_mutable(JSON), default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', backref='persona_time_contexts')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'persona_name': self.persona_name,
            'timezone': self.timezone,
            'date_format': self.date_format,
            'time_format': self.time_format,
            'work_schedule': self.work_schedule,
            'availability_status': self.availability_status,
            'important_dates': self.important_dates,
            'recurring_events': self.recurring_events,
            'morning_routine_time': self.morning_routine_time,
            'evening_routine_time': self.evening_routine_time,
            'preferred_meeting_times': self.preferred_meeting_times,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


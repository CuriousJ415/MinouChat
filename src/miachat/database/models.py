"""
Database models for MiaChat.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Table, Text, UniqueConstraint
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
    personality_id = Column(Integer, ForeignKey('personalities.id'), nullable=True)
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
    clerk_id = Column(String(255), nullable=True, unique=True, index=True)  # Clerk user ID
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    documents = relationship('Document', back_populates='user', cascade='all, delete-orphan')
    settings = relationship('UserSettings', back_populates='user', cascade='all, delete-orphan', uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'clerk_id': self.clerk_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
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

    # Priority and RAG settings (for enhanced context management)
    priority = Column(Integer, default=100)  # Higher = more important in context selection
    always_include = Column(Integer, default=0)  # Boolean: always include in RAG context
    character_associations = Column(JSON, default=list)  # Character IDs this doc applies to
    
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

    # LLM Provider Settings (for chat with personas)
    default_llm_provider = Column(String(50), default='ollama')
    default_model = Column(String(100), default='llama3:8b')
    privacy_mode = Column(String(20), default='local_only')

    # Assistant LLM Settings (for app utility tasks like generating prompts)
    assistant_llm_provider = Column(String(50), default='ollama')
    assistant_llm_model = Column(String(100), default='llama3.1:8b')

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

    # Setup wizard tracking
    setup_completed = Column(Integer, default=0)  # Boolean: 1=user has completed setup wizard

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
            'assistant_llm_provider': self.assistant_llm_provider or 'ollama',
            'assistant_llm_model': self.assistant_llm_model or 'llama3.1:8b',
            'ollama_url': self.ollama_url,
            'openai_model': self.openai_model,
            'anthropic_model': self.anthropic_model,
            'openrouter_model': self.openrouter_model,
            'theme': self.theme,
            'notifications_enabled': bool(self.notifications_enabled),
            'setup_completed': bool(self.setup_completed),
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


class WorldInfoEntry(Base):
    """World Info / Lorebook entry for keyword-triggered context injection.

    Similar to KoboldCpp's World Info feature - when keywords in user messages
    match an entry's keywords, the entry's content is automatically injected
    into the context.
    """
    __tablename__ = 'world_info_entries'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    character_id = Column(String(36), nullable=True)  # NULL = global entry for all characters

    # Entry metadata
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # e.g., "lore", "technical", "character", "location"

    # Trigger configuration
    keywords = Column(JSON, nullable=False)  # ["keyword1", "keyword2"]
    regex_pattern = Column(String(500))  # Optional regex trigger pattern
    case_sensitive = Column(Integer, default=0)  # Boolean: 0=case insensitive
    match_whole_word = Column(Integer, default=1)  # Boolean: 1=whole word only

    # Content to inject
    content = Column(Text, nullable=False)

    # Priority and activation
    priority = Column(Integer, default=100)  # Higher = injected first when budget limited
    is_enabled = Column(Integer, default=1)  # Boolean
    insertion_order = Column(Integer, default=0)  # Position in prompt (0=before other context)

    # Token management
    token_count = Column(Integer)  # Cached token count for budget calculations
    max_tokens = Column(Integer)  # Optional per-entry token limit

    # Conditional activation (optional advanced features)
    activation_conditions = Column(MutableDict.as_mutable(JSON), default=dict)
    # e.g., {"min_messages": 5, "requires_character": "mia", "time_range": {...}}

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', backref='world_info_entries')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'character_id': self.character_id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'keywords': self.keywords,
            'regex_pattern': self.regex_pattern,
            'case_sensitive': bool(self.case_sensitive),
            'match_whole_word': bool(self.match_whole_word),
            'content': self.content,
            'priority': self.priority,
            'is_enabled': bool(self.is_enabled),
            'insertion_order': self.insertion_order,
            'token_count': self.token_count,
            'max_tokens': self.max_tokens,
            'activation_conditions': self.activation_conditions,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class PersistentMemory(Base):
    """User-configurable persistent memory for always-injected context.

    Similar to KoboldCpp's Memory feature - content that is always included
    in the prompt, regardless of keywords or conversation context.
    """
    __tablename__ = 'persistent_memories'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    character_id = Column(String(36), nullable=True)  # NULL = applies to all characters

    # Memory content
    name = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)

    # Configuration
    is_enabled = Column(Integer, default=1)  # Boolean
    priority = Column(Integer, default=100)  # Higher = injected first
    insertion_position = Column(String(50), default='before_conversation')
    # Options: 'start', 'after_system_prompt', 'before_conversation', 'before_user_message'

    # Token management
    token_count = Column(Integer)  # Cached token count
    max_tokens = Column(Integer)  # Optional token limit

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', backref='persistent_memories')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'character_id': self.character_id,
            'name': self.name,
            'content': self.content,
            'is_enabled': bool(self.is_enabled),
            'priority': self.priority,
            'insertion_position': self.insertion_position,
            'token_count': self.token_count,
            'max_tokens': self.max_tokens,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class BackstoryChunk(Base):
    """Semantic chunks of character backstory for retrieval.

    When a user saves backstory text for a character, it gets split into
    chunks and embedded for semantic search. During conversations, relevant
    backstory is retrieved based on context similarity.
    """
    __tablename__ = 'backstory_chunks'

    id = Column(Integer, primary_key=True)
    character_id = Column(String(36), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Chunk content
    chunk_index = Column(Integer, nullable=False)  # Order within the backstory
    text_content = Column(Text, nullable=False)

    # Embedding for semantic search
    embedding_vector = Column(Text)  # JSON-serialized vector

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship('User', backref='backstory_chunks')

    def to_dict(self):
        return {
            'id': self.id,
            'character_id': self.character_id,
            'user_id': self.user_id,
            'chunk_index': self.chunk_index,
            'text_content': self.text_content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ConversationFact(Base):
    """Facts automatically extracted from conversations.

    The system learns about the user through conversation and stores
    extracted facts here. These can be edited or deleted by the user
    and are used to provide personalized context.
    """
    __tablename__ = 'conversation_facts'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    character_id = Column(String(36), nullable=True, index=True)  # NULL = global fact

    # The fact itself
    fact_type = Column(String(50))  # 'preference', 'name', 'relationship', 'event', 'trait', 'other'
    fact_key = Column(String(100))  # e.g., "user_name", "favorite_color", "job_title"
    fact_value = Column(Text, nullable=False)

    # Source tracking
    source_conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=True)
    source_message_id = Column(Integer, nullable=True)
    confidence = Column(Float, default=1.0)  # How confident we are (0-1)

    # Management
    is_active = Column(Integer, default=1)  # Boolean - user can disable facts

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', backref='conversation_facts')
    source_conversation = relationship('Conversation', backref='extracted_facts')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'character_id': self.character_id,
            'fact_type': self.fact_type,
            'fact_key': self.fact_key,
            'fact_value': self.fact_value,
            'source_conversation_id': self.source_conversation_id,
            'confidence': self.confidence,
            'is_active': bool(self.is_active),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class GeneratedDocument(Base):
    """Documents generated by the LLM from conversations.

    These are documents like Research Summaries, Weekly Reviews, Action Plans,
    etc. that are created using LLM intelligence based on conversation context.
    """
    __tablename__ = 'generated_documents'

    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    character_id = Column(String(36), nullable=True, index=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=True)

    # Document info
    title = Column(String(255), nullable=False)
    document_type = Column(String(50), nullable=False)  # research_summary, weekly_review, etc.
    category = Column(String(50), nullable=False)  # Assistant, Coach, Teacher, Friend, Creative
    format = Column(String(10), nullable=False)  # pdf, docx, md, txt

    # File storage
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)

    # Content (store markdown version for quick preview)
    content_preview = Column(Text)  # First ~500 chars for preview
    content_markdown = Column(Text)  # Full markdown content

    # Generation context
    custom_instructions = Column(Text)  # User's custom instructions if any
    message_count = Column(Integer)  # Number of messages used to generate

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship('User', backref='generated_documents')
    conversation = relationship('Conversation', backref='generated_documents')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'character_id': self.character_id,
            'conversation_id': self.conversation_id,
            'title': self.title,
            'document_type': self.document_type,
            'category': self.category,
            'format': self.format,
            'filename': self.filename,
            'file_size': self.file_size,
            'content_preview': self.content_preview,
            'custom_instructions': self.custom_instructions,
            'message_count': self.message_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TodoItem(Base):
    """User todo items for sidebar tracking.

    Todo items can be manually created or extracted from conversation.
    Displayed in the sidebar for Assistant-category personas.
    """
    __tablename__ = 'todo_items'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    character_id = Column(String(36), nullable=False, index=True)

    # Task content
    text = Column(Text, nullable=False)
    is_completed = Column(Integer, default=0)  # Boolean: 0=False, 1=True

    # Optional fields
    priority = Column(Integer, default=2)  # 1=high, 2=medium, 3=low
    due_date = Column(DateTime, nullable=True)
    parent_goal_id = Column(Integer, ForeignKey('persona_goals.id'), nullable=True)  # Link to goal

    # Source tracking
    source_message_id = Column(Integer, nullable=True)
    source_type = Column(String(20), default='manual')  # 'manual', 'extracted'

    # Order for manual reordering
    sort_order = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship('User', backref='todo_items')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'character_id': self.character_id,
            'text': self.text,
            'is_completed': bool(self.is_completed),
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'parent_goal_id': self.parent_goal_id,
            'source_type': self.source_type,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class LifeAreaScore(Base):
    """Life areas scorecard for Coach personas.

    Tracks user satisfaction scores (1-10) across life domains.
    Displayed in the sidebar for Coach-category personas.
    """
    __tablename__ = 'life_area_scores'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    character_id = Column(String(36), nullable=False, index=True)

    # Life area and score
    area = Column(String(50), nullable=False)  # career, finances, health, etc.
    score = Column(Integer, nullable=False)  # 1-10

    # Optional notes
    notes = Column(Text, nullable=True)

    # Source tracking
    source_message_id = Column(Integer, nullable=True)
    source_type = Column(String(20), default='manual')  # 'manual', 'extracted'

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', backref='life_area_scores')

    # Unique constraint: one score per area per user+character
    __table_args__ = (
        UniqueConstraint('user_id', 'character_id', 'area', name='uix_life_area_score'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'character_id': self.character_id,
            'area': self.area,
            'score': self.score,
            'notes': self.notes,
            'source_type': self.source_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# Life areas constant for reference
LIFE_AREAS = [
    'career',       # Career/Work
    'finances',     # Finances
    'health',       # Health
    'relationships',  # Romantic Relationships
    'family',       # Family
    'friendships',  # Friendships
    'growth',       # Personal Growth
    'recreation',   # Fun/Recreation
    'environment',  # Environment/Home
    'contribution'  # Contribution/Service
]


class PersonaGoal(Base):
    """Goals with progress tracking for personas.

    Users can set goals with numeric targets and track progress over time.
    Goals can be linked to a specific persona (Coach personas are typical users).
    """
    __tablename__ = 'persona_goals'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    character_id = Column(String(36), nullable=False, index=True)

    # Goal definition
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # health, career, finance, personal, etc.

    # Target tracking
    target_value = Column(Float, nullable=True)  # Optional numeric target
    current_value = Column(Float, default=0)
    unit = Column(String(50), nullable=True)  # e.g., "lbs", "miles", "$", "hours"

    # Timeline
    target_date = Column(DateTime, nullable=True)
    start_date = Column(DateTime, default=datetime.utcnow)

    # Status
    status = Column(String(20), default='active')  # active, completed, paused, abandoned
    priority = Column(Integer, default=2)  # 1=high, 2=medium, 3=low

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship('User', backref='persona_goals')
    progress_logs = relationship('GoalProgressLog', back_populates='goal', cascade='all, delete-orphan')
    todos = relationship('TodoItem', backref='parent_goal', foreign_keys='TodoItem.parent_goal_id')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'character_id': self.character_id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'target_value': self.target_value,
            'current_value': self.current_value,
            'unit': self.unit,
            'target_date': self.target_date.isoformat() if self.target_date else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'status': self.status,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'progress_percentage': self.get_progress_percentage()
        }

    def get_progress_percentage(self) -> float:
        """Calculate progress as a percentage (0-100)."""
        if not self.target_value or self.target_value == 0:
            return 0 if self.status != 'completed' else 100
        return min(100, (self.current_value / self.target_value) * 100)

    def mark_completed(self):
        """Mark goal as completed."""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        if self.target_value:
            self.current_value = self.target_value


class GoalProgressLog(Base):
    """Log entries for goal progress updates.

    Each time a user updates progress on a goal, a log entry is created.
    This enables tracking progress over time and showing charts.
    """
    __tablename__ = 'goal_progress_logs'

    id = Column(Integer, primary_key=True)
    goal_id = Column(Integer, ForeignKey('persona_goals.id'), nullable=False)

    # Progress update
    value_change = Column(Float, nullable=False)  # Positive or negative change
    new_value = Column(Float, nullable=False)  # Value after change
    note = Column(Text, nullable=True)

    # Timestamp
    logged_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    goal = relationship('PersonaGoal', back_populates='progress_logs')

    def to_dict(self):
        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'value_change': self.value_change,
            'new_value': self.new_value,
            'note': self.note,
            'logged_at': self.logged_at.isoformat() if self.logged_at else None
        }


class PersonaHabit(Base):
    """Habits with streak tracking for personas.

    Users can define habits and track daily/weekly completion.
    Streaks are automatically calculated based on completions.
    """
    __tablename__ = 'persona_habits'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    character_id = Column(String(36), nullable=False, index=True)

    # Habit definition
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Frequency configuration
    frequency = Column(String(20), default='daily')  # daily, weekly
    frequency_days = Column(JSON, nullable=True)  # For weekly: ["mon", "wed", "fri"]
    target_per_period = Column(Integer, default=1)  # Times per day/week

    # Streak tracking
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_completed_date = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Integer, default=1)  # Boolean: 0=paused, 1=active

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', backref='persona_habits')
    completions = relationship('HabitCompletion', back_populates='habit', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'character_id': self.character_id,
            'title': self.title,
            'description': self.description,
            'frequency': self.frequency,
            'frequency_days': self.frequency_days,
            'target_per_period': self.target_per_period,
            'current_streak': self.current_streak,
            'longest_streak': self.longest_streak,
            'last_completed_date': self.last_completed_date.isoformat() if self.last_completed_date else None,
            'is_active': bool(self.is_active),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_today': self.is_completed_today()
        }

    def is_completed_today(self) -> bool:
        """Check if habit was completed today."""
        if not self.last_completed_date:
            return False
        today = datetime.utcnow().date()
        return self.last_completed_date.date() == today


class HabitCompletion(Base):
    """Log of habit completions.

    Each time a user marks a habit as done, a completion is recorded.
    Used for streak calculation and completion history.
    """
    __tablename__ = 'habit_completions'

    id = Column(Integer, primary_key=True)
    habit_id = Column(Integer, ForeignKey('persona_habits.id'), nullable=False)

    # Completion details
    completed_at = Column(DateTime, default=datetime.utcnow)
    note = Column(Text, nullable=True)

    # Relationships
    habit = relationship('PersonaHabit', back_populates='completions')

    def to_dict(self):
        return {
            'id': self.id,
            'habit_id': self.habit_id,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'note': self.note
        }


class PersonaFeaturePreferences(Base):
    """User preferences for which features are enabled per persona.

    Hierarchy for determining feature visibility:
    1. User override (this table) - highest priority
    2. Character card 'features' field - persona creator defaults
    3. Category defaults - based on persona category (Coach, Friend, etc.)
    """
    __tablename__ = 'persona_feature_preferences'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    character_id = Column(String(36), nullable=False, index=True)

    # Feature toggles (NULL means use default, True/False for explicit override)
    show_goals = Column(Integer, nullable=True)  # NULL = use default
    show_habits = Column(Integer, nullable=True)
    show_todos = Column(Integer, nullable=True)
    show_life_areas = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: one preference record per user+character combo
    __table_args__ = (
        UniqueConstraint('user_id', 'character_id', name='uq_user_character_features'),
    )

    # Relationships
    user = relationship('User', backref='feature_preferences')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'character_id': self.character_id,
            'show_goals': bool(self.show_goals) if self.show_goals is not None else None,
            'show_habits': bool(self.show_habits) if self.show_habits is not None else None,
            'show_todos': bool(self.show_todos) if self.show_todos is not None else None,
            'show_life_areas': bool(self.show_life_areas) if self.show_life_areas is not None else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# =============================================================================
# Google Integration Models
# =============================================================================

class GoogleCredentials(Base):
    """OAuth2 credentials for Google APIs (Calendar + Tasks).

    Stores the user's Google OAuth tokens for accessing Calendar and Tasks APIs.
    One record per user (unique on user_id).
    """
    __tablename__ = 'google_credentials'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)

    # OAuth tokens
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expiry = Column(DateTime, nullable=False)

    # Connection status
    is_enabled = Column(Integer, default=1)  # Boolean
    scopes = Column(JSON, default=list)  # List of granted scopes

    # User info from Google
    google_email = Column(String(255))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', backref='google_credentials')

    def is_token_expired(self) -> bool:
        """Check if access token is expired (with 5 minute buffer)."""
        from datetime import timedelta
        return datetime.utcnow() >= (self.token_expiry - timedelta(minutes=5))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'google_email': self.google_email,
            'is_enabled': bool(self.is_enabled),
            'scopes': self.scopes,
            'token_expired': self.is_token_expired(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class PersonaGoogleSyncConfig(Base):
    """Per-persona Google sync configuration.

    Controls which personas sync their todos to Google Tasks.
    Each synced persona gets its own Google Tasks list.
    """
    __tablename__ = 'persona_google_sync_config'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    character_id = Column(String(36), nullable=False, index=True)

    # Google Tasks sync
    tasks_sync_enabled = Column(Integer, default=0)  # Boolean
    google_tasklist_id = Column(String(255))  # Google's internal list ID
    google_tasklist_name = Column(String(255))  # e.g., "MinouChat - Coach"

    # Google Calendar sync
    calendar_sync_enabled = Column(Integer, default=0)  # Boolean
    calendar_id = Column(String(255), default='primary')  # Which calendar to read from

    # Last sync timestamp
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(50), default='never')  # never, success, error
    last_sync_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint
    __table_args__ = (
        UniqueConstraint('user_id', 'character_id', name='uq_persona_google_sync'),
    )

    # Relationships
    user = relationship('User', backref='persona_google_sync_configs')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'character_id': self.character_id,
            'tasks_sync_enabled': bool(self.tasks_sync_enabled),
            'google_tasklist_id': self.google_tasklist_id,
            'google_tasklist_name': self.google_tasklist_name,
            'calendar_sync_enabled': bool(self.calendar_sync_enabled),
            'calendar_id': self.calendar_id,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'last_sync_status': self.last_sync_status,
            'last_sync_error': self.last_sync_error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class TodoGoogleTaskMapping(Base):
    """Mapping between MinouChat todos and Google Tasks.

    Enables two-way sync by tracking which local todo corresponds to which
    Google Task, and their respective update timestamps for conflict resolution.
    """
    __tablename__ = 'todo_google_task_mapping'

    id = Column(Integer, primary_key=True)
    todo_id = Column(Integer, ForeignKey('todo_items.id', ondelete='CASCADE'), nullable=False, unique=True)

    # Google Task identifiers
    google_task_id = Column(String(255), nullable=False)
    google_tasklist_id = Column(String(255), nullable=False)

    # Sync state tracking (for conflict resolution)
    local_updated_at = Column(DateTime, nullable=False)  # Last local update at sync time
    google_updated_at = Column(DateTime, nullable=False)  # Google's "updated" timestamp at sync time
    last_sync_at = Column(DateTime, default=datetime.utcnow)
    sync_status = Column(String(20), default='synced')  # synced, pending_push, pending_pull, conflict

    # Relationships
    todo = relationship('TodoItem', backref='google_mapping')

    __table_args__ = (
        # Index for looking up by Google task ID
        # Note: Using a simple index instead of compound for SQLite compatibility
    )

    def to_dict(self):
        return {
            'id': self.id,
            'todo_id': self.todo_id,
            'google_task_id': self.google_task_id,
            'google_tasklist_id': self.google_tasklist_id,
            'local_updated_at': self.local_updated_at.isoformat() if self.local_updated_at else None,
            'google_updated_at': self.google_updated_at.isoformat() if self.google_updated_at else None,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'sync_status': self.sync_status
        }


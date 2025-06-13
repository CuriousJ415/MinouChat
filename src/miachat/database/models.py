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
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
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
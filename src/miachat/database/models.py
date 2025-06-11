"""
Database models for MiaChat.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Table, Text
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.mutable import MutableDict

Base = declarative_base()

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
    context = Column(MutableDict.as_mutable(JSON))

    personality = relationship('Personality', back_populates='conversations')
    messages = relationship('Message', back_populates='conversation')

class Message(Base):
    """Message model."""
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    meta_data = Column(MutableDict.as_mutable(JSON))

    conversation = relationship('Conversation', back_populates='messages')

class User(Base):
    """User model for authentication."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(120), nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False) 
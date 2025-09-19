"""
Conversation management models for character versioning and session tracking.
These are data models for JSON-based storage, not database models.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List, Any, Optional


class CharacterVersion(BaseModel):
    """Represents a version of a character with change tracking."""
    character_id: str
    version: int
    system_prompt: str
    persona: str
    change_reason: str
    created_at: datetime
    is_active: bool = True
    traits: Optional[Dict[str, Any]] = None
    communication_style: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True


class ConversationSession(BaseModel):
    """Represents a conversation session between user and character."""
    session_id: str
    character_id: str
    character_version: int
    user_id: str
    started_at: datetime
    last_activity: datetime
    message_count: int
    context_summary: Optional[str] = None
    memory_context: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True


class ChatMessage(BaseModel):
    """Represents a message in a conversation."""
    session_id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime
    character_version: int
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True


class CharacterUpdateEvent(BaseModel):
    """Represents a character update event for tracking changes."""
    event_id: str
    character_id: str
    old_version: int
    new_version: int
    change_type: str  # 'personality', 'system_prompt', 'minor_update', 'major_update'
    change_description: str
    timestamp: datetime
    triggered_by: str  # 'user', 'system', 'conversation'

    class Config:
        arbitrary_types_allowed = True
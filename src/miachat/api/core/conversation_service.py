"""
Conversation service for managing chat conversations with database persistence.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, text
from ...database.models import Conversation, Message
from ...database.config import get_db
import logging

logger = logging.getLogger(__name__)

class ConversationService:
    """Service for managing conversations with database persistence."""
    
    def __init__(self):
        self.active_conversations: Dict[str, int] = {}  # character_id -> conversation_id
    
    def get_or_create_conversation(self, character_id: str, db: Session) -> Conversation:
        """Get existing active conversation or create a new one for a character."""
        # First check if we have an active conversation in memory
        if character_id in self.active_conversations:
            conversation_id = self.active_conversations[character_id]
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation and conversation.is_active():
                return conversation
        
        # Look for active conversation in database using JSON query
        conversation = db.query(Conversation).filter(
            and_(
                Conversation.conversation_data.contains({"character_id": character_id}),
                Conversation.ended_at.is_(None)
            )
        ).first()
        
        if conversation:
            self.active_conversations[character_id] = conversation.id
            return conversation
        
        # Create new conversation
        conversation = Conversation(
            persona_id=1,  # Use a default persona ID for now
            title=f"Conversation with {character_id}",
            conversation_data={
                "character_id": character_id,
                "started_by": "user",
                "created_at": datetime.utcnow().isoformat()
            }
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        self.active_conversations[character_id] = conversation.id
        return conversation
    
    def add_message(self, conversation_id: int, content: str, role: str, db: Session) -> Message:
        """Add a message to a conversation."""
        logger.debug(f"Adding message to conversation {conversation_id}: role={role}, content={content[:100]}...")

        message = Message(
            conversation_id=conversation_id,
            content=content,
            role=role,
            timestamp=datetime.utcnow(),
            file_attachments={
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        logger.debug(f"Successfully added message with id={message.id} to conversation {conversation_id}")
        return message
    
    def get_conversation_messages(self, conversation_id: int, limit: Optional[int] = None, db: Session = None) -> List[Dict[str, Any]]:
        """Get messages from a conversation."""
        if db is None:
            db = next(get_db())
        
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            return []
        
        messages = conversation.get_messages(limit=limit)
        return [msg.to_dict() for msg in messages]
    
    def end_conversation(self, character_id: str, db: Session) -> bool:
        """End the active conversation for a character."""
        if character_id in self.active_conversations:
            conversation_id = self.active_conversations[character_id]
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            
            if conversation and conversation.is_active():
                conversation.end()
                db.commit()
                del self.active_conversations[character_id]
                return True
        
        return False
    
    def get_character_conversations(self, character_id: str, db: Session) -> List[Dict[str, Any]]:
        """Get all conversations for a character."""
        # Use raw SQL for JSON query as SQLAlchemy JSON queries can be tricky
        result = db.execute(
            text("""
                SELECT id, started_at, ended_at, conversation_data
                FROM conversations 
                WHERE json_extract(conversation_data, '$.character_id') = :character_id
                ORDER BY started_at DESC
            """),
            {"character_id": character_id}
        )
        
        conversations = []
        for row in result:
            started_at = row[1]
            ended_at = row[2]
            # Handle both datetime and string
            if hasattr(started_at, 'isoformat'):
                started_at_val = started_at.isoformat()
            else:
                started_at_val = started_at
            if ended_at and hasattr(ended_at, 'isoformat'):
                ended_at_val = ended_at.isoformat()
            else:
                ended_at_val = ended_at
            conversation = {
                "id": row[0],
                "started_at": started_at_val,
                "ended_at": ended_at_val,
                "is_active": ended_at is None,
                "message_count": 0  # We'll get this separately if needed
            }
            conversations.append(conversation)
        
        return conversations
    
    def delete_conversation(self, conversation_id: int, db: Session) -> bool:
        """Delete a conversation and all its messages."""
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            return False
        
        # Remove from active conversations if present
        character_id = conversation.conversation_data.get("character_id")
        if character_id and character_id in self.active_conversations:
            del self.active_conversations[character_id]
        
        # Delete all messages first
        db.query(Message).filter(Message.conversation_id == conversation_id).delete()
        
        # Delete the conversation
        db.delete(conversation)
        db.commit()
        
        return True

# Global conversation service instance
conversation_service = ConversationService() 
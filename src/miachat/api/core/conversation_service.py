"""
Conversation service for managing chat conversations with database persistence.

Provides session-based conversation management with message history,
supporting both character-scoped and session-scoped conversations.

Security:
- Session IDs are validated as UUIDs
- Database queries use parameterized statements
- All timestamps use UTC timezone
"""

import uuid
from datetime import datetime, timezone
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
        self.session_cache: Dict[str, int] = {}  # session_id -> conversation_id

    # =====================
    # Session-based methods (replacing ConversationManager)
    # =====================

    def create_session(self, character_id: str, user_id: str, db: Session) -> Dict[str, Any]:
        """Create a new conversation session. Returns session data with session_id."""
        session_id = str(uuid.uuid4())

        conversation = Conversation(
            personality_id=None,
            title=f"Session with {character_id}",
            conversation_data={
                "character_id": character_id,
                "session_id": session_id,
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        self.session_cache[session_id] = conversation.id
        self.active_conversations[character_id] = conversation.id

        logger.info(f"Created session {session_id} for character {character_id}")

        return {
            "session_id": session_id,
            "character_id": character_id,
            "user_id": user_id,
            "started_at": conversation.started_at.isoformat() if conversation.started_at else None,
            "message_count": 0
        }

    def get_session(self, session_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """Get a conversation session by session_id."""
        # Check cache first
        if session_id in self.session_cache:
            conversation_id = self.session_cache[session_id]
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation:
                return self._session_to_dict(conversation)

        # Query by session_id in conversation_data
        result = db.execute(
            text("""
                SELECT id, started_at, ended_at, conversation_data
                FROM conversations
                WHERE json_extract(conversation_data, '$.session_id') = :session_id
            """),
            {"session_id": session_id}
        )

        row = result.fetchone()
        if row:
            self.session_cache[session_id] = row[0]
            # Parse conversation_data - it may be a JSON string from raw SQL
            conv_data = row[3]
            if isinstance(conv_data, str):
                import json
                try:
                    conv_data = json.loads(conv_data)
                except (json.JSONDecodeError, TypeError):
                    conv_data = {}
            elif not isinstance(conv_data, dict):
                conv_data = {}

            return {
                "session_id": session_id,
                "conversation_id": row[0],
                "character_id": conv_data.get("character_id"),
                "user_id": conv_data.get("user_id"),
                "started_at": row[1].isoformat() if hasattr(row[1], 'isoformat') else row[1],
                "ended_at": row[2].isoformat() if row[2] and hasattr(row[2], 'isoformat') else row[2],
                "is_active": row[2] is None
            }

        return None

    def _session_to_dict(self, conversation: Conversation) -> Dict[str, Any]:
        """Convert a Conversation to session dict format."""
        data = conversation.conversation_data or {}
        return {
            "session_id": data.get("session_id"),
            "conversation_id": conversation.id,
            "character_id": data.get("character_id"),
            "user_id": data.get("user_id"),
            "started_at": conversation.started_at.isoformat() if conversation.started_at else None,
            "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
            "is_active": conversation.ended_at is None
        }

    def get_conversation_history(self, session_id: str, limit: int = 20, db: Session = None) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""
        if db is None:
            db = next(get_db())

        # Get conversation_id from session
        session = self.get_session(session_id, db)
        if not session:
            return []

        conversation_id = session.get("conversation_id") or self.session_cache.get(session_id)
        if not conversation_id:
            return []

        return self.get_conversation_messages(conversation_id, limit=limit, db=db)

    def save_message(self, session_id: str, role: str, content: str, db: Session) -> Optional[Message]:
        """Save a message to a session."""
        session = self.get_session(session_id, db)
        if not session:
            logger.warning(f"Session {session_id} not found when saving message")
            return None

        conversation_id = session.get("conversation_id") or self.session_cache.get(session_id)
        if not conversation_id:
            return None

        return self.add_message(conversation_id, content, role, db)
    
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
            personality_id=None,  # Personality is optional for chat conversations
            title=f"Conversation with {character_id}",
            conversation_data={
                "character_id": character_id,
                "started_by": "user",
                "created_at": datetime.now(timezone.utc).isoformat()
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
            timestamp=datetime.now(timezone.utc),
            file_attachments={
                "timestamp": datetime.now(timezone.utc).isoformat()
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

    def get_recent_conversations(self, user_id: int, limit: int = 5, db: Session = None) -> List[Dict[str, Any]]:
        """Get recent conversations for a user, ordered by most recent activity.

        Args:
            user_id: The user's ID
            limit: Maximum number of conversations to return
            db: Database session

        Returns:
            List of conversation dicts with id, character_id, last_message, updated_at
        """
        if db is None:
            db = next(get_db())

        # Query conversations for this user with their most recent message
        result = db.execute(
            text("""
                SELECT
                    c.id,
                    c.started_at,
                    json_extract(c.conversation_data, '$.character_id') as character_id,
                    json_extract(c.conversation_data, '$.session_id') as session_id,
                    m.content as last_message,
                    m.timestamp as last_message_time,
                    (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as message_count
                FROM conversations c
                LEFT JOIN (
                    SELECT conversation_id, content, timestamp,
                           ROW_NUMBER() OVER (PARTITION BY conversation_id ORDER BY timestamp DESC) as rn
                    FROM messages
                ) m ON c.id = m.conversation_id AND m.rn = 1
                WHERE json_extract(c.conversation_data, '$.user_id') = :user_id
                ORDER BY COALESCE(m.timestamp, c.started_at) DESC
                LIMIT :limit
            """),
            {"user_id": str(user_id), "limit": limit}
        )

        conversations = []
        for row in result:
            conv_id = row[0]
            started_at = row[1]
            character_id = row[2]
            session_id = row[3]
            last_message = row[4]
            last_message_time = row[5]
            message_count = row[6] or 0

            # Format timestamps
            if last_message_time:
                if hasattr(last_message_time, 'isoformat'):
                    updated_at = last_message_time.isoformat()
                else:
                    updated_at = last_message_time
            elif started_at:
                if hasattr(started_at, 'isoformat'):
                    updated_at = started_at.isoformat()
                else:
                    updated_at = started_at
            else:
                updated_at = None

            # Truncate last message for preview
            if last_message and len(last_message) > 100:
                last_message = last_message[:97] + "..."

            conversations.append({
                "id": session_id or str(conv_id),
                "conversation_id": conv_id,
                "character_id": character_id,
                "last_message": last_message or "No messages yet",
                "updated_at": updated_at,
                "message_count": message_count
            })

        return conversations

    def get_conversations_for_character_grouped(
        self,
        character_id: str,
        user_id: int,
        db: Session
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get conversations for a character grouped by date (Today, Yesterday, Previous 7 Days, Older).

        Args:
            character_id: Character ID to filter by
            user_id: User ID to filter by
            db: Database session

        Returns:
            Dict with date group keys and lists of conversation dicts
        """
        from datetime import date, timedelta

        today = date.today()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)

        # Query conversations with first message for title
        result = db.execute(
            text("""
                SELECT
                    c.id,
                    c.started_at,
                    c.ended_at,
                    json_extract(c.conversation_data, '$.session_id') as session_id,
                    c.title,
                    (SELECT content FROM messages WHERE conversation_id = c.id AND role = 'user' ORDER BY timestamp ASC LIMIT 1) as first_message,
                    (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as message_count,
                    (SELECT MAX(timestamp) FROM messages WHERE conversation_id = c.id) as last_activity
                FROM conversations c
                WHERE json_extract(c.conversation_data, '$.character_id') = :character_id
                  AND json_extract(c.conversation_data, '$.user_id') = :user_id
                ORDER BY COALESCE(
                    (SELECT MAX(timestamp) FROM messages WHERE conversation_id = c.id),
                    c.started_at
                ) DESC
            """),
            {"character_id": character_id, "user_id": str(user_id)}
        )

        groups: Dict[str, List[Dict[str, Any]]] = {
            "today": [],
            "yesterday": [],
            "previous_7_days": [],
            "older": []
        }

        for row in result:
            conv_id = row[0]
            started_at = row[1]
            ended_at = row[2]
            session_id = row[3]
            title = row[4]
            first_message = row[5]
            message_count = row[6] or 0
            last_activity = row[7]

            # Skip empty conversations
            if message_count == 0:
                continue

            # Generate title from first message if not set
            if not title and first_message:
                title = self._generate_title_from_message(first_message)
            elif not title:
                title = "New conversation"

            # Parse date for grouping
            if last_activity:
                if hasattr(last_activity, 'date'):
                    conv_date = last_activity.date()
                else:
                    # Parse from string
                    try:
                        from datetime import datetime as dt
                        conv_date = dt.fromisoformat(str(last_activity).replace('Z', '+00:00')).date()
                    except:
                        conv_date = today
            elif started_at:
                if hasattr(started_at, 'date'):
                    conv_date = started_at.date()
                else:
                    try:
                        from datetime import datetime as dt
                        conv_date = dt.fromisoformat(str(started_at).replace('Z', '+00:00')).date()
                    except:
                        conv_date = today
            else:
                conv_date = today

            # Determine group
            if conv_date == today:
                group = "today"
            elif conv_date == yesterday:
                group = "yesterday"
            elif conv_date > week_ago:
                group = "previous_7_days"
            else:
                group = "older"

            # Format timestamp
            if last_activity:
                if hasattr(last_activity, 'isoformat'):
                    updated_at = last_activity.isoformat()
                else:
                    updated_at = str(last_activity)
            elif started_at:
                if hasattr(started_at, 'isoformat'):
                    updated_at = started_at.isoformat()
                else:
                    updated_at = str(started_at)
            else:
                updated_at = None

            conv = {
                "id": session_id or str(conv_id),
                "conversation_id": conv_id,
                "title": title,
                "message_count": message_count,
                "updated_at": updated_at,
                "is_active": ended_at is None
            }

            groups[group].append(conv)

        return groups

    def _generate_title_from_message(self, message: str, max_length: int = 40) -> str:
        """Generate a conversation title from the first message (fallback method).

        Args:
            message: First user message
            max_length: Maximum title length

        Returns:
            Generated title string
        """
        if not message:
            return "New conversation"

        # Clean up the message
        title = message.strip()

        # Remove common prefixes
        prefixes = ["hi ", "hey ", "hello ", "can you ", "could you ", "please ", "i need ", "i want "]
        lower = title.lower()
        for prefix in prefixes:
            if lower.startswith(prefix):
                title = title[len(prefix):]
                break

        # Truncate if too long
        if len(title) > max_length:
            # Find a good break point
            truncated = title[:max_length]
            last_space = truncated.rfind(' ')
            if last_space > max_length // 2:
                title = truncated[:last_space] + "..."
            else:
                title = truncated + "..."

        # Capitalize first letter
        if title:
            title = title[0].upper() + title[1:]

        return title or "New conversation"

    def generate_title_with_llm(
        self,
        conversation_id: int,
        db: Session,
        model_config: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Generate a conversation title using the LLM based on the first few messages.

        Args:
            conversation_id: Conversation ID
            db: Database session
            model_config: Optional LLM config (uses Ollama default if not provided)

        Returns:
            Generated title string, or None if generation failed
        """
        from .llm_client import llm_client

        # Get the first few messages from the conversation
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.timestamp.asc()).limit(4).all()

        if not messages:
            return None

        # Build context from messages
        context_parts = []
        for msg in messages:
            role = "User" if msg.role == "user" else "Assistant"
            # Truncate long messages
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            context_parts.append(f"{role}: {content}")

        context = "\n".join(context_parts)

        # Create the title generation prompt
        system_prompt = """You are a title generator. Generate a very short, descriptive title (3-6 words) for a conversation.
The title should capture the main topic or intent.
Reply with ONLY the title, no quotes, no explanation, no punctuation at the end."""

        prompt_messages = [
            {"role": "user", "content": f"Generate a short title for this conversation:\n\n{context}"}
        ]

        # Use provided config or default to a fast model
        if not model_config:
            model_config = {
                "provider": "ollama",
                "model": "llama3.1:8b",
                "temperature": 0.3,  # Lower temperature for more consistent titles
                "max_tokens": 20
            }

        try:
            title = llm_client.generate_response_with_config(
                messages=prompt_messages,
                system_prompt=system_prompt,
                model_config=model_config
            )

            if title:
                # Clean up the title
                title = title.strip().strip('"\'').strip()
                # Remove trailing punctuation
                title = title.rstrip('.,!?:;')
                # Capitalize first letter
                if title:
                    title = title[0].upper() + title[1:]
                # Limit length
                if len(title) > 60:
                    title = title[:57] + "..."

                # Update the conversation title in the database
                conversation = db.query(Conversation).filter(
                    Conversation.id == conversation_id
                ).first()
                if conversation:
                    conversation.title = title
                    db.commit()
                    logger.info(f"Generated title for conversation {conversation_id}: {title}")

                return title

        except Exception as e:
            logger.warning(f"Failed to generate title with LLM: {e}")

        return None

    def generate_title_async(
        self,
        conversation_id: int,
        model_config: Optional[Dict[str, Any]] = None
    ):
        """Generate a conversation title asynchronously in a background thread.

        Args:
            conversation_id: Conversation ID
            model_config: Optional LLM config
        """
        import threading
        from ...database.config import db_config

        def _generate():
            # Create a new database session for this thread
            db = db_config.get_session()
            try:
                self.generate_title_with_llm(conversation_id, db, model_config)
            finally:
                db.close()

        thread = threading.Thread(target=_generate, daemon=True)
        thread.start()

    def update_conversation_title(self, conversation_id: int, title: str, db: Session) -> bool:
        """Update a conversation's title.

        Args:
            conversation_id: Conversation ID
            title: New title
            db: Database session

        Returns:
            True if successful
        """
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            return False

        conversation.title = title
        db.commit()
        return True

    def delete_conversation_by_session(self, session_id: str, user_id: int, db: Session) -> bool:
        """Delete a conversation by session ID, verifying ownership.

        Args:
            session_id: Session ID of the conversation
            user_id: User ID for ownership verification
            db: Database session

        Returns:
            True if deleted, False otherwise
        """
        # Find conversation by session_id
        result = db.execute(
            text("""
                SELECT id, json_extract(conversation_data, '$.user_id') as owner_id
                FROM conversations
                WHERE json_extract(conversation_data, '$.session_id') = :session_id
            """),
            {"session_id": session_id}
        )

        row = result.fetchone()
        if not row:
            logger.warning(f"Conversation not found for session {session_id}")
            return False

        conv_id = row[0]
        owner_id = row[1]

        # Verify ownership
        if str(owner_id) != str(user_id):
            logger.warning(f"User {user_id} tried to delete conversation owned by {owner_id}")
            return False

        # Delete conversation
        return self.delete_conversation(conv_id, db)


# Global conversation service instance
conversation_service = ConversationService() 
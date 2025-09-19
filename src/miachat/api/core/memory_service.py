"""
Memory service for managing conversation context and memory retrieval.
"""

import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..models.chat import Conversation, Message
from ...database.config import get_db
import logging

logger = logging.getLogger(__name__)

class MemoryService:
    """Service for managing conversation memory and context retrieval."""
    
    def __init__(self, default_context_window: int = 10):
        """Initialize the memory service.
        
        Args:
            default_context_window: Default number of recent messages to include in context
        """
        self.default_context_window = default_context_window
    
    def get_context(
        self,
        conversation_id: int,
        current_message: str,
        context_window: Optional[int] = None,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """Get context for a conversation, combining recent messages and relevant search results.

        Args:
            conversation_id: ID of the conversation
            current_message: The current user message
            context_window: Number of recent messages to include (defaults to self.default_context_window)
            db: Database session (optional, will create one if not provided)

        Returns:
            List of message dictionaries with role, content, and timestamp
        """
        if db is None:
            db = next(get_db())

        context_window = context_window or self.default_context_window

        logger.debug(f"Getting context for conversation {conversation_id} with window {context_window}")
        logger.debug(f"Current message: {current_message[:100]}...")

        try:
            # Get recent messages
            logger.debug("Fetching recent messages...")
            recent_messages = self._get_recent_messages(conversation_id, context_window, db)
            logger.debug(f"Got {len(recent_messages)} recent messages")

            # Get relevant messages from search
            logger.debug("Fetching relevant messages...")
            relevant_messages = self._search_conversation(conversation_id, current_message, db)
            logger.debug(f"Got {len(relevant_messages)} relevant messages")

            # Combine and deduplicate messages
            logger.debug("Combining context...")
            combined_context = self._combine_context(recent_messages, relevant_messages)
            logger.debug(f"Combined context has {len(combined_context)} messages")

            logger.info(f"Retrieved context for conversation {conversation_id}: "
                       f"{len(recent_messages)} recent + {len(relevant_messages)} relevant = {len(combined_context)} total")

            return combined_context

        except Exception as e:
            logger.error(f"Error retrieving context for conversation {conversation_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Fallback to just recent messages
            return self._get_recent_messages(conversation_id, context_window, db)
    
    def _get_recent_messages(
        self,
        conversation_id: int,
        limit: int,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Get the most recent messages from a conversation.

        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages to retrieve
            db: Database session

        Returns:
            List of message dictionaries
        """
        try:
            logger.debug(f"Querying recent messages for conversation_id={conversation_id}, limit={limit}")

            # Query messages directly from the database
            messages = db.query(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(Message.timestamp.desc()).limit(limit).all()

            logger.debug(f"Found {len(messages)} messages in database")

            # Debug: check if any messages exist at all for this conversation
            total_messages = db.query(Message).filter(
                Message.conversation_id == conversation_id
            ).count()
            logger.debug(f"Total messages in conversation {conversation_id}: {total_messages}")

            if messages:
                logger.debug(f"Sample message: id={messages[0].id}, role={messages[0].role}, content={messages[0].content[:50]}...")

            result = [msg.to_dict() for msg in messages]
            logger.debug(f"Returning {len(result)} message dictionaries")
            return result

        except Exception as e:
            logger.error(f"Error getting recent messages for conversation {conversation_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def _search_conversation(
        self, 
        conversation_id: int, 
        query: str, 
        db: Session,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search conversation history for messages relevant to the query.
        
        Args:
            conversation_id: ID of the conversation
            query: Search query (current user message)
            db: Database session
            limit: Maximum number of relevant messages to return
            
        Returns:
            List of relevant message dictionaries
        """
        try:
            # Extract keywords from the query
            keywords = self._extract_keywords(query)
            if not keywords:
                return []
            
            # Search for messages containing these keywords
            relevant_messages = []
            
            # Use raw SQL for better performance with text search
            for keyword in keywords:
                result = db.execute(
                    text("""
                        SELECT id, role, content, timestamp, file_attachments
                        FROM messages
                        WHERE conversation_id = :conversation_id
                        AND LOWER(content) LIKE :keyword
                        ORDER BY timestamp DESC
                        LIMIT :limit
                    """),
                    {
                        "conversation_id": conversation_id,
                        "keyword": f"%{keyword.lower()}%",
                        "limit": limit
                    }
                )
                
                for row in result:
                    message_dict = {
                        "id": row[0],
                        "role": row[1],
                        "content": row[2],
                        "timestamp": row[3].isoformat() if hasattr(row[3], 'isoformat') else str(row[3]),
                        "metadata": row[4] if row[4] else {}
                    }
                    relevant_messages.append(message_dict)
            
            # Remove duplicates and sort by timestamp
            seen_ids = set()
            unique_messages = []
            for msg in relevant_messages:
                if msg["id"] not in seen_ids:
                    seen_ids.add(msg["id"])
                    unique_messages.append(msg)
            
            # Sort by timestamp (oldest first for context)
            unique_messages.sort(key=lambda x: x["timestamp"])
            
            return unique_messages[:limit]
            
        except Exception as e:
            logger.error(f"Error searching conversation {conversation_id}: {e}")
            return []
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text for search.
        
        Args:
            text: Input text
            
        Returns:
            List of keywords (lowercase, no duplicates)
        """
        # Convert to lowercase and remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Split into words and filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
            'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }
        
        words = text.split()
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for word in keywords:
            if word not in seen:
                seen.add(word)
                unique_keywords.append(word)
        
        return unique_keywords[:5]  # Limit to top 5 keywords
    
    def _combine_context(
        self, 
        recent_messages: List[Dict[str, Any]], 
        relevant_messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Combine recent and relevant messages, removing duplicates.
        
        Args:
            recent_messages: List of recent message dictionaries
            relevant_messages: List of relevant message dictionaries
            
        Returns:
            Combined list of message dictionaries
        """
        # Start with recent messages
        combined = recent_messages.copy()
        
        # Add relevant messages that aren't already in recent messages
        recent_ids = {msg["id"] for msg in recent_messages}
        
        for msg in relevant_messages:
            if msg["id"] not in recent_ids:
                combined.append(msg)
                recent_ids.add(msg["id"])
        
        # Sort by timestamp to maintain chronological order
        combined.sort(key=lambda x: x["timestamp"])
        
        return combined
    
    def search_conversation(
        self, 
        conversation_id: int, 
        query: str, 
        db: Session = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search conversation history for messages matching a query.
        
        Args:
            conversation_id: ID of the conversation
            query: Search query
            db: Database session (optional)
            limit: Maximum number of results
            
        Returns:
            List of matching message dictionaries
        """
        if db is None:
            db = next(get_db())
        
        return self._search_conversation(conversation_id, query, db, limit)
    
    def get_conversation_summary(
        self, 
        conversation_id: int, 
        db: Session = None
    ) -> Dict[str, Any]:
        """Get a summary of a conversation.
        
        Args:
            conversation_id: ID of the conversation
            db: Database session (optional)
            
        Returns:
            Dictionary with conversation summary information
        """
        if db is None:
            db = next(get_db())
        
        try:
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if not conversation:
                return {"error": "Conversation not found"}
            
            messages = conversation.get_messages()
            
            return {
                "conversation_id": conversation_id,
                "total_messages": len(messages),
                "started_at": conversation.started_at.isoformat(),
                "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
                "is_active": conversation.is_active(),
                "user_messages": len([m for m in messages if m.role == "user"]),
                "assistant_messages": len([m for m in messages if m.role == "assistant"])
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation summary for {conversation_id}: {e}")
            return {"error": str(e)}

# Global memory service instance
memory_service = MemoryService() 
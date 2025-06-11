"""
Conversation management module for MiaChat.

This module handles the core conversation functionality, including:
- Message processing and routing
- Context management
- Integration with LLM and memory systems
- Conversation state tracking
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from dataclasses import dataclass, field

from .memory import MemoryManager
from .personality import PersonalityManager
from ..llm.base import LLMProvider
from ..database.models import Conversation, Message

logger = logging.getLogger(__name__)

@dataclass
class ConversationContext:
    """Represents the current state and context of a conversation."""
    conversation_id: str
    personality_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.utcnow)

class ConversationManager:
    """Manages conversation state and processing."""
    
    def __init__(
        self,
        memory_manager: MemoryManager,
        personality_manager: PersonalityManager,
        llm_provider: LLMProvider
    ):
        self.memory = memory_manager
        self.personality = personality_manager
        self.llm = llm_provider
        self._active_conversations: Dict[str, ConversationContext] = {}

    async def start_conversation(
        self,
        personality_id: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start a new conversation with the specified personality."""
        conversation = Conversation.create(
            personality_id=personality_id,
            metadata=initial_context or {}
        )
        
        context = ConversationContext(
            conversation_id=conversation.id,
            personality_id=personality_id,
            metadata=initial_context or {}
        )
        
        self._active_conversations[conversation.id] = context
        return conversation.id

    async def process_message(
        self,
        conversation_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Process an incoming message and generate a response."""
        if conversation_id not in self._active_conversations:
            raise ValueError(f"Conversation {conversation_id} not found")

        context = self._active_conversations[conversation_id]
        
        # Store the user message
        user_message = Message.create(
            conversation_id=conversation_id,
            content=message,
            role="user",
            metadata=metadata or {}
        )
        
        # Get relevant context from memory
        memory_context = await self.memory.get_relevant_context(
            conversation_id=conversation_id,
            current_message=message
        )
        
        # Get personality context
        personality_context = await self.personality.get_context(
            personality_id=context.personality_id
        )
        
        # Generate response using LLM
        response = await self.llm.generate_response(
            message=message,
            conversation_history=context.messages,
            memory_context=memory_context,
            personality_context=personality_context
        )
        
        # Store the assistant's response
        assistant_message = Message.create(
            conversation_id=conversation_id,
            content=response,
            role="assistant",
            metadata={}
        )
        
        # Update conversation context
        context.messages.append({
            "role": "user",
            "content": message,
            "timestamp": user_message.created_at
        })
        context.messages.append({
            "role": "assistant",
            "content": response,
            "timestamp": assistant_message.created_at
        })
        context.last_updated = datetime.utcnow()
        
        # Update memory with new interaction
        await self.memory.store_interaction(
            conversation_id=conversation_id,
            user_message=message,
            assistant_message=response,
            metadata=metadata or {}
        )
        
        return response

    async def end_conversation(self, conversation_id: str) -> None:
        """End a conversation and clean up resources."""
        if conversation_id in self._active_conversations:
            # Perform any necessary cleanup
            await self.memory.finalize_conversation(conversation_id)
            del self._active_conversations[conversation_id]

    def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve conversation history."""
        if conversation_id not in self._active_conversations:
            raise ValueError(f"Conversation {conversation_id} not found")
            
        context = self._active_conversations[conversation_id]
        messages = context.messages
        
        if limit:
            messages = messages[-limit:]
            
        return messages 
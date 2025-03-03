"""
Chat Functionality
Handles message processing, context management, and response generation
"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from flask import current_app

from app.core.character import get_character
from app.llm.adapter import generate_llm_response
from app.memory.sql import save_conversation, get_recent_conversations
from app.memory.vector import query_memories

def send_message(character_id: str, user_message: str) -> Dict:
    """
    Send a message to a character and get a response
    
    Args:
        character_id: Character's unique identifier
        user_message: User's message text
        
    Returns:
        Response dictionary with character info and message
        
    Raises:
        ValueError: If character not found or message processing fails
    """
    # Get character
    character = get_character(character_id)
    if not character:
        raise ValueError(f"Character '{character_id}' not found")
    
    # Prepare context with relevant memories
    context = _prepare_context(character, user_message)
    
    # Generate response using LLM
    try:
        response_content = generate_llm_response(
            context, 
            model=character['model'],
            provider=character.get('llm_provider', 'ollama')
        )
    except Exception as e:
        current_app.logger.error(f"LLM generation error: {str(e)}")
        raise ValueError(f"Failed to generate response: {str(e)}")
    
    # Save conversation to memory
    conversation = [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": response_content}
    ]
    save_conversation(character_id, conversation)
    
    # Update character last used timestamp
    from app.memory.sql import update_character_last_used
    update_character_last_used(character_id)
    
    # Return response
    return {
        "character": {
            "id": character['id'],
            "name": character['name'],
            "role": character['role']
        },
        "message": response_content,
        "timestamp": datetime.now().isoformat()
    }

def get_conversation_history(character_id: str, limit: int = 20, offset: int = 0) -> Dict:
    """
    Get conversation history with a character
    
    Args:
        character_id: Character's unique identifier
        limit: Maximum number of conversations to retrieve
        offset: Offset for pagination
        
    Returns:
        Dictionary with character info and conversation history
        
    Raises:
        ValueError: If character not found
    """
    # Get character
    character = get_character(character_id)
    if not character:
        raise ValueError(f"Character '{character_id}' not found")
    
    # Get recent conversations
    conversations = get_recent_conversations(character_id, limit, offset)
    
    return {
        "character": {
            "id": character['id'],
            "name": character['name'],
            "role": character['role']
        },
        "conversations": conversations,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": len(conversations)
        }
    }

def search_memories(character_id: str, query: str, limit: int = 5) -> Dict:
    """
    Search a character's memories for relevant information
    
    Args:
        character_id: Character's unique identifier
        query: Search query
        limit: Maximum number of results
        
    Returns:
        Dictionary with search results
        
    Raises:
        ValueError: If character not found or search fails
    """
    # Get character
    character = get_character(character_id)
    if not character:
        raise ValueError(f"Character '{character_id}' not found")
    
    # Search vector store
    memories = query_memories(character_id, query, limit)
    
    return {
        "character": {
            "id": character['id'],
            "name": character['name']
        },
        "query": query,
        "results": memories
    }

def _prepare_context(character: Dict, user_message: str) -> List[Dict]:
    """
    Prepare context for LLM with character information and relevant memories
    
    Args:
        character: Character dictionary
        user_message: User's message
        
    Returns:
        List of message dictionaries for LLM context
    """
    # System message with character definition
    system_message = {
        "role": "system",
        "content": character['system_prompt']
    }
    
    # Get recent conversation history
    recent_messages = get_recent_conversations(character['id'], limit=5)
    flattened_messages = []
    for conv in recent_messages:
        for message in conv['messages']:
            flattened_messages.append(message)
    
    # Get relevant memories from vector store
    memories = query_memories(character['id'], user_message, limit=3)
    
    # Format memories as a context message
    memory_content = ""
    if memories:
        memory_content = "Here are some relevant memories that might help with your response:\n\n"
        for i, memory in enumerate(memories, 1):
            memory_content += f"{i}. {memory['content']}\n"
        memory_content += "\nPlease consider these memories in your response if relevant."
    
    # Build context
    context = [system_message]
    
    # Add memory context if available
    if memory_content:
        context.append({
            "role": "system",
            "content": memory_content
        })
    
    # Add conversation history
    context.extend(flattened_messages[-10:])  # Last 10 messages for context
    
    # Add current user message
    context.append({
        "role": "user",
        "content": user_message
    })
    
    return context 
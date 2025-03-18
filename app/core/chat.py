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

# Import enhanced memory components
try:
    from app.memory.enhanced_memory import (
        build_context_with_memories,
        save_conversation_memory,
        retrieve_relevant_memories,
        search_memories_by_text,
        forget_memories_by_search
    )
    from app.core.personalization import enhance_system_prompt
    ENHANCED_MEMORY = True
except ImportError:
    # Fallback to original memory system
    from app.memory.vector import query_memories
    ENHANCED_MEMORY = False

def send_message(character_id: str, user_message: str, use_documents: bool = False, context_type: str = 'default') -> Dict:
    """
    Send a message to a character and get a response
    
    Args:
        character_id: Character's unique identifier
        user_message: User's message text
        use_documents: Whether to include document context
        context_type: Type of context to build (default, full)
        
    Returns:
        Response dictionary with character info and message
        
    Raises:
        ValueError: If character not found or message processing fails
    """
    # Get character
    character = get_character(character_id)
    if not character:
        raise ValueError(f"Character '{character_id}' not found")
    
    # Save user message to the database
    save_conversation(character_id, "user", user_message)
    
    # Generate assistant response
    try:
        # Use the character's LLM settings
        llm_provider = character.get('llm_provider', 'ollama')
        model = character.get('model', 'mistral')
        temperature = character.get('temperature', 0.7)
        top_p = character.get('top_p', 0.9)
        repeat_penalty = character.get('repeat_penalty', 1.1)
        top_k = character.get('top_k', 40)
        
        # Build prompt with system information and user message
        prompt = f"You are {character['name']}, {character['role']}. {character['personality']}"
        if character.get('backstory'):
            prompt += f"\n\nBackstory: {character['backstory']}"
        
        # Add system prompt
        prompt += f"\n\n{character['system_prompt']}"
        
        # Get document context if requested
        if use_documents:
            document_context = get_character_document_context(character_id)
            if document_context:
                prompt += f"\n\nREFERENCE MATERIALS:\n{document_context}\n\n"
                prompt += "When answering questions, reference the materials provided above. If the question is about the document, use the reference materials to provide accurate information. If the answer isn't in the reference materials, say so instead of making up an answer."
        
        # Get message history
        message_history = _get_message_history(character_id)
        
        # Generate response
        assistant_message = generate_llm_response(
            model=model,
            provider=llm_provider,
            system_prompt=prompt,
            message_history=message_history,
            user_message=user_message,
            temperature=temperature,
            top_p=top_p,
            repeat_penalty=repeat_penalty,
            top_k=top_k
        )
        
        # Save assistant message to the database
        save_conversation(character_id, "assistant", assistant_message)
        
        # Return the result
        return {
            "character": character,
            "message": assistant_message
        }
    except Exception as e:
        current_app.logger.error(f"Error generating response: {str(e)}")
        raise ValueError(f"Failed to generate response: {str(e)}")

def get_conversation_history(character_id: str, limit: int = 20, offset: int = 0) -> Dict:
    """
    Get conversation history with a character
    
    Args:
        character_id: Character's unique identifier
        limit: Maximum number of messages to retrieve
        offset: Offset for pagination
        
    Returns:
        Dictionary with character info and conversation messages
    """
    # Get character
    character = get_character(character_id)
    if not character:
        return {"error": f"Character '{character_id}' not found"}
    
    # Get conversations from database
    conversations = get_recent_conversations(character_id, limit, offset)
    
    # Format conversations for the frontend
    formatted_conversations = []
    for conv in conversations:
        formatted_conversations.append({
            "role": conv["role"],
            "content": conv["content"],
            "timestamp": conv["timestamp"]
        })
    
    return {
        "character": character,
        "conversations": formatted_conversations
    }

def search_memories(character_id: str, query: str, limit: int = 5) -> Dict:
    """
    Search character memories for relevant information
    
    Args:
        character_id: Character's unique identifier
        query: Search query
        limit: Maximum number of results
        
    Returns:
        Dictionary with search results
    """
    # Get character directly from database if get_character fails
    character = get_character(character_id)
    
    if not character:
        # Fallback to direct database access
        try:
            from flask import current_app
            import sqlite3
            
            db_path = current_app.config.get('DATABASE_PATH', 'instance/memories.db')
            if not db_path.startswith('/'):
                db_path = f"/app/{db_path}"
                
            current_app.logger.info(f"Fallback: Getting character {character_id} directly from database at {db_path}")
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM characters WHERE id = ?", (character_id,))
            row = cursor.fetchone()
            
            if row:
                character = dict(row)
                current_app.logger.info(f"Successfully retrieved character {character_id} directly from database")
            else:
                return {
                    'success': False,
                    'error': 'Character not found in database'
                }
        except Exception as e:
            current_app.logger.error(f"Error accessing character database: {e}")
            return {
                'success': False,
                'error': f'Failed to access character database: {str(e)}'
            }
    
    # Search memories
    try:
        if ENHANCED_MEMORY:
            # Try semantic search first
            try:
                memories = retrieve_relevant_memories(character_id, query)
            except Exception as e:
                current_app.logger.warning(f"Semantic search failed, falling back to text search: {e}")
                memories = []
            
            # If no semantic results, try text search
            if not memories:
                text_results = search_memories_by_text(character_id, query, limit)
                # Use 0.8 as default score for text-based results, which are less accurate than semantic
                memories = [{'content': r['content'], 'score': 0.8, 'metadata': r.get('metadata', {})} 
                           for r in text_results]
        else:
            # Use original vector search
            memories = query_memories(character_id, query, limit)
        
        # Format results
        results = []
        for memory in memories:
            # Format memory content
            content = memory['content']
            
            # Add metadata if available
            metadata = memory.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            
            # Format timestamp if available
            timestamp = None
            if 'timestamp' in metadata:
                try:
                    dt = datetime.fromisoformat(metadata['timestamp'])
                    timestamp = dt.strftime("%B %d, %Y %I:%M %p")
                except:
                    timestamp = metadata.get('timestamp')
            
            # Ensure score is present and in the right format (0-1 range)
            score = memory.get('score', 0.5)
            if isinstance(score, str):
                try:
                    score = float(score)
                except:
                    score = 0.5
                    
            if score > 1:
                score = score / 100  # Normalize if score is outside 0-1 range
                    
            results.append({
                'content': content,
                'timestamp': timestamp,
                'score': score  # Changed from 'relevance' to 'score' to match frontend expectations
            })
        
        return {
            'success': True,
            'character': {
                'id': character['id'],
                'name': character.get('name', 'Unknown'),
                'role': character.get('role', 'assistant')
            },
            'results': results
        }
    except Exception as e:
        current_app.logger.error(f"Error searching memories: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def forget_memories(character_id: str, query: str) -> Dict:
    """
    Hide memories containing specific text (forget functionality)
    
    Args:
        character_id: Character's unique identifier
        query: Text to search for and forget
        
    Returns:
        Dictionary with operation result
    """
    if not ENHANCED_MEMORY:
        return {
            'success': False,
            'message': 'Forgetting functionality requires enhanced memory system'
        }
    
    # Get character
    character = get_character(character_id)
    if not character:
        return {
            'success': False,
            'message': 'Character not found'
        }
    
    # Forget memories
    count = forget_memories_by_search(character_id, query)
    
    return {
        'success': True,
        'message': f'Successfully removed {count} memories containing "{query}"',
        'count': count
    }

def _get_message_history(character_id: str, limit: int = 30) -> List[Dict]:
    """
    Get recent message history for context building
    
    Args:
        character_id: Character's unique identifier
        limit: Maximum number of messages to retrieve
        
    Returns:
        List of message dictionaries with role and content
    """
    # Get recent conversations from the database
    conversations = get_recent_conversations(character_id, limit)
    
    # Format into message history structure
    messages = []
    for conv in conversations:
        messages.append({
            "role": conv["role"],
            "content": conv["content"]
        })
    
    return messages

def _prepare_context(character: Dict, user_message: str) -> List[Dict]:
    """
    Legacy method: Prepare context for message generation
    
    Args:
        character: Character information
        user_message: User's message
        
    Returns:
        List of context messages
    """
    system_prompt = character['system_prompt']
    
    # Try to enhance with personalization if available
    if 'enhance_system_prompt' in globals():
        try:
            system_prompt = enhance_system_prompt(character['id'], system_prompt)
        except:
            pass
    
    context = [
        {'role': 'system', 'content': system_prompt}
    ]
    
    # Add recent conversation history
    messages = _get_message_history(character['id'])
    if messages:
        context.extend(messages)
    
    # Add relevant memories from vector search
    try:
        memories = query_memories(character['id'], user_message, limit=3)
        if memories:
            memory_context = "I'll remind you of some relevant information from our past conversations:\n\n"
            for memory in memories:
                memory_context += f"- {memory['content']}\n\n"
            
            context.append({'role': 'system', 'content': memory_context})
    except Exception as e:
        current_app.logger.error(f"Error retrieving memories: {str(e)}")
    
    return context 

def get_character_document_context(character_id: str) -> str:
    """
    Get document context for a character
    
    Args:
        character_id: Character's unique identifier
        
    Returns:
        Document context as string or empty string if no documents
    """
    try:
        # Import document functions
        from app.core.document_processor import get_character_documents
        
        # Get character documents 
        documents = get_character_documents(character_id)
        
        if not documents:
            return ""
        
        # Combine document content
        context = []
        for doc in documents:
            if "text_content" in doc and doc["text_content"]:
                doc_content = doc["text_content"]
                # Truncate if too long
                if len(doc_content) > 10000:
                    doc_content = doc_content[:10000] + "...(truncated)"
                
                context.append(f"--- Document: {doc['filename']} ---\n{doc_content}\n")
        
        return "\n".join(context)
    except Exception as e:
        current_app.logger.error(f"Error getting document context: {str(e)}")
        return "" 
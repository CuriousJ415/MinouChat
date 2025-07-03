from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from .core.templates import render_template
from .core.static import mount_static_files
from .core.character_manager import character_manager
from .core.llm_client import llm_client
from .core.conversation_service import conversation_service
from .core.memory_service import memory_service
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import os
from sqlalchemy.orm import Session
from ..database.config import get_db
from ..database.models import Conversation, Message, Personality

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="MiaChat API",
    description="API for MiaChat - AI Personality Chat Application with Privacy-First Design",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key-here"  # In production, use environment variable
)

# Mount static files
mount_static_files(app)

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    character_id: str

class ChatResponse(BaseModel):
    response: str
    character_name: str
    character_id: str

class CharacterCreateRequest(BaseModel):
    name: str
    personality: str
    system_prompt: str
    llm_config: Dict[str, Any]
    role: str = "assistant"
    category: str = "General"
    backstory: str = ""
    gender: str = ""
    tags: List[str] = []

class CharacterUpdateRequest(BaseModel):
    name: Optional[str] = None
    personality: Optional[str] = None
    system_prompt: Optional[str] = None
    llm_config: Optional[Dict[str, Any]] = None
    role: Optional[str] = None
    category: Optional[str] = None
    backstory: Optional[str] = None
    gender: Optional[str] = None
    tags: Optional[List[str]] = None

# Routes
@app.get("/")
async def index(request: Request):
    """Main application page."""
    return await render_template(request, "index")

@app.get("/chat")
async def chat_page(request: Request):
    """Chat interface page."""
    characters = character_manager.list_characters()
    return await render_template(request, "chat/index", characters=characters)

@app.get("/characters")
async def characters_page(request: Request):
    """Character management page."""
    characters = character_manager.list_characters()
    available_models = character_manager.get_available_models()
    model_recommendations = character_manager.get_model_recommendations()
    categories = character_manager.get_categories()
    tags = character_manager.get_tags()
    privacy_info = character_manager.get_privacy_info()
    
    return await render_template(request, "index", 
                         characters=characters, 
                         available_models=available_models,
                         model_recommendations=model_recommendations,
                         categories=categories,
                         tags=tags,
                         privacy_info=privacy_info)

@app.get("/settings")
async def settings_page(request: Request):
    """Settings page."""
    return await render_template(request, "settings")

@app.get("/config")
async def config_page(request: Request):
    """Configuration page."""
    return await render_template(request, "config")

@app.get("/personality")
async def personality_list_page(request: Request):
    """Personality list page."""
    personalities = character_manager.list_characters()
    return await render_template(request, "personality/list", personalities=personalities)

# API Routes
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test Ollama connection
        ollama_status = "connected" if llm_client.test_connection() else "disconnected"
        
        # Get character count
        characters = character_manager.list_characters()
        
        # Count local vs cloud characters
        local_count = sum(1 for char in characters if char.get('model_config', {}).get('provider') == 'ollama')
        cloud_count = len(characters) - local_count
        
        return {
            "status": "healthy",
            "ollama": ollama_status,
            "characters": {
                "total": len(characters),
                "local_private": local_count,
                "cloud": cloud_count
            },
            "privacy_focus": "Local Ollama models are used by default for complete privacy",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.get("/api/characters")
async def list_characters():
    """List all character cards."""
    return character_manager.list_characters()

@app.get("/api/characters/{character_id}")
async def get_character(character_id: str):
    """Get a specific character card."""
    character = character_manager.get_character(character_id)
    if not character:
        return {"error": "Character not found"}, 404
    return character

@app.post("/api/characters")
async def create_character(request: CharacterCreateRequest):
    """Create a new character card."""
    character_data = request.dict()
    
    # Convert llm_config back to model_config for internal use
    if 'llm_config' in character_data:
        character_data['model_config'] = character_data.pop('llm_config')
    
    # Set default provider to ollama for privacy if not specified
    if 'model_config' in character_data and 'provider' not in character_data['model_config']:
        character_data['model_config']['provider'] = 'ollama'
        logger.info("Defaulting to Ollama provider for privacy")
    
    character = character_manager.create_character(character_data)
    if not character:
        return {"error": "Failed to create character"}, 400
    return character

@app.put("/api/characters/{character_id}")
async def update_character(character_id: str, request: CharacterUpdateRequest):
    """Update an existing character card."""
    # Only include non-None fields
    update_data = {k: v for k, v in request.dict().items() if v is not None}
    
    # Convert llm_config back to model_config for internal use
    if 'llm_config' in update_data:
        update_data['model_config'] = update_data.pop('llm_config')
    
    character = character_manager.update_character(character_id, update_data)
    if not character:
        return {"error": "Character not found"}, 404
    return character

@app.delete("/api/characters/{character_id}")
async def delete_character(character_id: str):
    """Delete a character card."""
    success = character_manager.delete_character(character_id)
    if not success:
        return {"error": "Character not found"}, 404
    return {"success": True}

@app.get("/api/models")
async def get_available_models():
    """Get available models by provider - PRIVACY-FIRST ORDERING."""
    return character_manager.get_available_models()

@app.get("/api/models/recommendations")
async def get_model_recommendations():
    """Get model recommendations by use case - PRIVACY-FIRST."""
    return character_manager.get_model_recommendations()

@app.get("/api/models/privacy")
async def get_privacy_info():
    """Get privacy information for different providers."""
    return character_manager.get_privacy_info()

@app.get("/api/models/openrouter")
async def get_openrouter_models():
    """Get available models from OpenRouter."""
    models = character_manager.get_openrouter_models()
    return {
        "models": models,
        "count": len(models),
        "requires_api_key": not bool(os.getenv("OPENROUTER_API_KEY")),
        "privacy_note": "OpenRouter processes data through cloud providers. Use Ollama for complete privacy."
    }

@app.get("/api/categories")
async def get_categories():
    """Get all available categories."""
    return character_manager.get_categories()

@app.get("/api/tags")
async def get_tags():
    """Get all available tags."""
    return character_manager.get_tags()

@app.post("/api/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Send a message to a character and get a response."""
    try:
        # Get character
        character = character_manager.get_character(request.character_id)
        if not character:
            return {"error": "Character not found"}, 404
        
        # Get or create conversation
        conversation = conversation_service.get_or_create_conversation(request.character_id, db)
        
        # Store the user message
        user_message = conversation_service.add_message(
            conversation.id, 
            request.message, 
            "user", 
            db
        )
        
        # Update character usage
        character_manager.update_character(request.character_id, {
            'last_used': datetime.now().isoformat(),
            'conversation_count': character.get('conversation_count', 0) + 1,
            'total_messages': character.get('total_messages', 0) + 1
        })
        
        # Get conversation context for the LLM
        context_messages = memory_service.get_context(
            conversation_id=conversation.id,
            current_message=request.message,
            db=db
        )
        
        # Prepare messages for the LLM (system prompt + context + current message)
        llm_messages = []
        
        # Add system prompt
        llm_messages.append({
            "role": "system",
            "content": character['system_prompt']
        })
        
        # Add conversation context
        for context_msg in context_messages:
            llm_messages.append({
                "role": context_msg["role"],
                "content": context_msg["content"]
            })
        
        # Add current user message
        llm_messages.append({
            "role": "user",
            "content": request.message
        })
        
        # Generate response using the character's model configuration
        model_config = character['model_config']
        provider = model_config.get('provider', 'ollama')
        
        # Log privacy information
        if provider == 'ollama':
            logger.info(f"Using LOCAL Ollama for {character['name']} - FULLY PRIVATE")
        else:
            logger.info(f"Using CLOUD provider {provider} for {character['name']} - data may be processed externally")
        
        # Log context information
        logger.info(f"Generating response for {character['name']} with {len(context_messages)} context messages")
        
        response = llm_client.generate_response_with_config(
            messages=llm_messages,
            system_prompt=character['system_prompt'],
            model_config=model_config
        )
        
        # Store the assistant's response
        assistant_message = conversation_service.add_message(
            conversation.id, 
            response, 
            "assistant", 
            db
        )
        
        logger.info(f"Generated response for {character['name']}: {response[:100]}...")
        
        return ChatResponse(
            response=response,
            character_name=character['name'],
            character_id=character['id']
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        db.rollback()
        return {"error": str(e)}, 500

@app.get("/api/conversations")
async def list_conversations(character_id: Optional[str] = None, db: Session = Depends(get_db)):
    """List conversations, optionally filtered by character."""
    try:
        if character_id:
            conversations = conversation_service.get_character_conversations(character_id, db)
        else:
            # Get all conversations (this would need to be implemented in the service)
            conversations = []
            # For now, return empty list for all conversations
            # TODO: Implement get_all_conversations in conversation_service
        
        return conversations
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        return {"error": str(e)}, 500

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Get a specific conversation with its messages."""
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            return {"error": "Conversation not found"}, 404
        
        messages = conversation.get_messages()
        
        return {
            "id": conversation.id,
            "character_id": conversation.conversation_data.get("character_id"),
            "started_at": conversation.started_at.isoformat(),
            "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
            "is_active": conversation.is_active(),
            "messages": [msg.to_dict() for msg in messages]
        }
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        return {"error": str(e)}, 500

@app.get("/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int, 
    limit: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get messages from a specific conversation."""
    try:
        messages = conversation_service.get_conversation_messages(conversation_id, limit, db)
        return messages
    except Exception as e:
        logger.error(f"Error getting conversation messages: {e}")
        return {"error": str(e)}, 500

@app.post("/api/conversations/{conversation_id}/end")
async def end_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """End a conversation."""
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            return {"error": "Conversation not found"}, 404
        
        if conversation.ended_at:
            return {"error": "Conversation already ended"}, 400
        
        conversation.end()
        db.commit()
        
        # Remove from active conversations if present
        character_id = conversation.conversation_data.get("character_id")
        if character_id and character_id in conversation_service.active_conversations:
            del conversation_service.active_conversations[character_id]
        
        return {"success": True, "message": "Conversation ended successfully"}
    except Exception as e:
        logger.error(f"Error ending conversation: {e}")
        db.rollback()
        return {"error": str(e)}, 500

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Delete a conversation and all its messages."""
    try:
        success = conversation_service.delete_conversation(conversation_id, db)
        if not success:
            return {"error": "Conversation not found"}, 404
        
        return {"success": True, "message": "Conversation deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        return {"error": str(e)}, 500

@app.get("/api/characters/{character_id}/conversations")
async def get_character_conversations(character_id: str, db: Session = Depends(get_db)):
    """Get all conversations for a specific character."""
    try:
        conversations = conversation_service.get_character_conversations(character_id, db)
        return conversations
    except Exception as e:
        logger.error(f"Error getting character conversations: {e}")
        return {"error": str(e)}, 500

@app.post("/api/characters/{character_id}/conversations/end")
async def end_character_conversation(character_id: str, db: Session = Depends(get_db)):
    """End the active conversation for a character."""
    try:
        success = conversation_service.end_conversation(character_id, db)
        if not success:
            return {"error": "No active conversation found"}, 404
        
        return {"success": True, "message": "Conversation ended successfully"}
    except Exception as e:
        logger.error(f"Error ending character conversation: {e}")
        return {"error": str(e)}, 500

@app.get("/api/conversations/{conversation_id}/search")
async def search_conversation(
    conversation_id: int,
    q: str,
    limit: Optional[int] = 10,
    db: Session = Depends(get_db)
):
    """Search conversation history for messages matching a query."""
    try:
        messages = memory_service.search_conversation(
            conversation_id=conversation_id,
            query=q,
            db=db,
            limit=limit
        )
        
        return {
            "conversation_id": conversation_id,
            "query": q,
            "results": messages,
            "count": len(messages)
        }
    except Exception as e:
        logger.error(f"Error searching conversation {conversation_id}: {e}")
        return {"error": str(e)}, 500

@app.get("/api/conversations/{conversation_id}/summary")
async def get_conversation_summary(conversation_id: int, db: Session = Depends(get_db)):
    """Get a summary of a conversation."""
    try:
        summary = memory_service.get_conversation_summary(conversation_id, db)
        return summary
    except Exception as e:
        logger.error(f"Error getting conversation summary {conversation_id}: {e}")
        return {"error": str(e)}, 500

@app.get("/api/conversations/{conversation_id}/context")
async def get_conversation_context(
    conversation_id: int,
    message: Optional[str] = "",
    context_window: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get conversation context (for debugging/testing purposes)."""
    try:
        context = memory_service.get_context(
            conversation_id=conversation_id,
            current_message=message,
            context_window=context_window,
            db=db
        )
        
        return {
            "conversation_id": conversation_id,
            "current_message": message,
            "context_window": context_window or memory_service.default_context_window,
            "context_messages": context,
            "count": len(context)
        }
    except Exception as e:
        logger.error(f"Error getting conversation context {conversation_id}: {e}")
        return {"error": str(e)}, 500

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080) 
from fastapi import FastAPI, Request, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from .core.templates import render_template
from .core.static import mount_static_files
from .core.character_manager import character_manager
from .core.llm_client import llm_client
from .core.database import create_tables, get_db
from .core.auth import require_session_auth, get_current_user_from_session
from .core.settings_service import settings_service
from .core.conversation_manager import ConversationManager
from .routes.auth import router as auth_router
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import os
from starlette.responses import RedirectResponse
import json
import re
from fastapi import APIRouter
from fastapi.responses import JSONResponse

# --- Fixed trait and comm style keys ---
FIXED_TRAITS = [
    'Empathy',
    'Assertiveness',
    'Adaptability',
    'Creativity',
    'Resilience',
    'Self-discipline',
    'Sociability',
    'Integrity',
    'Curiosity'
]
FIXED_COMM_STYLES = [
    'Directness',
    'Warmth',
    'Formality',
    'Assertiveness',
    'Empathy',
    'Humor'
]

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

# Include routers
app.include_router(auth_router)

# Initialize conversation manager
conversation_manager = ConversationManager()

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    create_tables()
    logger.info("Database tables created")

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    character_id: str
    session_id: Optional[str] = None  # Optional session ID for continuing conversations

class ChatResponse(BaseModel):
    response: str
    character_name: str
    character_id: str
    session_id: str
    character_version: int
    migration_available: bool = False

class CharacterCreateRequest(BaseModel):
    name: str
    personality: str
    system_prompt: str
    role: str = "assistant"
    category: str = "General"
    backstory: str = ""
    gender: str = ""
    tags: List[str] = []
    traits: Optional[Dict[str, float]] = None  # Dynamic traits
    communication_style: Optional[Dict[str, float]] = None  # Dynamic comm styles
    llm_config: Optional[Dict[str, Any]] = None
    llm_model_config: Optional[Dict[str, Any]] = None
    llm_provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    repeat_penalty: Optional[float] = 1.1
    top_k: Optional[int] = 40

class CharacterUpdateRequest(BaseModel):
    name: Optional[str] = None
    personality: Optional[str] = None
    system_prompt: Optional[str] = None
    traits: Optional[Dict[str, float]] = None
    communication_style: Optional[Dict[str, float]] = None
    llm_config: Optional[Dict[str, Any]] = None
    role: Optional[str] = None
    category: Optional[str] = None
    backstory: Optional[str] = None
    gender: Optional[str] = None
    tags: Optional[List[str]] = None

class SuggestTraitsRequest(BaseModel):
    backstory: str
    name: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None

class SuggestTraitsResponse(BaseModel):
    traits: Dict[str, float]
    communication_style: Dict[str, float]
    raw_response: str

# Routes
@app.get("/")
async def index(request: Request, db = Depends(get_db)):
    """Main application page."""
    # Check if user is authenticated
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    return await render_template(request, "index", user=current_user)

@app.get("/chat")
async def chat_page(request: Request, db = Depends(get_db)):
    """Chat interface page."""
    # Check if user is authenticated
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    characters = character_manager.list_characters()
    categories = character_manager.get_categories()
    active_personality = None  # No active personality by default
    
    return await render_template(request, "chat/index", 
                                personalities=characters, 
                                categories=categories,
                                active_personality=active_personality,
                                user=current_user)

@app.get("/characters")
async def characters_page(request: Request, db = Depends(get_db)):
    """Character management page."""
    # Check if user is authenticated
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
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
                         privacy_info=privacy_info,
                         user=current_user)

@app.get("/settings")
async def settings_page(request: Request, db = Depends(get_db)):
    """Settings page."""
    # Check if user is authenticated
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    return await render_template(request, "settings", user=current_user)

@app.get("/config")
async def config_page(request: Request, db = Depends(get_db)):
    """Configuration page."""
    # Check if user is authenticated
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    return await render_template(request, "config", user=current_user)

@app.get("/personality")
async def personality_list_page(request: Request, db = Depends(get_db)):
    """Personality list page."""
    # Check if user is authenticated
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    personalities = character_manager.list_characters()
    return await render_template(request, "personality/list", personalities=personalities, user=current_user)

@app.get("/personality/create")
async def create_personality_page(request: Request, db = Depends(get_db)):
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    # Render the creation form with an empty personality
    return await render_template(request, "personality/edit", personality={}, user=current_user)

@app.get("/personality/edit/{personality_id}")
async def edit_personality_page(personality_id: str, request: Request, db = Depends(get_db)):
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    # Fetch the personality by id
    personality = character_manager.get_character(personality_id)
    if not personality:
        return RedirectResponse(url="/personality", status_code=302)
    return await render_template(request, "personality/edit", personality=personality, user=current_user)

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

    # Normalize traits and communication_style to 0-1 scale if needed
    def normalize_dict(d):
        if not d:
            return d
        norm = {}
        for k, v in d.items():
            if v > 1.0:
                norm[k] = float(v) / 10.0
            else:
                norm[k] = float(v)
        return norm
    if 'traits' in character_data:
        character_data['traits'] = normalize_dict(character_data['traits'])
    if 'communication_style' in character_data:
        character_data['communication_style'] = normalize_dict(character_data['communication_style'])

    # Handle different data formats for model config
    if 'llm_model_config' in character_data and character_data['llm_model_config']:
        character_data['model_config'] = character_data.pop('llm_model_config')
    elif 'llm_config' in character_data and character_data['llm_config']:
        character_data['model_config'] = character_data.pop('llm_config')
    else:
        model_config = {
            'provider': character_data.get('llm_provider', 'ollama'),
            'model': character_data.get('model', 'llama3:8b'),
            'temperature': character_data.get('temperature', 0.7),
            'top_p': character_data.get('top_p', 0.9),
            'repeat_penalty': character_data.get('repeat_penalty', 1.1),
            'top_k': character_data.get('top_k', 40)
        }
        character_data['model_config'] = model_config
        for field in ['llm_provider', 'model', 'temperature', 'top_p', 'repeat_penalty', 'top_k']:
            character_data.pop(field, None)

    if 'model_config' in character_data and 'provider' not in character_data['model_config']:
        character_data['model_config']['provider'] = 'ollama'
        logger.info("Defaulting to Ollama provider for privacy")

    character = character_manager.create_character(character_data)
    if not character:
        return {"error": "Failed to create character"}, 400

    # Create initial character version for conversation history
    initial_version = conversation_manager.create_character_version(
        character, 
        change_reason="Initial character creation"
    )

    return {
        "character": character,
        "version": initial_version.version
    }

@app.put("/api/characters/{character_id}")
async def update_character(character_id: str, request: CharacterUpdateRequest):
    """Update an existing character card and create a new version."""
    try:
        character = character_manager.get_character(character_id)
        if not character:
            return {"error": "Character not found"}, 404
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        # Normalize traits and communication_style to 0-1 scale if needed
        def normalize_dict(d):
            if not d:
                return d
            norm = {}
            for k, v in d.items():
                if v > 1.0:
                    norm[k] = float(v) / 10.0
                else:
                    norm[k] = float(v)
            return norm
        if 'traits' in update_data:
            update_data['traits'] = normalize_dict(update_data['traits'])
        if 'communication_style' in update_data:
            update_data['communication_style'] = normalize_dict(update_data['communication_style'])
        if 'llm_config' in update_data:
            update_data['model_config'] = update_data.pop('llm_config')
        updated_character = character_manager.update_character(character_id, update_data)
        if not updated_character:
            return {"error": "Failed to update character"}, 400
        change_reason = "Character updated via API"
        if 'system_prompt' in update_data:
            change_reason = "System prompt updated"
        elif 'personality' in update_data:
            change_reason = "Personality updated"
        new_version = conversation_manager.create_character_version(
            updated_character, 
            change_reason=change_reason
        )
        return {
            "message": "Character updated successfully", 
            "character": updated_character,
            "new_version": new_version.version,
            "change_reason": change_reason
        }
    except Exception as e:
        logger.error(f"Error updating character: {e}")
        return {"error": str(e)}, 500

@app.delete("/api/characters/{character_id}")
async def delete_character(character_id: str):
    """Delete a character card."""
    success = character_manager.delete_character(character_id)
    if not success:
        return {"error": "Character not found"}, 404
    return {"success": True}

@app.post("/api/conversations/{session_id}/migrate")
async def migrate_conversation(session_id: str, request: Request, db = Depends(get_db)):
    """Migrate a conversation session to the latest character version."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            return {"error": "Authentication required"}, 401
        
        # Get request body
        body = await request.json()
        user_choice = body.get("choice", "auto")  # "auto", "new_session", or "keep_old"
        
        if user_choice == "keep_old":
            return {"message": "Session kept on old version", "migrated": False}
        
        success = conversation_manager.migrate_session(session_id, user_choice)
        if not success:
            return {"error": "Failed to migrate session"}, 400
        
        return {
            "message": "Session migrated successfully", 
            "migrated": True,
            "choice": user_choice
        }
        
    except Exception as e:
        logger.error(f"Error migrating conversation: {e}")
        return {"error": str(e)}, 500

@app.get("/api/conversations/{session_id}/history")
async def get_conversation_history(session_id: str, request: Request, db = Depends(get_db)):
    """Get conversation history for a session."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            return {"error": "Authentication required"}, 401
        
        session = conversation_manager.get_session(session_id)
        if not session:
            return {"error": "Session not found"}, 404
        
        # Check if user owns this session
        if str(session.user_id) != str(current_user.id):
            return {"error": "Access denied"}, 403
        
        history = conversation_manager.get_conversation_history(session_id)
        
        # Check for migration availability
        update_event = conversation_manager.check_version_compatibility(session_id)
        migration_available = update_event is not None
        
        return {
            "session_id": session_id,
            "character_id": session.character_id,
            "character_version": session.character_version,
            "message_count": session.message_count,
            "migration_available": migration_available,
            "history": [msg.dict() for msg in history]
        }
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return {"error": str(e)}, 500

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
async def chat(request: ChatRequest, request_obj: Request, db = Depends(get_db)):
    """Send a message to a character and get a response with conversation memory."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request_obj, db)
        if not current_user:
            return {"error": "Authentication required"}, 401
        
        # Get character
        character = character_manager.get_character(request.character_id)
        if not character:
            return {"error": "Character not found"}, 404
        
        # Handle session management
        session_id = request.session_id
        migration_available = False
        
        if session_id:
            # Continue existing session
            session = conversation_manager.get_session(session_id)
            if not session or session.character_id != request.character_id:
                session_id = None  # Invalid session, create new one
        
        if not session_id:
            # Create new session
            session = conversation_manager.create_conversation_session(
                request.character_id, 
                str(current_user.id)
            )
            session_id = session.session_id
        
        # Check for character updates
        update_event = conversation_manager.check_version_compatibility(session_id)
        if update_event:
            migration_available = True
            logger.info(f"Character {request.character_id} has been updated, migration available")
        
        # Get conversation history for context
        history = conversation_manager.get_conversation_history(session_id, limit=10)
        messages = []
        
        # Add system prompt
        messages.append({"role": "system", "content": character['system_prompt']})
        
        # Add conversation history
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        
        # Add current message
        messages.append({"role": "user", "content": request.message})
        
        # Generate response using the character's model configuration
        model_config = character['model_config']
        provider = model_config.get('provider', 'ollama')
        
        # Log privacy information
        if provider == 'ollama':
            logger.info(f"Using LOCAL Ollama for {character['name']} - FULLY PRIVATE")
        else:
            logger.info(f"Using CLOUD provider {provider} for {character['name']} - data may be processed externally")
        
        response = llm_client.generate_response_with_config(
            messages=messages,
            system_prompt=character['system_prompt'],
            model_config=model_config
        )
        
        # Save messages to conversation history
        conversation_manager.save_message(session_id, "user", request.message)
        conversation_manager.save_message(session_id, "assistant", response)
        
        # Update character usage
        character_manager.update_character(request.character_id, {
            'last_used': datetime.now().isoformat(),
            'conversation_count': character.get('conversation_count', 0) + 1,
            'total_messages': character.get('total_messages', 0) + 1
        })
        
        logger.info(f"Generated response for {character['name']}: {response[:100]}...")
        
        return ChatResponse(
            response=response,
            character_name=character['name'],
            character_id=character['id'],
            session_id=session_id,
            character_version=session.character_version,
            migration_available=migration_available
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return {"error": str(e)}, 500

@app.post("/api/suggest_system_prompt")
async def suggest_system_prompt(request: Request):
    data = await request.json()
    backstory = data.get('backstory', '')
    category = data.get('category', '')
    # Prompt for the LLM
    prompt = f"""
Given the following backstory and category for a character, generate a concise, effective system prompt for an AI assistant to roleplay as this character. The system prompt should:
- Clearly establish the character's role, personality, and communication style
- Be 1-3 sentences
- Use natural language, not JSON
- Do NOT include any explanation, prelude, or commentary—just the system prompt itself.

Backstory: {backstory}
Category: {category}
"""
    model_config = {"provider": "ollama", "model": "llama3:8b", "temperature": 0.7, "max_tokens": 128}
    response = llm_client.generate_response_with_config(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are an expert at writing system prompts for AI roleplay based on character backstories and categories.",
        model_config=model_config
    )
    # Extract only the quoted or main instruction
    import re
    system_prompt_text = response.strip()
    # Try to extract quoted string
    quoted = re.search(r'"([^"]{20,})"', system_prompt_text)
    if quoted:
        system_prompt_text = quoted.group(1).strip()
    else:
        # Remove prelude lines (e.g. 'Here is ...') and explanations
        lines = [l.strip() for l in system_prompt_text.splitlines() if l.strip()]
        # Find the first line that looks like a persona instruction
        for line in lines:
            if len(line) > 20 and not line.lower().startswith(('here is', 'this prompt', 'the above', 'as requested', 'explanation', 'note:')):
                system_prompt_text = line
                break
    return JSONResponse({"system_prompt": system_prompt_text})

@app.post("/api/suggest_traits", response_model=SuggestTraitsResponse)
async def suggest_traits(request: SuggestTraitsRequest = Body(...)):
    """Suggest personality traits and communication style from a backstory using the LLM."""
    prompt = f"""
Given the following backstory for a character, suggest a set of core personality traits (as a dictionary of trait name to value from 0.0 to 1.0) and a communication style (as a dictionary of style name to value from 0.0 to 1.0). Only return valid JSON with two keys: 'traits' and 'communication_style'.

IMPORTANT: Only use the following traits: {', '.join(FIXED_TRAITS)}. Only use the following communication styles: {', '.join(FIXED_COMM_STYLES)}. If you don't have enough information for a trait/style, set it to 0.5.

Backstory: {request.backstory}
Category: {request.category or ''}
"""
    model_config = {"provider": "ollama", "model": "llama3:8b", "temperature": 0.7, "max_tokens": 512}
    response = llm_client.generate_response_with_config(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are an expert at analyzing character backstories and suggesting realistic, balanced personality traits and communication styles in JSON format.",
        model_config=model_config
    )
    traits = {}
    communication_style = {}
    try:
        data = json.loads(response)
        traits = data.get("traits", {})
        communication_style = data.get("communication_style", {})
    except json.JSONDecodeError:
        try:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                data = json.loads(json_str)
                traits = data.get("traits", {})
                communication_style = data.get("communication_style", {})
            else:
                json_match = re.search(r'\{.*?"traits".*?"communication_style".*?\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    traits = data.get("traits", {})
                    communication_style = data.get("communication_style", {})
        except Exception:
            traits = {}
            communication_style = {}
    # Only return fixed keys
    traits_out = {k: float(traits.get(k, 0.5)) for k in FIXED_TRAITS}
    comm_out = {k: float(communication_style.get(k, 0.5)) for k in FIXED_COMM_STYLES}
    return SuggestTraitsResponse(traits=traits_out, communication_style=comm_out, raw_response=response)

# Settings API endpoints
class LLMConfigRequest(BaseModel):
    provider: str
    model: Optional[str] = None
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    privacy_mode: Optional[str] = "local_only"

class TestConnectionRequest(BaseModel):
    provider: str
    config: Dict[str, Any]

@app.get("/api/settings/llm")
async def get_llm_settings(request: Request, db = Depends(get_db)):
    """Get current LLM settings for the authenticated user."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return {"error": "Authentication required"}, 401
    
    config = settings_service.get_llm_config(current_user.id, db)
    
    # Create a secure copy without sensitive data for return
    secure_config = config.copy()
    if 'api_key' in secure_config:
        # Just indicate if the API key exists
        secure_config['api_key'] = secure_config['api_key'] is not None
    
    return secure_config

@app.post("/api/settings/llm")
async def update_llm_settings(request: LLMConfigRequest, request_obj: Request, db = Depends(get_db)):
    """Update LLM settings for the authenticated user."""
    current_user = await get_current_user_from_session(request_obj, db)
    if not current_user:
        return {"error": "Authentication required"}, 401
    
    config = request.dict()
    success = settings_service.update_llm_config(current_user.id, db, config)
    
    if success:
        return {"success": True, "message": "Settings updated successfully"}
    else:
        return {"success": False, "error": "Failed to update settings"}, 400

@app.get("/api/settings/llm/models")
async def get_llm_models(provider: str):
    """Get available models for a specific LLM provider."""
    models = settings_service.get_available_models(provider)
    return {
        "provider": provider,
        "models": models,
        "count": len(models)
    }

@app.post("/api/settings/llm/test")
async def test_llm_connection(request: TestConnectionRequest):
    """Test connection to an LLM provider."""
    result = settings_service.test_provider_connection(request.provider, request.config)
    return result

@app.get("/api/settings/user")
async def get_user_settings(request: Request, db = Depends(get_db)):
    """Get all user settings for the authenticated user."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return {"error": "Authentication required"}, 401
    
    settings = settings_service.get_user_settings(current_user.id, db)
    if not settings:
        return {"message": "No settings found, using defaults"}
    
    # Return settings without sensitive data
    return {
        "theme": settings.theme,
        "language": settings.language,
        "privacy_mode": settings.privacy_mode,
        "default_llm_provider": settings.default_llm_provider,
        "default_model": settings.default_model
    }

@app.put("/api/settings/user")
async def update_user_settings(request: Request, db = Depends(get_db)):
    """Update user settings for the authenticated user."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return {"error": "Authentication required"}, 401
    
    data = await request.json()
    settings = settings_service.update_user_settings(current_user.id, db, **data)
    
    if settings:
        return {"success": True, "message": "Settings updated successfully"}
    else:
        return {"success": False, "error": "Failed to update settings"}, 400

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080) 
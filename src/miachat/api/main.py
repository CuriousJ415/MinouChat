from fastapi import FastAPI, Request, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from .core.templates import render_template
from .core.static import mount_static_files
from .core.character_manager import character_manager
from .core.llm_client import llm_client
from .core.database import create_tables, get_db
from .core.auth import require_session_auth, get_current_user_from_session
from .routes.auth import router as auth_router
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import os
from starlette.responses import RedirectResponse
import json
import re

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
    return await render_template(request, "chat/index", characters=characters, user=current_user)

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
async def chat(request: ChatRequest):
    """Send a message to a character and get a response."""
    try:
        # Get character
        character = character_manager.get_character(request.character_id)
        if not character:
            return {"error": "Character not found"}, 404
        
        # Update character usage
        character_manager.update_character(request.character_id, {
            'last_used': datetime.now().isoformat(),
            'conversation_count': character.get('conversation_count', 0) + 1,
            'total_messages': character.get('total_messages', 0) + 1
        })
        
        # Generate response using the character's model configuration
        model_config = character['model_config']
        provider = model_config.get('provider', 'ollama')
        
        # Log privacy information
        if provider == 'ollama':
            logger.info(f"Using LOCAL Ollama for {character['name']} - FULLY PRIVATE")
        else:
            logger.info(f"Using CLOUD provider {provider} for {character['name']} - data may be processed externally")
        
        response = llm_client.generate_response_with_config(
            messages=[{"role": "user", "content": request.message}],
            system_prompt=character['system_prompt'],
            model_config=model_config
        )
        
        logger.info(f"Generated response for {character['name']}: {response[:100]}...")
        
        return ChatResponse(
            response=response,
            character_name=character['name'],
            character_id=character['id']
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return {"error": str(e)}, 500

@app.post("/api/suggest_traits", response_model=SuggestTraitsResponse)
async def suggest_traits(request: SuggestTraitsRequest = Body(...)):
    """Suggest personality traits and communication style from a backstory using the LLM."""
    # Build a prompt for the LLM
    prompt = f"""
Given the following backstory for a character, suggest a set of core personality traits (as a dictionary of trait name to value from 0.0 to 1.0) and a communication style (as a dictionary of style name to value from 0.0 to 1.0). Only return valid JSON with two keys: 'traits' and 'communication_style'.

Backstory: {request.backstory}
"""
    # Use Ollama for now
    model_config = {"provider": "ollama", "model": "llama3:8b", "temperature": 0.7, "max_tokens": 512}
    response = llm_client.generate_response_with_config(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are an expert at analyzing character backstories and suggesting personality traits and communication styles in JSON format.",
        model_config=model_config
    )
    # Try to parse the response as JSON
    traits = {}
    communication_style = {}
    try:
        # First try direct JSON parsing
        data = json.loads(response)
        traits = data.get("traits", {})
        communication_style = data.get("communication_style", {})
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        try:
            # Look for JSON inside ```json or ``` blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                data = json.loads(json_str)
                traits = data.get("traits", {})
                communication_style = data.get("communication_style", {})
            else:
                # Try to find JSON object in the text
                json_match = re.search(r'\{.*?"traits".*?"communication_style".*?\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    traits = data.get("traits", {})
                    communication_style = data.get("communication_style", {})
        except Exception:
            # If all parsing fails, return empty dicts
            traits = {}
            communication_style = {}
    return SuggestTraitsResponse(traits=traits, communication_style=communication_style, raw_response=response)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080) 
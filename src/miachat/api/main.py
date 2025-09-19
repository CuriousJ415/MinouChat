from fastapi import FastAPI, Request, Depends, Body, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from .core.templates import render_template
from .core.static import mount_static_files
from .core.character_manager import character_manager
from .core.llm_client import llm_client
from ..database.config import get_db
from ..database.models import Base
from .core.auth import require_session_auth, get_current_user_from_session
from .core.settings_service import settings_service
from .core.conversation_manager import ConversationManager
from .core.rag_service import rag_service
from .routes.auth import router as auth_router
from .routes.documents import router as documents_router
from .routes.setup import router as setup_router
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

def _should_use_comprehensive_analysis(message: str) -> bool:
    """Detect if a message requires comprehensive document analysis.

    Args:
        message: User message to analyze

    Returns:
        True if comprehensive analysis should be used
    """
    # Convert to lowercase for analysis
    msg_lower = message.lower()

    # Phrases that indicate comprehensive document analysis
    comprehensive_indicators = [
        'analyze', 'review', 'summarize', 'summary', 'document', 'report', 'look at',
        'take a look', 'examine', 'study', 'assess', 'evaluate', 'overall', 'complete',
        'full', 'entire', 'whole', 'comprehensive', 'thorough', 'understand', 'learn',
        'tell me about', 'what does', 'what is', 'overview', 'breakdown', 'findings'
    ]

    # Check if any comprehensive indicators are present
    for indicator in comprehensive_indicators:
        if indicator in msg_lower:
            return True

    # If message is very general or short, likely needs comprehensive analysis
    if len(msg_lower.strip()) < 50 and any(word in msg_lower for word in ['document', 'file', 'report', 'it']):
        return True

    return False

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
app.include_router(documents_router)
app.include_router(setup_router)

# Initialize conversation manager
conversation_manager = ConversationManager()

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    from ..database.config import db_config
    db_config.create_tables()
    logger.info("Database tables created")

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    character_id: str
    session_id: Optional[str] = None  # Optional session ID for continuing conversations
    use_documents: bool = True  # Whether to include document context (RAG)

class ChatResponse(BaseModel):
    response: str
    character_name: str
    character_id: str
    session_id: str
    character_version: int
    migration_available: bool = False
    document_context_used: bool = False
    sources: List[Dict[str, Any]] = []
    context_summary: Optional[str] = None  # Compact version for UI display
    context_summary_full: Optional[str] = None  # Full version for detailed view

class CharacterCreateRequest(BaseModel):
    name: str
    persona: str
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
    persona: Optional[str] = None
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
    """Main application page with setup detection."""
    # Check if user is authenticated
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        # Show landing page for unauthenticated users
        return await render_template(request, "landing", user=None)
    
    # Check if setup is needed (for authenticated users)
    try:
        from .core.setup_service import setup_service
        assessment = await setup_service.perform_full_assessment()
        
        # Redirect to setup if system needs configuration
        if assessment.overall_status in ["broken", "needs_setup"] or assessment.setup_required:
            return RedirectResponse(url="/setup", status_code=302)
    except Exception as e:
        logger.warning(f"Setup check failed: {e}")
        # Continue to dashboard if setup check fails
    
    # Show dashboard for authenticated users
    return await render_template(request, "dashboard", user=current_user)

@app.get("/dashboard")
async def dashboard_page(request: Request, db = Depends(get_db)):
    """Dashboard page for authenticated users."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    return await render_template(request, "dashboard", user=current_user)

@app.get("/chat")
async def chat_page(request: Request, db = Depends(get_db)):
    """Chat interface page."""
    # Check if user is authenticated
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    characters = character_manager.list_characters()
    categories = character_manager.get_categories()
    active_persona = None  # No active persona by default
    
    return await render_template(request, "chat/index", 
                                personas=characters, 
                                categories=categories,
                                active_persona=active_persona,
                                user=current_user)

@app.get("/characters")
async def characters_page(request: Request, db = Depends(get_db)):
    """Character management page."""
    # Check if user is authenticated
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    characters = character_manager.list_characters()
    available_models = character_manager.get_available_models("cloud_allowed")
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

@app.get("/documents")
async def documents_page(request: Request, db = Depends(get_db)):
    """Document management page."""
    # Check if user is authenticated
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    return await render_template(request, "documents", user=current_user)

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

@app.get("/test-image")
async def test_image_page(request: Request):
    """Test page for hero image."""
    return await render_template(request, "test-image")

@app.get("/landing")
async def landing_page(request: Request):
    """Force show landing page even when logged in."""
    return await render_template(request, "landing", user=None)

@app.get("/setup")
async def setup_wizard_page(request: Request, db = Depends(get_db)):
    """Setup wizard for first-time configuration."""
    # Check if user is already authenticated
    current_user = await get_current_user_from_session(request, db)
    
    if not current_user:
        # Create or get a default setup user for anonymous setup
        from .core.auth import get_or_create_setup_user, login_user_session
        setup_user = get_or_create_setup_user(db)
        if setup_user:
            await login_user_session(setup_user, request)
            current_user = setup_user
    
    return await render_template(request, "setup/wizard", user=current_user)

@app.get("/favicon.ico")
async def favicon():
    """Serve a simple favicon to prevent 404 errors"""
    from fastapi.responses import Response
    # Return a minimal 1x1 transparent PNG
    favicon_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00\x7f\x06\xde\x02\x00\x00\x00\x00IEND\xaeB`\x82'
    return Response(content=favicon_data, media_type="image/x-icon")

@app.get("/persona")
async def persona_list_page(request: Request, db = Depends(get_db)):
    """Persona list page."""
    # Check if user is authenticated
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    personas = character_manager.list_characters()
    return await render_template(request, "persona/list", personas=personas, user=current_user)

@app.get("/persona/create")
async def create_persona_page(request: Request, db = Depends(get_db)):
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    # Render the creation form with an empty persona
    return await render_template(request, "persona/edit", persona={}, user=current_user)

@app.get("/persona/edit/{persona_id}")
async def edit_persona_page(persona_id: str, request: Request, db = Depends(get_db)):
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    # Fetch the persona by id
    persona = character_manager.get_character(persona_id)
    if not persona:
        return RedirectResponse(url="/persona", status_code=302)
    return await render_template(request, "persona/edit", persona=persona, user=current_user)

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

@app.get("/api/characters/examples")
async def get_example_characters():
    """Get available example characters that users can import."""
    examples = character_manager.get_example_characters()
    return {
        "examples": examples,
        "count": len(examples),
        "description": "Example characters that can be imported as templates"
    }

@app.post("/api/characters/examples/{example_id}/import")
async def import_example_character(example_id: str, request: Request, db = Depends(get_db)):
    """Import an example character as a new character."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            return {"error": "Authentication required"}, 401
        
        # Get request body for custom name
        body = await request.json() if request.method == "POST" else {}
        new_name = body.get("name")
        
        # Import the example character
        character = character_manager.import_example_character(example_id, new_name)
        if not character:
            return {"error": "Example character not found or import failed"}, 404
        
        # Create initial character version for conversation history
        initial_version = conversation_manager.create_character_version(
            character, 
            change_reason=f"Imported from example: {example_id}"
        )
        
        return {
            "success": True,
            "character": character,
            "version": initial_version.version,
            "message": f"Successfully imported {character['name']}"
        }
        
    except Exception as e:
        logger.error(f"Error importing example character: {e}")
        return {"error": str(e)}, 500

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
        elif 'persona' in update_data:
            change_reason = "Persona updated"
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
async def delete_character(character_id: str, db = Depends(get_db)):
    """Delete a character card and all associated memories/conversations (but not audit logs)."""
    # Delete the character file
    success = character_manager.delete_character(character_id)
    if not success:
        return {"error": "Character not found"}, 404

    # Delete all conversations and memories for this character
    # (Assume conversation_manager has a method to get all sessions or conversations for a character)
    try:
        # If using ConversationService with DB:
        from .core.conversation_service import conversation_service
        conversations = conversation_service.get_character_conversations(character_id, db)
        for conv in conversations:
            conversation_service.delete_conversation(conv["id"], db)
    except Exception as e:
        # Log but do not fail deletion if memory cleanup fails
        logger.error(f"Error deleting conversations for character {character_id}: {e}")

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
async def get_available_models(privacy_mode: str = "local_only"):
    """Get available models by provider - PRIVACY-FIRST ORDERING."""
    return character_manager.get_available_models(privacy_mode)

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
        
        # Initialize RAG context variables
        rag_context = {}
        enhanced_prompt = None
        document_context_used = False
        sources = []
        context_summary = None
        
        # Get enhanced context if document RAG is enabled
        if request.use_documents:
            try:
                # Detect if this is a comprehensive document analysis request
                comprehensive_analysis = _should_use_comprehensive_analysis(request.message)

                # Get RAG context
                rag_context = rag_service.get_enhanced_context(
                    user_message=request.message,
                    user_id=current_user.id,
                    conversation_id=session_id,
                    character_id=request.character_id,
                    include_conversation_history=True,
                    include_documents=True,
                    comprehensive_analysis=comprehensive_analysis,
                    db=db
                )
                
                if rag_context.get('document_chunks'):
                    document_context_used = True
                    sources = rag_context.get('sources', [])
                    context_summary = rag_context.get('context_summary_compact', '')  # Use compact for display

                    # Create enhanced prompt with document context (use full context for LLM)
                    enhanced_prompt = rag_service.format_rag_prompt(
                        user_message=request.message,
                        context=rag_context,
                        character_instructions=character['system_prompt']
                    )

                    logger.info(f"RAG enabled for {character['name']}: {len(rag_context.get('document_chunks', []))} document chunks included")
                
            except Exception as e:
                logger.warning(f"RAG context generation failed, falling back to regular chat: {e}")
        
        # Build messages array
        messages = []

        # Add system prompt (always)
        system_prompt_text = character.get('system_prompt') or character.get('persona', 'You are a helpful AI assistant.')
        messages.append({"role": "system", "content": system_prompt_text})

        # Try to use semantic memory service for intelligent context retrieval
        try:
            from .core.memory_service import memory_service
            from .core.conversation_service import conversation_service

            # Get database conversation for semantic memory
            db_conversation = conversation_service.get_or_create_conversation(request.character_id, db)

            # Save current message to database for semantic search
            conversation_service.add_message(
                conversation_id=db_conversation.id,
                content=request.message,
                role="user",
                db=db
            )

            # Use semantic memory to get intelligent context (recent + relevant)
            context_messages = memory_service.get_context(
                conversation_id=db_conversation.id,
                current_message=request.message,
                context_window=15,  # Start with 15 recent messages
                db=db
            )

            # Add context messages to conversation
            for msg in context_messages:
                messages.append({"role": msg["role"], "content": msg["content"]})

            logger.info(f"Using semantic memory: {len(context_messages)} messages retrieved for {character['name']}")

        except Exception as e:
            logger.warning(f"Semantic memory failed, falling back to simple history: {e}")

            # Fallback to simple conversation history
            history = conversation_manager.get_conversation_history(session_id, limit=15)
            for msg in history:
                messages.append({"role": msg.role, "content": msg.content})

        # Add current user message (use enhanced prompt if RAG context available)
        if enhanced_prompt:
            # Use the properly formatted RAG prompt that includes both context and user message
            messages.append({"role": "user", "content": enhanced_prompt})
        else:
            # Use regular user message
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
            system_prompt=None,  # System prompt already included in messages
            model_config=model_config
        )
        
        # Save messages to conversation history (file-based system)
        conversation_manager.save_message(session_id, "user", request.message)
        conversation_manager.save_message(session_id, "assistant", response)

        # Also save to database for semantic memory (if available)
        try:
            from .core.conversation_service import conversation_service
            db_conversation = conversation_service.get_or_create_conversation(request.character_id, db)

            # Save assistant response to database for future semantic search
            conversation_service.add_message(
                conversation_id=db_conversation.id,
                content=response,
                role="assistant",
                db=db
            )

            logger.info(f"Saved assistant response to semantic memory for {character['name']}")

        except Exception as e:
            logger.warning(f"Failed to save to semantic memory: {e}")
        
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
            migration_available=migration_available,
            document_context_used=document_context_used,
            sources=sources,
            context_summary=context_summary if document_context_used else None,
            context_summary_full=rag_context.get('context_summary', '') if document_context_used else None
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return {"error": str(e)}, 500

@app.post("/api/chat/with-document")
async def chat_with_document(
    message: str = Form(...),
    character_id: str = Form(...),
    session_id: Optional[str] = Form(None),
    use_documents: bool = Form(True),
    file: Optional[UploadFile] = File(None),
    request_obj: Request = None,
    db = Depends(get_db)
):
    """Send a message with optional document upload to a character and get a response."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request_obj, db)
        if not current_user:
            return {"error": "Authentication required"}, 401

        # Process uploaded document if present
        uploaded_document = None
        document_analysis = None

        if file and file.filename:
            logger.info(f"Processing uploaded document: {file.filename}")

            # Upload and process the document
            from .core.document_service import document_service
            upload_result = await document_service.upload_document(
                file=file,
                user_id=current_user.id,
                db=db
            )

            if upload_result['success']:
                uploaded_document = upload_result['document']
                document_analysis = upload_result['processing_result']
                logger.info(f"Document processed successfully: {uploaded_document['id']}")

                # Auto-assign document to the current character via metadata
                try:
                    from ..database.models import Document

                    # Update document metadata to include character association
                    document = db.query(Document).filter(Document.id == uploaded_document['id']).first()
                    if document:
                        if not document.doc_metadata:
                            document.doc_metadata = {}

                        # Add character association to metadata
                        if 'character_associations' not in document.doc_metadata:
                            document.doc_metadata['character_associations'] = []

                        if character_id not in document.doc_metadata['character_associations']:
                            document.doc_metadata['character_associations'].append(character_id)
                            document.doc_metadata['auto_assigned'] = True
                            db.commit()
                            logger.info(f"Auto-assigned document {uploaded_document['id']} to character {character_id}")
                        else:
                            logger.info(f"Document {uploaded_document['id']} already assigned to character {character_id}")

                except Exception as e:
                    logger.warning(f"Failed to auto-assign document to character: {e}")
                    # Don't fail the entire request if assignment fails
            else:
                logger.error(f"Document upload failed: {upload_result.get('error')}")
                return {"error": f"Document upload failed: {upload_result.get('error')}"}, 400

        # Create ChatRequest object for reuse of existing logic
        chat_request = ChatRequest(
            message=message,
            character_id=character_id,
            session_id=session_id,
            use_documents=use_documents
        )

        # Get character
        character = character_manager.get_character(chat_request.character_id)
        if not character:
            return {"error": "Character not found"}, 404

        # Handle session management (same as original chat endpoint)
        session_id = chat_request.session_id
        migration_available = False

        if session_id:
            session = conversation_manager.get_session(session_id)
            if not session or session.character_id != chat_request.character_id:
                session_id = None

        if not session_id:
            session = conversation_manager.create_conversation_session(
                chat_request.character_id,
                str(current_user.id)
            )
            session_id = session.session_id

        # Check for character updates
        update_event = conversation_manager.check_version_compatibility(session_id)
        if update_event:
            migration_available = True

        # Initialize context variables
        rag_context = None
        enhanced_prompt = None
        document_context_used = False
        sources = []
        context_summary = None

        # Enhanced message with document analysis
        enhanced_message = chat_request.message
        if uploaded_document and document_analysis:
            # Add document context to the message
            doc_context = f"\n\n[Document uploaded: {uploaded_document['original_filename']}]\n"
            if document_analysis.get('summary'):
                doc_context += f"Document summary: {document_analysis['summary']}\n"
            if document_analysis.get('key_points'):
                doc_context += f"Key points: {', '.join(document_analysis['key_points'])}\n"

            enhanced_message += doc_context
            document_context_used = True
            sources = [uploaded_document['original_filename']]

        # Get enhanced context if document RAG is enabled
        if chat_request.use_documents:
            try:
                from .core.rag_service import rag_service
                rag_context = rag_service.get_enhanced_context(
                    user_message=enhanced_message,
                    user_id=current_user.id,
                    conversation_id=None,
                    character_id=chat_request.character_id,
                    include_conversation_history=True,
                    include_documents=True,
                    db=db
                )

                if rag_context and rag_context.get('document_chunks'):
                    document_context_used = True
                    doc_sources = [chunk.get('document_filename', 'Unknown')
                                  for chunk in rag_context['document_chunks']]
                    sources.extend(doc_sources)
                    sources = list(set(sources))  # Remove duplicates

                    context_summary = f"Found {len(rag_context['document_chunks'])} relevant document sections"

            except Exception as e:
                logger.warning(f"RAG context failed, continuing without: {e}")

        # Build messages for the conversation
        messages = []

        # Add system prompt (with fallback for null values)
        system_prompt = character.get('system_prompt') or character.get('persona', 'You are a helpful AI assistant.')
        messages.append({"role": "system", "content": system_prompt})

        # Try to use semantic memory service for intelligent context retrieval
        try:
            from .core.memory_service import memory_service
            from .core.conversation_service import conversation_service

            # Get database conversation for semantic memory
            db_conversation = conversation_service.get_or_create_conversation(chat_request.character_id, db)

            # Save current message to database for semantic search
            conversation_service.add_message(
                conversation_id=db_conversation.id,
                content=enhanced_message,
                role="user",
                db=db
            )

            # Use semantic memory to get intelligent context (recent + relevant)
            context_messages = memory_service.get_context(
                conversation_id=db_conversation.id,
                current_message=enhanced_message,
                context_window=15,
                db=db
            )

            # Add context messages to conversation
            for msg in context_messages:
                messages.append({"role": msg["role"], "content": msg["content"]})

            logger.info(f"Using semantic memory: {len(context_messages)} messages retrieved for {character['name']}")

        except Exception as e:
            logger.warning(f"Semantic memory failed, falling back to simple history: {e}")
            # Fallback to simple conversation history
            history = conversation_manager.get_conversation_history(session_id, limit=15)
            for msg in history:
                messages.append({"role": msg.role, "content": msg.content})

        # Add current message with RAG context if available
        final_message = enhanced_message
        if rag_context and rag_context.get('document_chunks'):
            # Prepend document context to the message
            document_context = "\n\n--- Document Context ---\n"
            for i, chunk in enumerate(rag_context['document_chunks'], 1):
                document_context += f"Document {i}: {chunk.get('document_filename', 'Unknown')}\n"
                document_context += f"Content: {chunk.get('text_content', '')[:1000]}...\n\n"
            document_context += "--- End Context ---\n\n"
            final_message = document_context + enhanced_message

        messages.append({"role": "user", "content": final_message})

        # Generate response using the character's model configuration
        model_config = character['model_config']
        provider = model_config.get('provider', 'ollama')

        # Log privacy information
        if provider == 'ollama':
            logger.info(f"Using LOCAL Ollama for {character['name']} - FULLY PRIVATE")
        else:
            logger.info(f"Using CLOUD provider {provider} for {character['name']} - data may be processed externally")

        # Generate response
        system_prompt_for_llm = character.get('system_prompt') or character.get('persona', 'You are a helpful AI assistant.')
        response = llm_client.generate_response_with_config(
            messages=messages,
            system_prompt=system_prompt_for_llm,
            model_config=model_config
        )

        # Save messages to conversation manager
        conversation_manager.save_message(session_id, "user", chat_request.message)
        conversation_manager.save_message(session_id, "assistant", response)

        # Also save to database for semantic memory (if available)
        try:
            from .core.conversation_service import conversation_service
            db_conversation = conversation_service.get_or_create_conversation(chat_request.character_id, db)

            # Save assistant response to database for future semantic search
            conversation_service.add_message(
                conversation_id=db_conversation.id,
                content=response,
                role="assistant",
                db=db
            )

            logger.info(f"Saved assistant response to semantic memory for {character['name']}")

        except Exception as e:
            logger.warning(f"Failed to save to semantic memory: {e}")

        # Update character usage
        character_manager.update_character(chat_request.character_id, {
            'last_used': datetime.now().isoformat(),
            'conversation_count': character.get('conversation_count', 0) + 1,
            'total_messages': character.get('total_messages', 0) + 1
        })

        logger.info(f"Generated response for {character['name']}: {response[:100]}...")

        # Build response with document information
        response_data = {
            "response": response,
            "character_name": character['name'],
            "character_id": character['id'],
            "session_id": session_id,
            "character_version": session.character_version,
            "migration_available": migration_available,
            "document_context_used": document_context_used,
            "sources": sources,
            "context_summary": context_summary if document_context_used else None
        }

        # Add document upload information if present
        if uploaded_document:
            response_data["uploaded_document"] = {
                "id": uploaded_document['id'],
                "filename": uploaded_document['original_filename'],
                "analysis": document_analysis
            }

        return response_data

    except Exception as e:
        logger.error(f"Error in chat with document: {e}")
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
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from .core.templates import render_template
from .core.static import mount_static_files
from .core.personality_manager import PersonalityManager
from .core.llm_client import llm_client
from pydantic import BaseModel
from typing import Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="MiaChat API",
    description="API for MiaChat - AI Personality Chat Application",
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
    secret_key="your-secret-key-here",  # Change this in production
    session_cookie="miachat_session"
)

# Mount static files
mount_static_files(app)

# Initialize personality manager
personality_manager = PersonalityManager()

# Pydantic models for API
class ChatMessage(BaseModel):
    message: str
    personality_name: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    personality_name: str
    success: bool = True

@app.get("/")
async def index(request: Request):
    """Render the index page."""
    return await render_template(request, "index")

@app.get("/chat")
async def chat(request: Request):
    """Render the chat page with personality selector."""
    # Get all personalities
    personalities = [
        personality_manager.get_personality(name)
        for name in personality_manager.list_personalities()
    ]
    
    # Get active personality
    active_personality = personality_manager.get_active_personality()
    active_name = active_personality.name if active_personality else None
    
    # Get categories and tags
    categories = personality_manager.get_categories()
    tags = personality_manager.get_tags()
    
    return await render_template(
        request, 
        "chat/index", 
        personalities=personalities,
        active_personality=active_name,
        categories=categories,
        tags=tags,
        chat_history=[],
        messages=[]
    )

@app.get("/personality")
async def personality_list(request: Request):
    """Render the personality list page."""
    personalities = [
        personality_manager.get_personality(name)
        for name in personality_manager.list_personalities()
    ]
    return await render_template(request, "personality/list", personalities=personalities)

@app.get("/settings")
async def settings(request: Request):
    """Render the settings page."""
    return await render_template(request, "settings")

@app.get("/config")
async def config(request: Request):
    """Render the config page."""
    return await render_template(request, "config")

@app.post("/api/chat", response_model=ChatResponse)
async def chat_api(chat_message: ChatMessage):
    """Chat API endpoint using Ollama with llama3:8b."""
    # Get personality
    personality_name = chat_message.personality_name or "Mia"
    personality = personality_manager.get_personality(personality_name)
    
    if not personality:
        return ChatResponse(
            response="I'm sorry, I couldn't find that personality. Let me respond as Mia instead.",
            personality_name="Mia",
            success=False
        )
    
    try:
        # Test Ollama connection first
        if not llm_client.test_connection():
            logger.error("Ollama is not accessible")
            return ChatResponse(
                response="I'm sorry, but I'm having trouble connecting to my language model. Please make sure Ollama is running.",
                personality_name=personality_name,
                success=False
            )
        
        # Generate response using Ollama with personality context
        response = llm_client.generate_personality_response(
            personality=personality,
            user_message=chat_message.message
        )
        
        logger.info(f"Generated response for {personality_name}: {response[:100]}...")
        
        return ChatResponse(
            response=response,
            personality_name=personality_name
        )
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return ChatResponse(
            response=f"I'm sorry, but I encountered an error while processing your message. Please try again. Error: {str(e)}",
            personality_name=personality_name,
            success=False
        )

@app.get("/api/personalities")
async def get_personalities():
    """Get all available personalities."""
    personalities = [
        personality_manager.get_personality(name)
        for name in personality_manager.list_personalities()
    ]
    return {"personalities": personalities}

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    ollama_status = "connected" if llm_client.test_connection() else "disconnected"
    return {
        "status": "ok",
        "ollama": ollama_status,
        "personalities": len(personality_manager.list_personalities())
    } 
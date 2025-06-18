from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from .core.templates import render_template
from .core.static import mount_static_files
from .core.personality_manager import PersonalityManager

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
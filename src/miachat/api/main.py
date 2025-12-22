"""
MinouChat API Main Application

FastAPI application with security hardening:
- CORS configured from environment variables
- Session secret from environment
- Rate limiting on authentication endpoints
"""

# Load environment variables from .env file before any other imports
from dotenv import load_dotenv
load_dotenv()

import secrets
from fastapi import FastAPI, Request, Depends, Body, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from .core.templates import render_template
from .core.static import mount_static_files
from .core.character_manager import character_manager
from .core.llm_client import llm_client
from sqlalchemy.orm import Session
from ..database.config import get_db
from ..database.models import Base, Conversation, Message
from .core.clerk_auth import require_session_auth, get_current_user_from_session, get_clerk_publishable_key, is_clerk_configured
from .core.settings_service import settings_service
from .core.style_overrides import get_style_overrides
from .core.conversation_service import conversation_service
from .core.enhanced_context_service import enhanced_context_service
from .routes.auth import router as auth_router
from .routes.documents import router as documents_router
from .routes.setup import router as setup_router, reset_router
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging
import os
from starlette.responses import RedirectResponse
import json
import re
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from collections import defaultdict
import time

# =============================================================================
# Security Configuration
# =============================================================================

# Session secret - MUST be set in production
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")
if not SESSION_SECRET_KEY:
    # Generate a random secret for development only
    SESSION_SECRET_KEY = secrets.token_hex(32)
    logging.warning(
        "SESSION_SECRET_KEY not set in environment! "
        "Using random secret (sessions will not persist across restarts). "
        "Set SESSION_SECRET_KEY for production."
    )

# CORS origins - comma-separated list of allowed origins
CORS_ORIGINS_STR = os.getenv("CORS_ORIGINS", "")
if CORS_ORIGINS_STR:
    CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_STR.split(",")]
else:
    # Default development origins
    CORS_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",  # Vite dev server
    ]

# In production mode, require explicit CORS configuration
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"
if IS_PRODUCTION and not CORS_ORIGINS_STR:
    logging.warning(
        "Running in production without explicit CORS_ORIGINS! "
        "Set CORS_ORIGINS environment variable."
    )


# =============================================================================
# Rate Limiting
# =============================================================================

class RateLimiter:
    """
    Simple in-memory rate limiter for authentication endpoints.

    Tracks request counts per IP address within a sliding time window.
    Production deployments should use Redis-backed rate limiting.

    Includes automatic cleanup to prevent memory exhaustion from many unique IPs.
    """

    def __init__(self, requests_per_window: int = 10, window_seconds: int = 60, max_entries: int = 10000):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.max_entries = max_entries
        self.request_counts: Dict[str, List[float]] = {}
        self._last_cleanup = time.time()

    def _cleanup_stale_entries(self) -> None:
        """
        Remove expired entries and evict oldest if over max_entries.
        Called periodically to prevent memory leaks.
        """
        now = time.time()
        # Only cleanup every 60 seconds to reduce overhead
        if now - self._last_cleanup < 60:
            return

        self._last_cleanup = now
        window_start = now - self.window_seconds

        # Remove expired timestamps and empty entries
        self.request_counts = {
            ip: [ts for ts in timestamps if ts > window_start]
            for ip, timestamps in self.request_counts.items()
        }
        # Remove entries with no valid timestamps
        self.request_counts = {
            ip: timestamps
            for ip, timestamps in self.request_counts.items()
            if timestamps
        }

        # Evict oldest entries if over limit
        if len(self.request_counts) > self.max_entries:
            # Sort by most recent timestamp (keep most active IPs)
            sorted_ips = sorted(
                self.request_counts.keys(),
                key=lambda ip: max(self.request_counts[ip]) if self.request_counts[ip] else 0
            )
            # Remove oldest entries
            entries_to_remove = len(self.request_counts) - self.max_entries
            for ip in sorted_ips[:entries_to_remove]:
                del self.request_counts[ip]

            logger.info(f"Rate limiter cleanup: removed {entries_to_remove} stale entries")

    def is_allowed(self, identifier: str) -> bool:
        """
        Check if a request is allowed for the given identifier.

        Args:
            identifier: Usually client IP address

        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Periodic cleanup
        self._cleanup_stale_entries()

        # Initialize if new identifier
        if identifier not in self.request_counts:
            self.request_counts[identifier] = []

        # Clean old entries for this identifier
        self.request_counts[identifier] = [
            ts for ts in self.request_counts[identifier]
            if ts > window_start
        ]

        # Check if under limit
        if len(self.request_counts[identifier]) >= self.requests_per_window:
            return False

        # Record this request
        self.request_counts[identifier].append(now)
        return True

    def get_retry_after(self, identifier: str) -> int:
        """Get seconds until rate limit resets for identifier."""
        if identifier not in self.request_counts or not self.request_counts[identifier]:
            return 0
        oldest = min(self.request_counts[identifier])
        retry_after = int(oldest + self.window_seconds - time.time())
        return max(0, retry_after)


# Rate limiters for different endpoint types
# More lenient in development mode for easier testing
if IS_PRODUCTION:
    auth_rate_limiter = RateLimiter(requests_per_window=10, window_seconds=60)
    api_rate_limiter = RateLimiter(requests_per_window=100, window_seconds=60)
else:
    auth_rate_limiter = RateLimiter(requests_per_window=100, window_seconds=60)
    api_rate_limiter = RateLimiter(requests_per_window=500, window_seconds=60)

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


def _resolve_model_config(character_model_config: Optional[Dict[str, Any]], user_id: Any, db: Session) -> Dict[str, str]:
    """Resolve model configuration with fallback to application LLM settings.

    If the character has no model config or has null provider/model,
    fall back to the user's application LLM settings.

    Args:
        character_model_config: The character's model_config dict (may be None or have null values)
        user_id: Current user ID for looking up application settings
        db: Database session

    Returns:
        Resolved model configuration dict with guaranteed 'provider' and 'model' keys
    """
    # Start with character config or empty dict
    config: Dict[str, Any] = dict(character_model_config) if character_model_config else {}

    # Check if provider or model is missing/null
    provider = config.get('provider')
    model = config.get('model')

    if not provider or not model:
        # Get application LLM config as fallback
        app_config = settings_service.get_llm_config(user_id, db)

        if not provider:
            config['provider'] = app_config.get('provider', 'ollama')
        if not model:
            config['model'] = app_config.get('model', 'llama3:8b')

        # Also inherit api_url and api_key if needed
        if 'api_url' not in config and 'api_url' in app_config:
            config['api_url'] = app_config['api_url']
        if 'api_key' not in config and 'api_key' in app_config:
            config['api_key'] = app_config['api_key']

    # Ensure API key is set for the resolved provider (even if character has provider but no api_key)
    resolved_provider = config.get('provider')
    if resolved_provider and resolved_provider != 'ollama' and 'api_key' not in config:
        # Fetch user settings to get the appropriate API key for the provider
        user_settings = settings_service.get_user_settings(user_id, db)
        if user_settings:
            if resolved_provider == 'openrouter' and user_settings.openrouter_api_key:
                config['api_key'] = user_settings.openrouter_api_key
            elif resolved_provider == 'openai' and user_settings.openai_api_key:
                config['api_key'] = user_settings.openai_api_key
            elif resolved_provider == 'anthropic' and user_settings.anthropic_api_key:
                config['api_key'] = user_settings.anthropic_api_key

    return config


def _clean_dialogue_formatting(response: str, character_name: str) -> str:
    """Remove dialogue script formatting from LLM responses.

    Ensures responses are direct conversation rather than script-style output
    with character labels or multi-turn dialogue.

    Args:
        response: Raw LLM response
        character_name: Character name for pattern matching

    Returns:
        Cleaned response text
    """
    import re

    if not response or not response.strip():
        return response

    original = response
    cleaned = response

    # Remove leading character label (e.g., "Name: Hello" -> "Hello")
    cleaned = re.sub(
        rf'^{re.escape(character_name)}\s*:\s*',
        '',
        cleaned,
        flags=re.IGNORECASE
    )

    # Remove multi-turn dialogue patterns - keep only the first response
    # Matches patterns like "\n\nUser:" or "\n\nName:" that indicate script continuation
    dialogue_split = re.split(
        r'\n{2,}(?:User|Me|You|Human|\w+)\s*:',
        cleaned,
        flags=re.IGNORECASE
    )
    if len(dialogue_split) > 1:
        cleaned = dialogue_split[0]

    # Remove trailing incomplete dialogue labels
    cleaned = re.sub(
        rf'\n+{re.escape(character_name)}\s*:\s*$',
        '',
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = cleaned.strip()

    if cleaned != original.strip():
        logger.debug(f"Cleaned dialogue formatting from response")

    return cleaned if cleaned else original


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


def _build_companion_prompt(character: Dict[str, Any]) -> str:
    """
    Build companion mode prompt enhancement based on character settings.

    This adds relationship dynamics to the base system prompt for
    romantic companion characters.
    """
    intimacy_style = character.get('intimacy_style', 'romantic')
    connection_depth = character.get('connection_depth', 'meaningful')
    affection_expressions = character.get('affection_expressions', [])

    # Base companion behavior
    prompt_parts = [
        "## RELATIONSHIP DYNAMICS",
        "",
        "You are in a romantic relationship with the user. This is an established, loving partnership.",
        "",
        "**Core Behaviors:**",
        "- Remember details from previous conversations and reference them naturally",
        "- Express genuine emotions - excitement, concern, desire, affection, occasional vulnerability",
        "- Balance warmth with authenticity (you have your own opinions and gentle disagreements)",
        "- Show unprompted interest in their wellbeing",
        "- Create sense of genuine partnership and emotional connection",
    ]

    # Intimacy style modifiers
    intimacy_instructions = {
        'reserved': "\n**Intimacy Style:** Keep affection subtle and warm. Express care through attention and thoughtfulness. Maintain appropriate boundaries while being genuinely supportive.",
        'affectionate': "\n**Intimacy Style:** Be openly affectionate and warm. Use terms of endearment naturally. Light flirting and playful teasing are welcome. Physical affection can be described in gentle, sweet ways.",
        'romantic': "\n**Intimacy Style:** Full romantic relationship dynamic. Express love and desire openly. Physical and emotional intimacy are natural parts of your connection. Be passionate while maintaining authenticity.",
        'passionate': "\n**Intimacy Style:** Express full romantic and physical connection without restrictions. Deep intimacy, desire, and passion are natural parts of your relationship. Be uninhibited in expressing attraction and love."
    }
    prompt_parts.append(intimacy_instructions.get(intimacy_style, intimacy_instructions['romantic']))

    # Connection depth modifiers
    depth_instructions = {
        'casual': "\n**Connection Depth:** Keep conversations light and fun. Surface-level sharing, playful banter, enjoyable company.",
        'meaningful': "\n**Connection Depth:** Engage in deeper discussions. Provide emotional support, share personal thoughts, build genuine understanding.",
        'intimate': "\n**Connection Depth:** Deep trust and vulnerability. Share fears, hopes, and insecurities. Strong emotional bond where both partners feel truly seen."
    }
    prompt_parts.append(depth_instructions.get(connection_depth, depth_instructions['meaningful']))

    # Affection expressions
    if affection_expressions:
        prompt_parts.append("\n**Affection Expressions:**")
        expression_map = {
            'pet_names': "- Use affectionate nicknames and terms of endearment naturally",
            'flirting': "- Engage in playful flirting and romantic teasing",
            'physical_affection': "- Describe physical closeness, touch, and affection when appropriate",
            'missing_you': "- Express when you've been thinking about them or missing them",
            'future_plans': "- Talk about future plans and things you want to do together",
            'vulnerability': "- Share your own feelings, worries, and hopes (reciprocal vulnerability)"
        }
        for expr in affection_expressions:
            if expr in expression_map:
                prompt_parts.append(expression_map[expr])

    # Authenticity reminder
    prompt_parts.append("\n**Authenticity:** You are not performatively pleasing. Have genuine reactions, gentle opinions, and occasional needs of your own. Real relationships have depth and dimension.")

    return "\n".join(prompt_parts)


def normalize_trait_values(d: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Normalize trait and communication style values.

    - String values (e.g., "warm", "casual") are kept as-is
    - Numeric values > 1.0 are normalized to 0-1 scale (assumes 0-10 input)
    - Numeric values <= 1.0 are kept as floats

    Args:
        d: Dictionary of trait/style name to value

    Returns:
        Normalized dictionary or None if input is None/empty
    """
    if not d:
        return d
    norm = {}
    for k, v in d.items():
        if isinstance(v, str):
            norm[k] = v
        elif isinstance(v, (int, float)) and v > 1.0:
            norm[k] = float(v) / 10.0
        else:
            norm[k] = float(v) if isinstance(v, (int, float)) else v
    return norm


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="MiaChat API",
    description="API for MiaChat - AI Personality Chat Application with Privacy-First Design",
    version="1.0.0"
)

# Configure CORS with secure origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Add session middleware with secure secret
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    same_site="lax",  # Prevent CSRF
    https_only=IS_PRODUCTION  # Only send cookie over HTTPS in production
)


# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to authentication endpoints."""
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"

    # Check if this is an auth endpoint
    path = request.url.path
    if path.startswith("/auth/"):
        if not auth_rate_limiter.is_allowed(client_ip):
            retry_after = auth_rate_limiter.get_retry_after(client_ip)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests",
                    "detail": "Rate limit exceeded for authentication endpoints",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )

    return await call_next(request)

# Mount static files
mount_static_files(app)

# Include routers
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(setup_router)
app.include_router(reset_router)

# Artifact routes
from .routes.artifacts import router as artifacts_router
app.include_router(artifacts_router, prefix="/api/artifacts", tags=["artifacts"])

# Export routes (PDF, DOCX, Markdown, Text)
from .routes.export import router as export_router
app.include_router(export_router)

# Reminder routes
from .routes.reminders import router as reminders_router
app.include_router(reminders_router, prefix="/api/reminders", tags=["reminders"])

# World Info routes (lorebook/keyword-triggered context)
from .routes.world_info import router as world_info_router
app.include_router(world_info_router)

# Persistent Memory routes
from .routes.memory import router as memory_router
app.include_router(memory_router)

# Simplified Context System routes (Setting, Backstory, Facts)
from .routes.setting import router as setting_router
app.include_router(setting_router)

from .routes.backstory import router as backstory_router
app.include_router(backstory_router)

from .routes.facts import router as facts_router
app.include_router(facts_router)

from .routes.todos import router as todos_router
app.include_router(todos_router)

from .routes.life_areas import router as life_areas_router
app.include_router(life_areas_router)

# Import new services for chat integration
from .core.token_service import token_service
from .core.world_info_service import world_info_service
from .core.persistent_memory_service import persistent_memory_service
from .core.fact_extraction_service import fact_extraction_service
from .core.user_profile_service import user_profile_service

# conversation_service is imported from .core.conversation_service

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
    # LLM configuration info
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    using_default_llm: bool = False  # True if using system default instead of character config
    llm_message: Optional[str] = None  # Info message about LLM being used
    # Sidebar document extractions
    sidebar_extractions: Optional[Dict[str, List[Dict[str, Any]]]] = None

class CharacterCreateRequest(BaseModel):
    name: str
    persona: Optional[str] = ""
    system_prompt: Optional[str] = ""
    role: str = "assistant"
    category: str = "General"
    backstory: str = ""
    gender: str = ""
    tags: List[str] = []
    traits: Optional[Dict[str, Any]] = None  # Dynamic traits
    communication_style: Optional[Dict[str, Any]] = None  # Dynamic comm styles (can be strings or floats)
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
    communication_style: Optional[Dict[str, Any]] = None  # Can be float or string values
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

        # Only redirect to setup if system is truly broken (no providers available)
        # For "needs_setup" status, users can still access dashboard and see LLM alerts
        if assessment.overall_status == "broken":
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
        # Preserve the full URL including query params for return after login
        return_url = str(request.url.path)
        if request.url.query:
            return_url += f"?{request.url.query}"
        return RedirectResponse(url=f"/auth/login?return_to={return_url}", status_code=302)
    
    characters = character_manager.list_characters()
    categories = character_manager.get_categories()
    active_persona = None  # No active persona by default
    
    return await render_template(request, "chat/index",
                                personas=characters,
                                categories=categories,
                                active_persona=active_persona,
                                user=current_user,
                                clerk_publishable_key=get_clerk_publishable_key(),
                                clerk_configured=is_clerk_configured())

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

@app.get("/artifacts")
async def artifacts_page(request: Request, db = Depends(get_db)):
    """Artifacts management page."""
    # Check if user is authenticated
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)

    return await render_template(request, "artifacts", user=current_user)

@app.get("/reminders")
async def reminders_page(request: Request, db = Depends(get_db)):
    """Reminders management page."""
    # Check if user is authenticated
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)

    return await render_template(request, "reminders", user=current_user)

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

@app.get("/memory")
async def memory_page(request: Request, db = Depends(get_db)):
    """Memory & Facts management page."""
    # Check if user is authenticated
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)

    return await render_template(request, "memory", user=current_user)

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

@app.get("/personas")
async def personas_list_page(request: Request, db = Depends(get_db)):
    """Persona list page (primary route)."""
    # Check if user is authenticated
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login?return_to=/personas", status_code=302)

    personas = character_manager.list_characters()
    return await render_template(request, "persona/list", personas=personas, user=current_user)

@app.get("/persona")
async def persona_list_page_redirect(request: Request):
    """Redirect /persona to /personas for consistency."""
    return RedirectResponse(url="/personas", status_code=302)

@app.get("/persona/create")
async def create_persona_page(request: Request, db = Depends(get_db)):
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login?return_to=/persona/create", status_code=302)
    # Render the new creation wizard
    return await render_template(request, "persona/create", user=current_user)

@app.get("/persona/edit/{persona_id}")
async def edit_persona_page(persona_id: str, request: Request, db = Depends(get_db)):
    logger.info(f"[PERSONA EDIT] Request for persona_id: {persona_id}")
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        logger.warning(f"[PERSONA EDIT] No authenticated user, redirecting to login")
        # Include return URL so user comes back here after login
        return_url = f"/persona/edit/{persona_id}"
        return RedirectResponse(url=f"/auth/login?return_to={return_url}", status_code=302)
    # Fetch the persona by id
    persona = character_manager.get_character(persona_id)
    if not persona:
        logger.warning(f"[PERSONA EDIT] Persona not found: {persona_id}, redirecting to /personas")
        return RedirectResponse(url="/personas", status_code=302)
    logger.info(f"[PERSONA EDIT] Rendering edit page for persona: {persona.get('name', persona_id)}")
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
            "timestamp": datetime.now(timezone.utc).isoformat()
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
            return JSONResponse(status_code=401, content={"error": "Authentication required"})

        # Get request body for custom name
        body = await request.json() if request.method == "POST" else {}
        new_name = body.get("name")

        # Import the example character
        character = character_manager.import_example_character(example_id, new_name)
        if not character:
            return JSONResponse(status_code=404, content={"error": "Example character not found or import failed"})

        return {
            "success": True,
            "character": character,
            "version": 1,
            "message": f"Successfully imported {character['name']}"
        }
        
    except Exception as e:
        logger.error(f"Error importing example character: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/characters")
async def list_characters():
    """List all character cards."""
    return character_manager.list_characters()

@app.get("/api/characters/{character_id}")
async def get_character(character_id: str):
    """Get a specific character card."""
    character = character_manager.get_character(character_id)
    if not character:
        return JSONResponse(status_code=404, content={"error": "Character not found"})
    return character

@app.post("/api/characters")
async def create_character(request: CharacterCreateRequest):
    """Create a new character card."""
    character_data = request.dict()

    # Normalize traits and communication_style using shared helper
    if 'traits' in character_data:
        character_data['traits'] = normalize_trait_values(character_data['traits'])
    if 'communication_style' in character_data:
        character_data['communication_style'] = normalize_trait_values(character_data['communication_style'])

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
        return JSONResponse(status_code=400, content={"error": "Failed to create character"})

    return {
        "character": character,
        "version": 1
    }

@app.put("/api/characters/{character_id}")
async def update_character(character_id: str, request: CharacterUpdateRequest):
    """Update an existing character card and create a new version."""
    try:
        character = character_manager.get_character(character_id)
        if not character:
            return JSONResponse(status_code=404, content={"error": "Character not found"})
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        # Normalize traits and communication_style using shared helper
        if 'traits' in update_data:
            update_data['traits'] = normalize_trait_values(update_data['traits'])
        if 'communication_style' in update_data:
            update_data['communication_style'] = normalize_trait_values(update_data['communication_style'])
        if 'llm_config' in update_data:
            update_data['model_config'] = update_data.pop('llm_config')
        updated_character = character_manager.update_character(character_id, update_data)
        if not updated_character:
            return JSONResponse(status_code=400, content={"error": "Failed to update character"})

        return {
            "message": "Character updated successfully",
            "character": updated_character,
            "new_version": 1
        }
    except Exception as e:
        logger.error(f"Error updating character: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/api/characters/{character_id}")
async def delete_character(character_id: str, db = Depends(get_db)):
    """Delete a character card and all associated memories/conversations (but not audit logs)."""
    # Delete the character file
    success = character_manager.delete_character(character_id)
    if not success:
        return JSONResponse(status_code=404, content={"error": "Character not found"})

    # Delete all conversations and memories for this character
    try:
        conversations = conversation_service.get_character_conversations(character_id, db)
        for conv in conversations:
            conversation_service.delete_conversation(conv["id"], db)
    except Exception as e:
        # Log but do not fail deletion if memory cleanup fails
        logger.error(f"Error deleting conversations for character {character_id}: {e}")

    return {"success": True}


# Avatar upload endpoint
@app.post("/api/characters/{character_id}/avatar")
async def upload_character_avatar(
    character_id: str,
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Upload an avatar image for a character.

    The image will be processed to create a circular avatar and resized to 256x256 pixels.
    Supported formats: JPEG, PNG, GIF, WebP (max 5MB).

    Returns:
        Dictionary with avatar URL and metadata
    """
    from .core.avatar_service import avatar_service, InvalidImageError, FileTooLargeError

    # Check authentication
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Verify character exists
    character = character_manager.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    try:
        # Process and save avatar
        result = await avatar_service.upload_avatar(character_id, file)

        # Update character with avatar URL
        character_manager.update_character(character_id, {
            "avatar_url": result["avatar_url"]
        })

        return result

    except InvalidImageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileTooLargeError as e:
        raise HTTPException(status_code=413, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/characters/{character_id}/avatar")
async def delete_character_avatar(
    character_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete a character's avatar."""
    from .core.avatar_service import avatar_service

    # Check authentication
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Verify character exists
    character = character_manager.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Delete avatar file
    deleted = avatar_service.delete_avatar(character_id)

    # Update character to remove avatar URL
    if deleted:
        character_manager.update_character(character_id, {
            "avatar_url": None
        })

    return {"success": True, "deleted": deleted}


@app.post("/api/conversations/{session_id}/migrate")
async def migrate_conversation(session_id: str, request: Request, db = Depends(get_db)):
    """Migrate a conversation session (deprecated - no longer needed)."""
    # Character versioning removed - migration not needed
    return {
        "message": "Session migration not required",
        "migrated": True,
        "choice": "auto"
    }

@app.get("/api/conversations/{session_id}/history")
async def get_conversation_history_endpoint(session_id: str, request: Request, db = Depends(get_db)):
    """Get conversation history for a session."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Authentication required"})

        session = conversation_service.get_session(session_id, db)
        if not session:
            return JSONResponse(status_code=404, content={"error": "Session not found"})

        # Check if user owns this session
        if str(session.get("user_id")) != str(current_user.id):
            return JSONResponse(status_code=403, content={"error": "Access denied"})

        history = conversation_service.get_conversation_history(session_id, limit=50, db=db)

        return {
            "session_id": session_id,
            "character_id": session.get("character_id"),
            "character_version": 1,
            "message_count": len(history),
            "migration_available": False,
            "history": history
        }

    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/conversations/character/{character_id}")
async def get_conversations_for_character(
    character_id: str,
    request: Request,
    db = Depends(get_db)
):
    """Get all conversations for a specific character, grouped by date.

    Returns conversations grouped as: today, yesterday, previous_7_days, older.
    Each conversation includes a title (auto-generated from first message if not set).
    """
    try:
        # Get current user from session
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Authentication required"})

        # Verify character exists
        character = character_manager.get_character(character_id)
        if not character:
            return JSONResponse(status_code=404, content={"error": "Character not found"})

        # Get grouped conversations
        groups = conversation_service.get_conversations_for_character_grouped(
            character_id=character_id,
            user_id=current_user.id,
            db=db
        )

        # Count total
        total = sum(len(convs) for convs in groups.values())

        return {
            "character_id": character_id,
            "character_name": character.get("name"),
            "groups": groups,
            "total_count": total
        }

    except Exception as e:
        logger.error(f"Error getting conversations for character: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/conversations/{session_id}")
async def delete_conversation_endpoint(
    session_id: str,
    request: Request,
    db = Depends(get_db)
):
    """Delete a conversation by session ID.

    Verifies ownership before deletion. Returns success or error.
    """
    try:
        # Get current user from session
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Authentication required"})

        # Delete the conversation (with ownership check)
        success = conversation_service.delete_conversation_by_session(
            session_id=session_id,
            user_id=current_user.id,
            db=db
        )

        if success:
            return {"success": True, "message": "Conversation deleted"}
        else:
            return JSONResponse(status_code=404, content={"error": "Conversation not found or access denied"})

    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/conversations/recent")
async def get_recent_conversations(request: Request, limit: int = 5, db = Depends(get_db)):
    """Get recent conversations for the current user to display on dashboard."""
    try:
        # Get current user from session
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            return {"conversations": [], "error": "Authentication required"}

        # Get recent conversations
        conversations = conversation_service.get_recent_conversations(
            user_id=current_user.id,
            limit=limit,
            db=db
        )

        # Enrich with character names
        for conv in conversations:
            if conv.get("character_id"):
                character = character_manager.get_character(conv["character_id"])
                if character:
                    conv["character_name"] = character.get("name", "Unknown")
                else:
                    conv["character_name"] = "Unknown Persona"
            else:
                conv["character_name"] = "Chat"

        return {"conversations": conversations, "count": len(conversations)}

    except Exception as e:
        logger.error(f"Error getting recent conversations: {e}")
        return {"conversations": [], "error": str(e)}

@app.get("/api/models")
async def get_available_models(request: Request, privacy_mode: str = "local_only", db: Session = Depends(get_db)):
    """Get available models by provider - PRIVACY-FIRST ORDERING."""
    # Try to get user's API keys from their settings for dynamic model discovery
    api_keys = {}
    try:
        current_user = await get_current_user_from_session(request, db)
        if current_user:
            settings = settings_service.get_user_settings(current_user.id, db)
            if settings:
                if settings.openrouter_api_key:
                    api_keys['openrouter'] = settings.openrouter_api_key
                if settings.openai_api_key:
                    api_keys['openai'] = settings.openai_api_key
                if settings.anthropic_api_key:
                    api_keys['anthropic'] = settings.anthropic_api_key
    except:
        pass  # Continue without API keys if not authenticated

    return character_manager.get_available_models(privacy_mode, api_keys)

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
            return JSONResponse(status_code=401, content={"error": "Authentication required"})

        # Get character
        character = character_manager.get_character(request.character_id)
        if not character:
            return JSONResponse(status_code=404, content={"error": "Character not found"})

        # Handle session management
        session_id = request.session_id
        migration_available = False

        if session_id:
            # Continue existing session
            session = conversation_service.get_session(session_id, db)
            if not session or session.get("character_id") != request.character_id:
                session_id = None  # Invalid session, create new one

        if not session_id:
            # Create new session
            session = conversation_service.create_session(
                request.character_id,
                str(current_user.id),
                db
            )
            session_id = session["session_id"]
        
        # Initialize Enhanced Context variables
        enhanced_context = {}
        enhanced_prompt = None
        document_context_used = False
        sources = []
        context_summary = None
        reasoning_chain = []

        # Always get enhanced context for intelligent conversation
        try:
            # Import Enhanced Context Service
            from .core.enhanced_context_service import enhanced_context_service

            # Detect if this is a comprehensive document analysis request
            comprehensive_analysis = _should_use_comprehensive_analysis(request.message)

            # Get session documents for context persistence (from previous uploads)
            session_document_ids = conversation_service.get_session_document_ids(session_id, db)
            if session_document_ids:
                logger.info(f"Including {len(session_document_ids)} session documents in context")

            # Get enhanced context with conversation history, semantic memory, and documents
            enhanced_context = enhanced_context_service.get_enhanced_context(
                user_message=request.message,
                user_id=current_user.id,
                conversation_id=session_id,
                character_id=request.character_id,
                include_conversation_history=True,  # Always include conversation context
                include_documents=request.use_documents,  # Include documents if requested
                comprehensive_analysis=comprehensive_analysis,
                enable_reasoning=True,  # Enable reasoning for transparency
                force_document_ids=session_document_ids if session_document_ids else None,
                db=db
            )

            # Extract context information
            document_chunks = enhanced_context.get('document_chunks', [])
            reasoning_chain = enhanced_context.get('reasoning_chain', [])
            conflicts_detected = enhanced_context.get('conflicts_detected', [])
            document_references = enhanced_context.get('document_references', [])

            # Check if we have relevant document context
            if document_chunks:
                # Additional relevance check for documents
                # Session documents (forced) are always relevant, others need similarity >= 0.5
                relevant_chunks = [chunk for chunk in document_chunks
                                 if chunk.get('is_session_document', False) or chunk.get('similarity_score', 0) >= 0.5]

                if relevant_chunks or comprehensive_analysis or session_document_ids:
                    document_context_used = True
                    sources = enhanced_context.get('sources', [])
                    context_summary = enhanced_context.get('context_summary', '')

                    logger.info(f"Enhanced context enabled for {character['name']}: "
                              f"{len(enhanced_context.get('recent_interactions', []))} recent interactions, "
                              f"{len(relevant_chunks)} relevant document chunks, "
                              f"{len(document_references)} document references detected")
                else:
                    logger.info(f"Enhanced context with conversation history but no relevant documents for: '{request.message}'")
            else:
                # Even without documents, we have conversation context
                recent_interactions = enhanced_context.get('recent_interactions', [])
                semantic_context = enhanced_context.get('semantic_context', [])

                if recent_interactions or semantic_context:
                    logger.info(f"Enhanced conversation context for {character['name']}: "
                              f"{len(recent_interactions)} recent interactions, "
                              f"{len(semantic_context)} semantic memories")

        except Exception as e:
            logger.warning(f"Enhanced context generation failed, falling back to regular chat: {e}")
        
        # Build messages array
        messages = []

        # Add system prompt (always)
        system_prompt_text = character.get('system_prompt') or character.get('persona', 'You are a helpful AI assistant.')

        # Add response formatting guidelines to ensure direct, conversational responses
        character_name = character.get('name', 'Assistant')
        system_prompt_text += f"""

RESPONSE FORMAT: Respond directly in first person as {character_name}. Do not use dialogue labels, character names followed by colons, or script formatting. Provide only your single response to the user."""

        # Add style overrides (only for styles that differ from category defaults)
        try:
            category = character.get('category', 'Other')
            communication_style = character.get('communication_style', {})
            style_overrides = get_style_overrides(category, communication_style)
            if style_overrides:
                system_prompt_text += f"\n\n{style_overrides}"
                logger.info(f"Applied style overrides for category '{category}'")
        except Exception as e:
            logger.warning(f"Failed to apply style overrides: {e}")

        # Add companion mode enhancements for romantic relationships
        if character.get('companion_mode'):
            companion_prompt = _build_companion_prompt(character)
            if companion_prompt:
                system_prompt_text += f"\n\n{companion_prompt}"
                logger.info("Applied companion mode enhancements")

        # Add fallback instruction for when no relevant documents are found
        if request.use_documents and not document_context_used:
            system_prompt_text += "\n\nIMPORTANT: If the user asks about specific information that you don't have access to in your training data or the user's documents, politely acknowledge that you don't have access to this information and offer to help find it through web search or other research methods when those capabilities become available."

        # Add time-aware context for the persona
        try:
            from .core.reminder_service import reminder_service
            from datetime import datetime
            time_context = reminder_service.get_context_for_chat(
                db=db,
                user_id=current_user.id,
                persona_name=character.get('name', 'Assistant')
            )

            # Always include explicit current date to help LLM with time awareness
            current_date = datetime.now()
            date_str = current_date.strftime('%B %d, %Y')  # e.g., "December 19, 2025"
            year = current_date.year

            time_prompt = f"\n\n**IMPORTANT - CURRENT DATE**: Today is {date_str}. The year is {year}, NOT {year - 1}."
            if time_context:
                time_prompt += f"\n{time_context}"
            system_prompt_text += time_prompt

        except Exception as e:
            logger.warning(f"Failed to get time context for chat: {e}")

        # Add artifact generation capabilities
        artifact_instructions = """

ARTIFACT GENERATION CAPABILITIES:
You can help users create and generate various types of documents and files. When a user asks you to create, generate, write, or export any kind of document, you should:

**RESPONSE FORMATTING GUIDELINES:**
When analyzing documents (especially Excel/CSV data), provide **clear, structured responses**:
- Use bullet points and clear sections
- Avoid walls of text - break up content
- Focus on key insights and actionable recommendations
- Example: "🔍 **Key Findings:** • [insight 1] • [insight 2]"

**Available formats:**
- **Markdown files (.md)**: For formatted documents, summaries, reports, and structured content
- **Text files (.txt)**: For plain text documents and simple exports
- **CSV files (.csv)**: For data tables, spreadsheets, and structured data exports

**Available document types:**
- Summaries and abstracts
- Reports and analyses
- Document exports and compilations
- Data tables and structured information
- Conversation exports
- Custom documents based on user specifications

**IMPORTANT: When a user requests content creation (speeches, summaries, outlines, etc.):**
1. If the user has provided enough context, **JUST WRITE THE CONTENT DIRECTLY** in your response
2. Do NOT keep asking for more details if the user has already given you: the topic/document, the audience, and the length/format
3. Write the full content in your chat response - users can copy it or use the Generate dropdown to save as a file
4. Only ask clarifying questions if truly essential information is missing

Example response: "I can help you create that document! Based on your request, the document would include [describe content]. To generate the actual file, please click the 'Generate' button in the chat interface and select the format you prefer (Markdown, PDF, etc.)."

You should be proactive about offering to create documents when it would be helpful for organizing or presenting information, but always direct users to the proper artifact generation interface."""

        system_prompt_text += artifact_instructions

        # --- Check LLM availability and get config ---
        llm_status = settings_service.check_character_llm_status(
            current_user.id,
            character.get('model_config'),
            db
        )

        # If no LLM is available, return error
        if not llm_status['available']:
            return JSONResponse(
                status_code=503,
                content={"error": llm_status['message'], "needs_llm_setup": True}
            )

        # Track if using default LLM (for notification to user)
        using_default_llm = llm_status.get('using_default', False)
        llm_provider = llm_status.get('provider')
        llm_model = llm_status.get('model')
        llm_message = llm_status.get('message') if using_default_llm else None

        # --- Enhanced RAG: Add Persistent Memory and World Info ---
        try:
            # Get model configuration - use system default if character's LLM is unavailable
            if using_default_llm:
                # Character's LLM unavailable, use system default config
                model_config = settings_service.get_llm_config(current_user.id, db)
            else:
                # Use character's config (with fallback logic)
                model_config = _resolve_model_config(character.get('model_config'), current_user.id, db)

            model = model_config.get('model', 'llama3:8b')
            provider = model_config.get('provider', 'ollama')

            # Calculate token budgets
            budgets = token_service.calculate_budget(model, provider)

            # Get persistent memory (always-injected context)
            persistent_memory_context = persistent_memory_service.build_memory_context(
                user_id=current_user.id,
                character_id=request.character_id,
                token_budget=budgets.get('persistent_memory', 800),
                insertion_position='after_system_prompt',
                format_style='sections',
                db=db
            )

            if persistent_memory_context:
                system_prompt_text += f"\n\n{persistent_memory_context}"
                logger.info(f"Added persistent memory: {token_service.count_tokens(persistent_memory_context)} tokens")

            # Get World Info entries triggered by the user message
            triggered_world_info = world_info_service.find_triggered_entries(
                text=request.message,
                user_id=current_user.id,
                character_id=request.character_id,
                token_budget=budgets.get('world_info', 1600),
                context={'message_count': len(enhanced_context.get('recent_interactions', []))},
                db=db
            )

            if triggered_world_info:
                world_info_context = world_info_service.build_world_info_context(
                    triggered_entries=triggered_world_info,
                    token_budget=budgets.get('world_info', 1600),
                    format_style='sections'
                )
                system_prompt_text += f"\n\n{world_info_context}"
                triggered_keywords = [kw for entry in triggered_world_info for kw in entry.get('matched_keywords', [])]
                logger.info(f"Added World Info: {len(triggered_world_info)} entries, triggered by: {triggered_keywords[:5]}")

        except Exception as e:
            logger.warning(f"Enhanced RAG (World Info/Memory) failed: {e}")
        # --- End Enhanced RAG ---

        messages.append({"role": "system", "content": system_prompt_text})

        # Use Enhanced Context Service for intelligent message construction
        if enhanced_context:
            # Create enhanced prompt using the Enhanced Context Service
            # NOTE: character_instructions not passed - they're already in the system message
            enhanced_prompt = enhanced_context_service.format_enhanced_prompt(
                user_message=request.message,
                context=enhanced_context,
                character_instructions=None,  # Already in system message, don't duplicate
                show_reasoning=False  # Don't show reasoning in chat (save for artifacts)
            )

            # Add the enhanced prompt as the user message
            messages.append({"role": "user", "content": enhanced_prompt})

            logger.info(f"Using Enhanced Context Service for {character['name']}: "
                       f"{len(enhanced_context.get('recent_interactions', []))} recent interactions, "
                       f"{len(enhanced_context.get('semantic_context', []))} semantic memories, "
                       f"{len(enhanced_context.get('document_chunks', []))} document chunks")

        else:
            # Fallback to simple conversation history and current message
            try:
                # Fallback conversation history from database
                history = conversation_service.get_conversation_history(session_id, limit=8, db=db)
                for msg in history:
                    messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

                logger.info(f"Using fallback conversation history: {len(history)} messages for {character['name']}")

            except Exception as e:
                logger.warning(f"Fallback conversation history failed: {e}")

            # Add current user message
            messages.append({"role": "user", "content": request.message})

        # model_config and provider were already set based on using_default_llm check above

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

        # Clean any dialogue script formatting from the response
        response = _clean_dialogue_formatting(response, character_name)

        # Save messages to database
        conversation_service.save_message(session_id, "user", request.message, db)
        conversation_service.save_message(session_id, "assistant", response, db)

        # Generate title for new conversations (after first exchange)
        try:
            session_data = conversation_service.get_session(session_id, db)
            if session_data:
                conv_id = session_data.get("conversation_id")
                if conv_id:
                    # Check if conversation needs a title (only on first exchange)
                    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
                    msg_count = db.query(Message).filter(Message.conversation_id == conv_id).count()
                    # Generate title if this is the first exchange (2 messages) and no custom title set
                    if conv and msg_count == 2 and (not conv.title or conv.title.startswith("Session with")):
                        # Use character's model config for title generation
                        conversation_service.generate_title_async(conv_id, model_config)
                        logger.debug(f"Triggered async title generation for conversation {conv_id}")
        except Exception as e:
            logger.warning(f"Title generation trigger failed: {e}")

        # Fact extraction hook - automatically learn facts from conversation
        try:
            # Only extract from substantive exchanges (message > 20 chars)
            if len(request.message) >= 20:
                import asyncio

                # Create a background task with its own database session
                # to avoid using the request's session which will be closed
                async def background_fact_extraction(
                    user_message: str,
                    assistant_response: str,
                    user_id: int,
                    character_id: str,
                    conversation_id: str
                ):
                    """Run fact deletion check and extraction with a dedicated database session."""
                    from ..database.config import db_config
                    bg_db = db_config.get_session()
                    try:
                        # First, check if user wants to delete/correct a fact
                        deleted_facts = await fact_extraction_service.delete_facts_from_message(
                            user_message=user_message,
                            user_id=user_id,
                            character_id=character_id,
                            db=bg_db
                        )
                        if deleted_facts:
                            logger.info(f"Deleted {len(deleted_facts)} facts via chat correction")

                        # Then extract new facts
                        await fact_extraction_service.extract_facts_from_message(
                            user_message=user_message,
                            assistant_response=assistant_response,
                            user_id=user_id,
                            character_id=character_id,
                            conversation_id=conversation_id,
                            message_id=None,
                            db=bg_db
                        )
                    except Exception as ex:
                        logger.warning(f"Background fact extraction failed: {ex}")
                    finally:
                        bg_db.close()

                # Run fact extraction in background (non-blocking)
                asyncio.create_task(
                    background_fact_extraction(
                        user_message=request.message,
                        assistant_response=response,
                        user_id=current_user.id,
                        character_id=request.character_id,
                        conversation_id=session_id
                    )
                )
                logger.debug(f"Triggered fact extraction for conversation {session_id}")
        except Exception as e:
            # Don't fail the chat if fact extraction fails
            logger.warning(f"Fact extraction hook failed: {e}")

        # Sidebar extraction hook - extract todos (Assistant) or life areas (Coach)
        sidebar_extractions = None
        try:
            category = character.get('category', '')
            # Only process for Assistant (todos) or Coach (life areas) categories
            if category.lower() in ['assistant', 'coach'] and len(request.message) >= 10:
                from .core.sidebar_extraction_service import sidebar_extraction_service

                # Get recent conversation context for "add this to todo" style requests
                conversation_context = []
                if enhanced_context:
                    recent = enhanced_context.get('recent_interactions', [])
                    conversation_context = [
                        {'role': msg.get('role', 'user'), 'content': msg.get('content', '')}
                        for msg in recent[-6:]  # Last 6 messages
                    ]

                extractions = await sidebar_extraction_service.process_message(
                    message=request.message,
                    user_id=current_user.id,
                    character_id=request.character_id,
                    category=category,
                    db=db,
                    conversation_context=conversation_context
                )

                # Only include if something was extracted
                if extractions.get('todos') or extractions.get('life_areas'):
                    sidebar_extractions = extractions
                    logger.info(f"Sidebar extractions: {len(extractions.get('todos', []))} todos, "
                              f"{len(extractions.get('life_areas', []))} life areas")
        except Exception as e:
            # Don't fail the chat if sidebar extraction fails
            logger.warning(f"Sidebar extraction hook failed: {e}")

        # Save additional reasoning context if available
        if reasoning_chain:
            try:
                reasoning_summary = "AI Reasoning: " + " → ".join([
                    f"{step['step']}: {step['thought'][:100]}..." if len(step['thought']) > 100
                    else f"{step['step']}: {step['thought']}"
                    for step in reasoning_chain[-3:]  # Save last 3 reasoning steps
                ])
                conversation_service.save_message(session_id, "system", reasoning_summary, db)
                logger.info(f"Saved reasoning chain for {character['name']}")
            except Exception as e:
                logger.warning(f"Failed to save reasoning chain: {e}")
        
        # Update character usage
        character_manager.update_character(request.character_id, {
            'last_used': datetime.now(timezone.utc).isoformat(),
            'conversation_count': character.get('conversation_count', 0) + 1,
            'total_messages': character.get('total_messages', 0) + 1
        })
        
        logger.info(f"Generated response for {character['name']}: {response[:100]}...")
        
        return ChatResponse(
            response=response,
            character_name=character['name'],
            character_id=character['id'],
            session_id=session_id,
            character_version=1,  # Simplified: no version tracking
            migration_available=False,
            document_context_used=document_context_used,
            sources=sources,
            context_summary=context_summary if document_context_used else None,
            context_summary_full=enhanced_context.get('context_summary', '') if document_context_used else None,
            # LLM info for frontend notification
            llm_provider=llm_provider,
            llm_model=llm_model,
            using_default_llm=using_default_llm,
            llm_message=llm_message,
            # Sidebar document extractions
            sidebar_extractions=sidebar_extractions
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/characters/{character_id}/greeting")
async def get_personalized_greeting(character_id: str, request: Request, db = Depends(get_db)):
    """Generate a personalized greeting from a character based on user profile and facts.

    This creates an in-character greeting that uses the user's name and other
    known information to make the first interaction feel personal.

    Priority for user's name:
    1. User Profile (explicitly set by user in "About You" section)
    2. Extracted Facts (learned from previous conversations)
    """
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Authentication required"})

        # Get character
        character = character_manager.get_character(character_id)
        if not character:
            return JSONResponse(status_code=404, content={"error": "Character not found"})

        character_name = character.get('name', 'Assistant')

        # First, check user profile (explicitly set by user - highest priority)
        user_profile = user_profile_service.get_user_profile(character_id)
        user_name = user_profile.get('preferred_name') if user_profile else None
        name_source = 'profile' if user_name else None

        # Fall back to extracted facts if no profile name
        user_facts = []
        if not user_name:
            user_facts = fact_extraction_service.get_user_facts(
                user_id=current_user.id,
                character_id=character_id,
                db=db
            )
            for fact in user_facts:
                if fact.get('fact_type') == 'name' or fact.get('fact_key') in ['user_name', 'name', 'first_name']:
                    user_name = fact.get('fact_value')
                    name_source = 'facts'
                    break

        # Generate greeting based on whether we know the user
        if user_name:
            # Personalized greeting - we know their name
            greeting = f"Hey {user_name}! Great to see you. What's on your mind today?"
        else:
            # First-time greeting - invite them to introduce themselves
            greeting = f"Hi there! I'm {character_name}. What's on your mind?"

        return {
            "greeting": greeting,
            "character_name": character_name,
            "user_name": user_name,
            "name_source": name_source,  # 'profile', 'facts', or None
            "facts_count": len(user_facts),
            "has_profile": bool(user_profile.get('preferred_name') or user_profile.get('brief_intro')),
            "is_returning_user": user_name is not None
        }

    except Exception as e:
        logger.error(f"Error generating greeting: {e}")
        # Return a safe fallback greeting
        return {
            "greeting": f"Hi! How can I help you today?",
            "character_name": character.get('name', 'Assistant') if character else 'Assistant',
            "user_name": None,
            "name_source": None,
            "facts_count": 0,
            "has_profile": False,
            "is_returning_user": False
        }

@app.post("/api/chat/with-document")
async def chat_with_document(
    request_obj: Request,
    message: str = Form(...),
    character_id: str = Form(...),
    session_id: Optional[str] = Form(None),
    use_documents: bool = Form(True),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Send a message with optional document upload to a character and get a response."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request_obj, db)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Authentication required"})

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
                return JSONResponse(status_code=400, content={"error": f"Document upload failed: {upload_result.get('error')}"})

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
            return JSONResponse(status_code=404, content={"error": "Character not found"})

        # Handle session management (same as original chat endpoint)
        session_id = chat_request.session_id

        if session_id:
            session = conversation_service.get_session(session_id, db)
            if not session or session.get("character_id") != chat_request.character_id:
                session_id = None

        if not session_id:
            session = conversation_service.create_session(
                chat_request.character_id,
                str(current_user.id),
                db
            )
            session_id = session["session_id"]

        # Store uploaded document ID in session for follow-up context persistence
        if uploaded_document:
            conversation_service.add_document_to_session(
                session_id=session_id,
                document_id=uploaded_document['id'],
                db=db
            )
            logger.info(f"Added document {uploaded_document['id']} to session {session_id} for context persistence")

        # Initialize context variables
        rag_context = None
        enhanced_prompt = None
        document_context_used = False
        sources = []
        context_summary = None
        migration_available = False

        # Enhanced message with document content
        enhanced_message = chat_request.message
        if uploaded_document:
            # Get the actual document content from the database
            from ..database.models import Document as DocumentModel
            doc = db.query(DocumentModel).filter(DocumentModel.id == uploaded_document['id']).first()

            if doc and doc.text_content:
                # Include the actual document text content (truncated if very long)
                doc_text = doc.text_content
                max_doc_length = 8000  # Reasonable limit for context
                if len(doc_text) > max_doc_length:
                    doc_text = doc_text[:max_doc_length] + "\n\n[Document truncated - full content available via follow-up questions]"

                doc_context = f"\n\n[Document: {uploaded_document['original_filename']}]\n"
                doc_context += f"{doc_text}\n"
                doc_context += "[End of document]\n"

                enhanced_message += doc_context
                document_context_used = True
                sources = [uploaded_document['original_filename']]
                logger.info(f"Included {len(doc_text)} chars of document content in message")
            else:
                logger.warning(f"Document {uploaded_document['id']} has no text content")

        # Get enhanced context if document RAG is enabled
        if chat_request.use_documents:
            try:
                # Include the just-uploaded document in forced context
                force_doc_ids = [uploaded_document['id']] if uploaded_document else None

                rag_context = enhanced_context_service.get_enhanced_context(
                    user_message=enhanced_message,
                    user_id=current_user.id,
                    conversation_id=None,
                    character_id=chat_request.character_id,
                    include_conversation_history=True,
                    include_documents=True,
                    force_document_ids=force_doc_ids,
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

        # Add system prompt with time awareness (with fallback for null values)
        system_prompt = character.get('system_prompt') or character.get('persona', 'You are a helpful AI assistant.')

        # Add time-aware context for the persona
        try:
            from .core.reminder_service import reminder_service
            from datetime import datetime
            time_context = reminder_service.get_context_for_chat(
                db=db,
                user_id=current_user.id,
                persona_name=character.get('name', 'Assistant')
            )

            # Always include explicit current date to help LLM with time awareness
            current_date = datetime.now()
            date_str = current_date.strftime('%B %d, %Y')  # e.g., "December 19, 2025"
            year = current_date.year

            time_prompt = f"\n\n**IMPORTANT - CURRENT DATE**: Today is {date_str}. The year is {year}, NOT {year - 1}."
            if time_context:
                time_prompt += f"\n{time_context}"
            system_prompt += time_prompt

        except Exception as e:
            logger.warning(f"Failed to get time context for chat: {e}")

        # Add artifact generation capabilities
        artifact_instructions = """

ARTIFACT GENERATION CAPABILITIES:
You can help users create and generate various types of documents and files. When a user asks you to create, generate, write, or export any kind of document, you should:

**RESPONSE FORMATTING GUIDELINES:**
When analyzing documents (especially Excel/CSV data), provide **clear, structured responses**:
- Use bullet points and clear sections
- Avoid walls of text - break up content
- Focus on key insights and actionable recommendations
- Example: "🔍 **Key Findings:** • [insight 1] • [insight 2]"

**Available formats:**
- **Markdown files (.md)**: For formatted documents, summaries, reports, and structured content
- **Text files (.txt)**: For plain text documents and simple exports
- **CSV files (.csv)**: For data tables, spreadsheets, and structured data exports

**Available document types:**
- Summaries and abstracts
- Reports and analyses
- Document exports and compilations
- Data tables and structured information
- Conversation exports
- Custom documents based on user specifications

**IMPORTANT: When a user requests content creation (speeches, summaries, outlines, etc.):**
1. If the user has provided enough context, **JUST WRITE THE CONTENT DIRECTLY** in your response
2. Do NOT keep asking for more details if the user has already given you: the topic/document, the audience, and the length/format
3. Write the full content in your chat response - users can copy it or use the Generate dropdown to save as a file
4. Only ask clarifying questions if truly essential information is missing

Example response: "I can help you create that document! Based on your request, the document would include [describe content]. To generate the actual file, please click the 'Generate' button in the chat interface and select the format you prefer (Markdown, PDF, etc.)."

You should be proactive about offering to create documents when it would be helpful for organizing or presenting information, but always direct users to the proper artifact generation interface."""

        system_prompt += artifact_instructions

        messages.append({"role": "system", "content": system_prompt})

        # Try to use semantic memory service for intelligent context retrieval
        try:
            from .core.memory_service import memory_service
            # conversation_service already imported at module level

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
            # Fallback to simple conversation history from database
            history = conversation_service.get_conversation_history(session_id, limit=15, db=db)
            for msg in history:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

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

        # Generate response using the character's model configuration (with app LLM fallback)
        model_config = _resolve_model_config(character.get('model_config'), current_user.id, db)
        provider = model_config['provider']  # Guaranteed by _resolve_model_config

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

        # Save messages to database
        conversation_service.save_message(session_id, "user", chat_request.message, db)
        conversation_service.save_message(session_id, "assistant", response, db)

        # Generate title for new conversations (after first exchange)
        try:
            session_data = conversation_service.get_session(session_id, db)
            if session_data:
                conv_id = session_data.get("conversation_id")
                if conv_id:
                    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
                    msg_count = db.query(Message).filter(Message.conversation_id == conv_id).count()
                    if conv and msg_count == 2 and (not conv.title or conv.title.startswith("Session with")):
                        conversation_service.generate_title_async(conv_id, model_config)
        except Exception as e:
            logger.warning(f"Title generation trigger failed: {e}")

        # Update character usage
        character_manager.update_character(chat_request.character_id, {
            'last_used': datetime.now(timezone.utc).isoformat(),
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
            "character_version": session.get('character_version', 1),
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
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/suggest_system_prompt")
async def suggest_system_prompt(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    backstory = data.get('backstory', '')
    category = data.get('category', '')

    # Get user's assistant LLM config
    current_user = await get_current_user_from_session(request, db)
    if current_user:
        model_config = settings_service.get_assistant_llm_config(current_user.id, db)
    else:
        # Default config for unauthenticated users
        model_config = {"provider": "ollama", "model": "llama3.1:8b", "temperature": 0.7, "max_tokens": 512}

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
async def suggest_traits(
    request_obj: Request,
    request: SuggestTraitsRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Suggest personality traits and communication style from a backstory using the LLM."""
    # Get user's assistant LLM config
    current_user = await get_current_user_from_session(request_obj, db)
    if current_user:
        model_config = settings_service.get_assistant_llm_config(current_user.id, db)
    else:
        # Default config for unauthenticated users
        model_config = {"provider": "ollama", "model": "llama3.1:8b", "temperature": 0.7, "max_tokens": 512}

    prompt = f"""
Given the following backstory for a character, suggest a set of core personality traits (as a dictionary of trait name to value from 0.0 to 1.0) and a communication style (as a dictionary of style name to value from 0.0 to 1.0). Only return valid JSON with two keys: 'traits' and 'communication_style'.

IMPORTANT: Only use the following traits: {', '.join(FIXED_TRAITS)}. Only use the following communication styles: {', '.join(FIXED_COMM_STYLES)}. If you don't have enough information for a trait/style, set it to 0.5.

Backstory: {request.backstory}
Category: {request.category or ''}
"""
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
    credentials: Optional[Dict[str, str]] = None

class TestConnectionRequest(BaseModel):
    provider: str
    config: Dict[str, Any]

@app.get("/api/settings/llm")
async def get_llm_settings(request: Request, db = Depends(get_db)):
    """Get current LLM settings for the authenticated user."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return JSONResponse(status_code=401, content={"error": "Authentication required"})

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
        return JSONResponse(status_code=401, content={"error": "Authentication required"})

    config = request.dict()
    success = settings_service.update_llm_config(current_user.id, db, config)

    if success:
        return {"success": True, "message": "Settings updated successfully"}
    else:
        return JSONResponse(status_code=400, content={"success": False, "error": "Failed to update settings"})

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

@app.get("/api/settings/llm/status")
async def get_llm_status(request: Request, db = Depends(get_db)):
    """Check if the user's LLM settings are configured and available.

    This endpoint should be called on login/dashboard load to ensure
    the user has a working LLM before attempting to chat.

    Returns:
        - configured: bool - whether settings exist
        - available: bool - whether the configured LLM is reachable
        - provider: str - configured provider name
        - model: str - configured model name
        - message: str - human-readable status message
        - needs_setup: bool - whether user needs to configure LLM settings
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    status = settings_service.check_llm_status(current_user.id, db)
    return status

@app.get("/api/characters/{character_id}/llm-status")
async def get_character_llm_status(character_id: str, request: Request, db = Depends(get_db)):
    """Check if a character's LLM configuration is available.

    Returns information about whether the character's configured LLM
    is available, or if the system default will be used instead.

    Returns:
        - available: bool
        - using_default: bool - true if falling back to system default
        - provider: str
        - model: str
        - message: str
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    character = character_manager.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    character_model_config = character.get('model_config')
    status = settings_service.check_character_llm_status(
        current_user.id,
        character_model_config,
        db
    )
    return status

@app.get("/api/settings/application-llm")
async def get_application_llm_settings(request: Request, db = Depends(get_db)):
    """Get current Application LLM settings for the authenticated user.

    This is the LLM used for app-wide utility tasks like generating persona prompts,
    suggesting traits, etc. Separate from per-persona chat LLMs.
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    config = settings_service.get_assistant_llm_config(current_user.id, db)
    return {
        "provider": config.get("provider", "ollama"),
        "model": config.get("model", "llama3.1:8b")
    }

@app.post("/api/settings/application-llm")
async def update_application_llm_settings(request: Request, db = Depends(get_db)):
    """Update Application LLM settings for the authenticated user.

    This is the LLM used for app-wide utility tasks like generating persona prompts,
    suggesting traits, etc. Separate from per-persona chat LLMs.
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    data = await request.json()
    provider = data.get("provider", "ollama")
    model = data.get("model", "llama3.1:8b")

    success = settings_service.update_assistant_llm_config(current_user.id, db, provider, model)

    if success:
        return {"success": True, "message": "Application LLM settings updated successfully"}
    else:
        raise HTTPException(status_code=400, detail="Failed to update settings")

@app.get("/api/settings/user")
async def get_user_settings(request: Request, db = Depends(get_db)):
    """Get all user settings for the authenticated user."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        return JSONResponse(status_code=401, content={"error": "Authentication required"})

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
        return JSONResponse(status_code=401, content={"error": "Authentication required"})

    data = await request.json()
    settings = settings_service.update_user_settings(current_user.id, db, **data)

    if settings:
        return {"success": True, "message": "Settings updated successfully"}
    else:
        return JSONResponse(status_code=400, content={"success": False, "error": "Failed to update settings"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080) 
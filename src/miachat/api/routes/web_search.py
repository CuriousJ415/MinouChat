"""
Web Search API Routes.

Provides endpoints for performing web searches via DuckDuckGo.
Only available to personas with web_search capability enabled.

Endpoints:
- POST /api/search/ - Perform a web search
- GET /api/search/detect-intent - Detect search intent in a message
- GET /api/search/capability/{character_id} - Check character search capability
- GET /api/search/status - Check if search service is available
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from miachat.database.config import get_db
from ..core.auth import get_current_user_from_session
from ..core.character_manager import character_manager
from ..core.web_search_service import (
    web_search_service,
    WebSearchError,
    WebSearchUnavailableError,
    WebSearchRateLimitError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["web-search"])


# ==================== PYDANTIC MODELS ====================

class SearchRequest(BaseModel):
    """Request model for web search."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query text"
    )
    character_id: Optional[str] = Field(
        None,
        description="Character ID to check capability (optional)"
    )
    max_results: int = Field(
        5,
        ge=1,
        le=10,
        description="Maximum results to return (1-10)"
    )
    search_type: str = Field(
        "web",
        description="Type of search: 'web' or 'news'"
    )
    timelimit: Optional[str] = Field(
        None,
        description="Time limit: d (day), w (week), m (month), y (year)"
    )

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate and clean query string."""
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty or whitespace only")
        return v

    @field_validator('search_type')
    @classmethod
    def validate_search_type(cls, v: str) -> str:
        """Validate search type."""
        if v not in ('web', 'news'):
            raise ValueError("search_type must be 'web' or 'news'")
        return v

    @field_validator('timelimit')
    @classmethod
    def validate_timelimit(cls, v: Optional[str]) -> Optional[str]:
        """Validate time limit value."""
        if v is not None and v not in ('d', 'w', 'm', 'y'):
            raise ValueError("timelimit must be 'd', 'w', 'm', or 'y'")
        return v


class SearchResultItem(BaseModel):
    """Model for a single search result."""
    title: str
    url: str
    snippet: str
    source: str
    type: str = "web"


class SearchResponse(BaseModel):
    """Response model for web search."""
    query: str
    results: List[SearchResultItem]
    result_count: int
    formatted_context: Optional[str] = None
    search_type: str = "web"


class SearchIntentResponse(BaseModel):
    """Response model for search intent detection."""
    should_search: bool
    query: Optional[str] = None
    type: Optional[str] = None


class CapabilityResponse(BaseModel):
    """Response model for capability check."""
    character_id: str
    character_name: str
    web_search_enabled: bool
    category: str


class StatusResponse(BaseModel):
    """Response model for service status."""
    available: bool
    message: str


# ==================== ENDPOINTS ====================

@router.post("/", response_model=SearchResponse)
async def perform_search(
    request: SearchRequest,
    request_obj: Request,
    db: Session = Depends(get_db)
) -> SearchResponse:
    """Perform a web search.

    If character_id is provided, validates that the character has web_search
    capability enabled. Returns search results formatted for both display
    and LLM context.

    Args:
        request: Search parameters including query and options.
        request_obj: HTTP request for auth extraction.
        db: Database session.

    Returns:
        SearchResponse with results and formatted context.

    Raises:
        HTTPException 401: If not authenticated.
        HTTPException 403: If character doesn't have web search capability.
        HTTPException 404: If character not found.
        HTTPException 503: If search service unavailable.
        HTTPException 429: If rate limited.
    """
    # Authenticate user
    current_user = await get_current_user_from_session(request_obj, db)
    if not current_user:
        logger.warning("Unauthenticated search attempt")
        raise HTTPException(status_code=401, detail="Authentication required")

    # Validate character capability if character_id provided
    if request.character_id:
        character = character_manager.get_character(request.character_id)
        if not character:
            logger.warning(f"Search attempted for non-existent character: {request.character_id}")
            raise HTTPException(status_code=404, detail="Character not found")

        if not web_search_service.check_capability(character):
            logger.info(
                f"Search blocked - web_search not enabled for character {request.character_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Web search is not enabled for this character. "
                       "Enable it in character settings under Capabilities."
            )

    # Check service availability
    if not web_search_service.is_available():
        logger.error("Web search service unavailable - package not installed")
        raise HTTPException(
            status_code=503,
            detail="Web search service is not available. "
                   "Please install duckduckgo-search package."
        )

    try:
        # Perform the search based on type
        if request.search_type == "news":
            results = web_search_service.search_news(
                query=request.query,
                max_results=request.max_results,
                timelimit=request.timelimit or "w"
            )
        else:
            results = web_search_service.search(
                query=request.query,
                max_results=request.max_results,
                timelimit=request.timelimit
            )

        # Format results
        formatted_results = web_search_service.format_results_for_display(results)
        formatted_context = web_search_service.format_results_for_context(
            results, request.query
        )

        logger.info(
            f"Search completed for user {current_user.id}: "
            f"query='{request.query[:30]}...', results={len(results)}"
        )

        return SearchResponse(
            query=request.query,
            results=[SearchResultItem(**r) for r in formatted_results],
            result_count=len(results),
            formatted_context=formatted_context,
            search_type=request.search_type
        )

    except WebSearchRateLimitError as e:
        logger.warning(f"Rate limited during search: {e}")
        raise HTTPException(
            status_code=429,
            detail="Search rate limit exceeded. Please try again in a moment."
        )
    except WebSearchError as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Search service error: {str(e)}"
        )


@router.get("/detect-intent", response_model=SearchIntentResponse)
async def detect_search_intent(
    message: str = Query(..., min_length=1, max_length=1000, description="Message to analyze"),
    request_obj: Request = None,
    db: Session = Depends(get_db)
) -> SearchIntentResponse:
    """Detect if a message implies a need for web search.

    Useful for the frontend to show a search suggestion button when
    the user's message contains search triggers like "search for...",
    "what's the latest...", etc.

    Args:
        message: User message to analyze for search intent.
        request_obj: HTTP request for auth extraction.
        db: Database session.

    Returns:
        SearchIntentResponse indicating whether to suggest search.

    Raises:
        HTTPException 401: If not authenticated.
    """
    current_user = await get_current_user_from_session(request_obj, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    intent = web_search_service.detect_search_intent(message)

    logger.debug(
        f"Intent detection for message '{message[:30]}...': "
        f"should_search={intent.should_search}, type={intent.intent_type}"
    )

    return SearchIntentResponse(
        should_search=intent.should_search,
        query=intent.query,
        type=intent.intent_type
    )


@router.get("/capability/{character_id}", response_model=CapabilityResponse)
async def check_search_capability(
    character_id: str,
    request_obj: Request,
    db: Session = Depends(get_db)
) -> CapabilityResponse:
    """Check if a character has web search capability enabled.

    Args:
        character_id: Character ID to check.
        request_obj: HTTP request for auth extraction.
        db: Database session.

    Returns:
        CapabilityResponse with capability status.

    Raises:
        HTTPException 401: If not authenticated.
        HTTPException 404: If character not found.
    """
    current_user = await get_current_user_from_session(request_obj, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    character = character_manager.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    has_capability = web_search_service.check_capability(character)

    logger.debug(
        f"Capability check for character {character_id}: "
        f"web_search={has_capability}"
    )

    return CapabilityResponse(
        character_id=character_id,
        character_name=character.get("name", "Unknown"),
        web_search_enabled=has_capability,
        category=character.get("category", "Other")
    )


@router.get("/status", response_model=StatusResponse)
async def check_service_status(
    request_obj: Request,
    db: Session = Depends(get_db)
) -> StatusResponse:
    """Check if the web search service is available.

    Returns whether the duckduckgo-search package is installed
    and the service is operational.

    Args:
        request_obj: HTTP request for auth extraction.
        db: Database session.

    Returns:
        StatusResponse with availability status.

    Raises:
        HTTPException 401: If not authenticated.
    """
    current_user = await get_current_user_from_session(request_obj, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    is_available = web_search_service.is_available()

    if is_available:
        return StatusResponse(
            available=True,
            message="Web search service is available and operational"
        )
    else:
        return StatusResponse(
            available=False,
            message="Web search service is not available. "
                    "The duckduckgo-search package may not be installed."
        )

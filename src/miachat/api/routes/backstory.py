"""
Backstory API routes for managing character backstory with semantic retrieval.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database.config import get_db
from ..core.clerk_auth import get_current_user_from_session
from ..core.backstory_service import backstory_service

router = APIRouter(prefix="/api/characters", tags=["backstory"])


# Pydantic models
class BackstoryUpdateRequest(BaseModel):
    backstory: str = Field(..., max_length=50000)  # Max ~10k words


class BackstorySearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=3, ge=1, le=10)


@router.get("/{character_id}/backstory")
async def get_character_backstory(
    character_id: str,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get the full backstory for a character."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    backstory = backstory_service.get_full_backstory(character_id)
    stats = backstory_service.get_backstory_stats(character_id, current_user.id, db)

    return {
        "success": True,
        "backstory": backstory,
        "stats": stats
    }


@router.put("/{character_id}/backstory")
async def update_character_backstory(
    character_id: str,
    backstory_data: BackstoryUpdateRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Save/update the backstory for a character.

    This triggers re-chunking and re-embedding of the backstory
    for semantic retrieval.
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    success = backstory_service.save_backstory(
        character_id=character_id,
        user_id=current_user.id,
        backstory_text=backstory_data.backstory,
        db=db
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to save backstory. Check server logs."
        )

    stats = backstory_service.get_backstory_stats(character_id, current_user.id, db)

    return {
        "success": True,
        "message": f"Backstory saved and indexed ({stats['chunk_count']} chunks)",
        "stats": stats
    }


@router.post("/{character_id}/backstory/search")
async def search_backstory(
    character_id: str,
    search_data: BackstorySearchRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Search for relevant backstory chunks using semantic similarity.

    Useful for testing/debugging what backstory would be retrieved
    for a given conversation context.
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    relevant_chunks = backstory_service.get_relevant_backstory(
        character_id=character_id,
        user_id=current_user.id,
        query=search_data.query,
        db=db,
        top_k=search_data.top_k
    )

    return {
        "success": True,
        "query": search_data.query,
        "chunks": relevant_chunks,
        "count": len(relevant_chunks)
    }


@router.get("/{character_id}/backstory/context")
async def get_backstory_context(
    character_id: str,
    query: str = "",
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Get formatted backstory context for system prompt injection.

    Pass a query (recent conversation text) to get contextually
    relevant backstory chunks.
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    context = backstory_service.format_backstory_context(
        character_id=character_id,
        user_id=current_user.id,
        query=query or "general conversation",
        db=db
    )

    return {
        "success": True,
        "context": context,
        "has_content": bool(context)
    }


@router.delete("/{character_id}/backstory")
async def delete_character_backstory(
    character_id: str,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Delete all backstory and chunks for a character.
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Save empty backstory to clear chunks
    success = backstory_service.save_backstory(
        character_id=character_id,
        user_id=current_user.id,
        backstory_text="",
        db=db
    )

    return {
        "success": success,
        "message": "Backstory cleared" if success else "Failed to clear backstory"
    }

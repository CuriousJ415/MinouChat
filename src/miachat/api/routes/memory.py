"""
Persistent Memory API routes.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database.config import get_db
from ...database.models import PersistentMemory
from ..core.auth import get_current_user_from_session
from ..core.persistent_memory_service import persistent_memory_service

router = APIRouter(prefix="/api/memory", tags=["memory"])


# Valid insertion positions
VALID_POSITIONS = ['start', 'after_system_prompt', 'before_conversation', 'before_user_message']


# Pydantic models for request/response
class MemoryCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    character_id: Optional[str] = None
    is_enabled: bool = True
    priority: int = Field(default=100, ge=0, le=1000)
    insertion_position: str = Field(default='before_conversation')
    max_tokens: Optional[int] = Field(default=None, ge=10)

    def validate_position(self):
        if self.insertion_position not in VALID_POSITIONS:
            raise ValueError(f"insertion_position must be one of: {VALID_POSITIONS}")


class MemoryUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    character_id: Optional[str] = None
    is_enabled: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=1000)
    insertion_position: Optional[str] = None
    max_tokens: Optional[int] = Field(None, ge=10)


class MemoryResponse(BaseModel):
    id: int
    name: str
    content: str
    character_id: Optional[str]
    is_enabled: bool
    priority: int
    insertion_position: str
    token_count: Optional[int]
    max_tokens: Optional[int]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get("")
async def list_memories(
    character_id: Optional[str] = None,
    enabled_only: bool = True,
    insertion_position: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """List all persistent memories for the current user.

    Args:
        character_id: Filter by character (also includes global memories)
        enabled_only: Only return enabled memories
        insertion_position: Filter by position
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if insertion_position and insertion_position not in VALID_POSITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid insertion_position. Must be one of: {VALID_POSITIONS}"
        )

    memories = persistent_memory_service.get_user_memories(
        user_id=current_user.id,
        character_id=character_id,
        enabled_only=enabled_only,
        insertion_position=insertion_position,
        db=db
    )

    return {
        "success": True,
        "memories": [memory.to_dict() for memory in memories],
        "count": len(memories)
    }


@router.post("")
async def create_memory(
    memory_data: MemoryCreateRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Create a new persistent memory."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if memory_data.insertion_position not in VALID_POSITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid insertion_position. Must be one of: {VALID_POSITIONS}"
        )

    memory = persistent_memory_service.create_memory(
        user_id=current_user.id,
        memory_data=memory_data.model_dump(),
        db=db
    )

    return {
        "success": True,
        "memory": memory.to_dict(),
        "message": f"Persistent memory '{memory.name}' created successfully"
    }


@router.get("/positions")
async def get_valid_positions():
    """Get list of valid insertion positions with descriptions."""
    return {
        "success": True,
        "positions": [
            {
                "id": "start",
                "name": "Start of Context",
                "description": "Injected at the very beginning, before system prompt"
            },
            {
                "id": "after_system_prompt",
                "name": "After System Prompt",
                "description": "Injected immediately after character system prompt"
            },
            {
                "id": "before_conversation",
                "name": "Before Conversation",
                "description": "Injected before conversation history (default)"
            },
            {
                "id": "before_user_message",
                "name": "Before User Message",
                "description": "Injected just before the current user message"
            }
        ]
    }


@router.get("/{memory_id}")
async def get_memory(
    memory_id: int,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get a specific persistent memory."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    memory = db.query(PersistentMemory).filter(
        PersistentMemory.id == memory_id,
        PersistentMemory.user_id == current_user.id
    ).first()

    if not memory:
        raise HTTPException(status_code=404, detail="Persistent memory not found")

    return {
        "success": True,
        "memory": memory.to_dict()
    }


@router.put("/{memory_id}")
async def update_memory(
    memory_id: int,
    memory_data: MemoryUpdateRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Update a persistent memory."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if memory_data.insertion_position and memory_data.insertion_position not in VALID_POSITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid insertion_position. Must be one of: {VALID_POSITIONS}"
        )

    # Only include fields that were actually provided
    update_data = {k: v for k, v in memory_data.model_dump().items() if v is not None}

    memory = persistent_memory_service.update_memory(
        memory_id=memory_id,
        user_id=current_user.id,
        memory_data=update_data,
        db=db
    )

    if not memory:
        raise HTTPException(status_code=404, detail="Persistent memory not found")

    return {
        "success": True,
        "memory": memory.to_dict(),
        "message": f"Persistent memory '{memory.name}' updated successfully"
    }


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: int,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Delete a persistent memory."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    success = persistent_memory_service.delete_memory(
        memory_id=memory_id,
        user_id=current_user.id,
        db=db
    )

    if not success:
        raise HTTPException(status_code=404, detail="Persistent memory not found")

    return {
        "success": True,
        "message": "Persistent memory deleted successfully"
    }


@router.get("/preview/context")
async def preview_memory_context(
    character_id: Optional[str] = None,
    insertion_position: Optional[str] = None,
    token_budget: Optional[int] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Preview how persistent memory context would be built.

    Useful for debugging and seeing what will be injected.
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    context = persistent_memory_service.build_memory_context(
        user_id=current_user.id,
        character_id=character_id,
        token_budget=token_budget,
        insertion_position=insertion_position,
        format_style='sections',
        db=db
    )

    from ..core.token_service import token_service
    token_count = token_service.count_tokens(context)

    return {
        "success": True,
        "context": context,
        "token_count": token_count,
        "character_id": character_id,
        "insertion_position": insertion_position
    }


@router.get("/stats/summary")
async def get_memory_stats(
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get persistent memory statistics for the current user."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    stats = persistent_memory_service.get_stats(
        user_id=current_user.id,
        db=db
    )

    return {
        "success": True,
        "stats": stats
    }

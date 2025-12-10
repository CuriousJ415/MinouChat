"""
World Info API routes for managing lorebook/world info entries.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database.config import get_db
from ...database.models import WorldInfoEntry
from ..core.auth import get_current_user_from_session
from ..core.world_info_service import world_info_service

router = APIRouter(prefix="/api/world-info", tags=["world-info"])


# Pydantic models for request/response
class WorldInfoCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    keywords: List[str] = Field(..., min_items=1)
    character_id: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    regex_pattern: Optional[str] = None
    case_sensitive: bool = False
    match_whole_word: bool = True
    priority: int = Field(default=100, ge=0, le=1000)
    is_enabled: bool = True
    insertion_order: int = Field(default=0, ge=0)
    max_tokens: Optional[int] = Field(default=None, ge=10)
    activation_conditions: Optional[dict] = None


class WorldInfoUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    keywords: Optional[List[str]] = None
    character_id: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    regex_pattern: Optional[str] = None
    case_sensitive: Optional[bool] = None
    match_whole_word: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=1000)
    is_enabled: Optional[bool] = None
    insertion_order: Optional[int] = Field(None, ge=0)
    max_tokens: Optional[int] = Field(None, ge=10)
    activation_conditions: Optional[dict] = None


class WorldInfoTestRequest(BaseModel):
    text: str = Field(..., min_length=1)
    character_id: Optional[str] = None


class WorldInfoResponse(BaseModel):
    id: int
    name: str
    content: str
    keywords: List[str]
    character_id: Optional[str]
    description: Optional[str]
    category: Optional[str]
    case_sensitive: bool
    match_whole_word: bool
    priority: int
    is_enabled: bool
    insertion_order: int
    token_count: Optional[int]
    max_tokens: Optional[int]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get("")
async def list_world_info(
    character_id: Optional[str] = None,
    category: Optional[str] = None,
    enabled_only: bool = True,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """List all World Info entries for the current user.

    Args:
        character_id: Filter by character (also includes global entries)
        category: Filter by category
        enabled_only: Only return enabled entries
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    entries = world_info_service.get_user_entries(
        user_id=current_user.id,
        character_id=character_id,
        category=category,
        enabled_only=enabled_only,
        db=db
    )

    return {
        "success": True,
        "entries": [entry.to_dict() for entry in entries],
        "count": len(entries)
    }


@router.post("")
async def create_world_info(
    entry_data: WorldInfoCreateRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Create a new World Info entry."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    entry = world_info_service.create_entry(
        user_id=current_user.id,
        entry_data=entry_data.model_dump(),
        db=db
    )

    return {
        "success": True,
        "entry": entry.to_dict(),
        "message": f"World Info entry '{entry.name}' created successfully"
    }


@router.get("/{entry_id}")
async def get_world_info(
    entry_id: int,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get a specific World Info entry."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    entry = db.query(WorldInfoEntry).filter(
        WorldInfoEntry.id == entry_id,
        WorldInfoEntry.user_id == current_user.id
    ).first()

    if not entry:
        raise HTTPException(status_code=404, detail="World Info entry not found")

    return {
        "success": True,
        "entry": entry.to_dict()
    }


@router.put("/{entry_id}")
async def update_world_info(
    entry_id: int,
    entry_data: WorldInfoUpdateRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Update a World Info entry."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Only include fields that were actually provided
    update_data = {k: v for k, v in entry_data.model_dump().items() if v is not None}

    entry = world_info_service.update_entry(
        entry_id=entry_id,
        user_id=current_user.id,
        entry_data=update_data,
        db=db
    )

    if not entry:
        raise HTTPException(status_code=404, detail="World Info entry not found")

    return {
        "success": True,
        "entry": entry.to_dict(),
        "message": f"World Info entry '{entry.name}' updated successfully"
    }


@router.delete("/{entry_id}")
async def delete_world_info(
    entry_id: int,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Delete a World Info entry."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    success = world_info_service.delete_entry(
        entry_id=entry_id,
        user_id=current_user.id,
        db=db
    )

    if not success:
        raise HTTPException(status_code=404, detail="World Info entry not found")

    return {
        "success": True,
        "message": "World Info entry deleted successfully"
    }


@router.post("/test")
async def test_world_info(
    test_request: WorldInfoTestRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Test which World Info entries would be triggered by given text.

    Useful for debugging and previewing keyword matches.
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    results = world_info_service.test_triggers(
        text=test_request.text,
        user_id=current_user.id,
        character_id=test_request.character_id,
        db=db
    )

    triggered = [r for r in results if r['triggered']]

    return {
        "success": True,
        "text": test_request.text,
        "triggered_count": len(triggered),
        "results": results
    }


@router.get("/stats/summary")
async def get_world_info_stats(
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get World Info statistics for the current user."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    stats = world_info_service.get_stats(
        user_id=current_user.id,
        db=db
    )

    return {
        "success": True,
        "stats": stats
    }


@router.post("/bulk")
async def bulk_create_world_info(
    entries: List[WorldInfoCreateRequest],
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Bulk create World Info entries.

    Useful for importing multiple entries at once.
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    created = []
    errors = []

    for i, entry_data in enumerate(entries):
        try:
            entry = world_info_service.create_entry(
                user_id=current_user.id,
                entry_data=entry_data.model_dump(),
                db=db
            )
            created.append(entry.to_dict())
        except Exception as e:
            errors.append({
                "index": i,
                "name": entry_data.name,
                "error": str(e)
            })

    return {
        "success": len(errors) == 0,
        "created_count": len(created),
        "error_count": len(errors),
        "created": created,
        "errors": errors
    }

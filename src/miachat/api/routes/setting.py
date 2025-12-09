"""
Setting API routes for managing character setting/world context.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database.config import get_db
from ..core.auth import get_current_user_from_session
from ..core.setting_service import setting_service

router = APIRouter(prefix="/api/characters", tags=["setting"])


# Pydantic models
class SettingUpdateRequest(BaseModel):
    world: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=500)
    time_period: Optional[str] = Field(None, max_length=500)
    key_facts: Optional[List[str]] = None


class KeyFactRequest(BaseModel):
    fact: str = Field(..., min_length=1, max_length=500)


class SettingResponse(BaseModel):
    world: str
    location: str
    time_period: str
    key_facts: List[str]


@router.get("/{character_id}/setting")
async def get_character_setting(
    character_id: str,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get the setting for a character."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    setting = setting_service.get_setting(character_id)

    return {
        "success": True,
        "setting": setting
    }


@router.put("/{character_id}/setting")
async def update_character_setting(
    character_id: str,
    setting_data: SettingUpdateRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Update the setting for a character."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Build update dict from provided fields
    update_dict = {}
    if setting_data.world is not None:
        update_dict['world'] = setting_data.world
    if setting_data.location is not None:
        update_dict['location'] = setting_data.location
    if setting_data.time_period is not None:
        update_dict['time_period'] = setting_data.time_period
    if setting_data.key_facts is not None:
        update_dict['key_facts'] = setting_data.key_facts

    # Merge with existing setting
    existing = setting_service.get_setting(character_id)
    existing.update(update_dict)

    updated = setting_service.update_setting(character_id, existing)

    if not updated:
        raise HTTPException(status_code=404, detail="Character not found")

    return {
        "success": True,
        "setting": updated,
        "message": "Setting updated successfully"
    }


@router.post("/{character_id}/setting/facts")
async def add_key_fact(
    character_id: str,
    fact_data: KeyFactRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Add a key fact to the character's setting."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    key_facts = setting_service.add_key_fact(character_id, fact_data.fact)

    if key_facts is None:
        raise HTTPException(status_code=404, detail="Character not found")

    return {
        "success": True,
        "key_facts": key_facts,
        "message": "Key fact added"
    }


@router.delete("/{character_id}/setting/facts/{fact_index}")
async def remove_key_fact(
    character_id: str,
    fact_index: int,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Remove a key fact by index."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    key_facts = setting_service.remove_key_fact(character_id, fact_index)

    if key_facts is None:
        raise HTTPException(status_code=404, detail="Character not found or invalid index")

    return {
        "success": True,
        "key_facts": key_facts,
        "message": "Key fact removed"
    }


@router.get("/{character_id}/setting/context")
async def get_setting_context(
    character_id: str,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get the formatted setting context for system prompt injection."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    context = setting_service.format_setting_context(character_id)

    return {
        "success": True,
        "context": context,
        "has_content": bool(context)
    }

"""
Facts API routes for managing automatically extracted conversation facts.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database.config import get_db
from ..core.clerk_auth import get_current_user_from_session
from ..core.fact_extraction_service import fact_extraction_service

router = APIRouter(prefix="/api/facts", tags=["facts"])


# Pydantic models
class FactUpdateRequest(BaseModel):
    fact_value: str = Field(..., min_length=1, max_length=1000)


class FactCreateRequest(BaseModel):
    fact_type: str = Field(..., description="Type of fact: name, preference, relationship, event, trait, location, occupation, hobby, goal, other")
    fact_key: str = Field(..., min_length=1, max_length=100, description="Label for the fact (e.g., 'favorite_color')")
    fact_value: str = Field(..., min_length=1, max_length=1000, description="The fact value (e.g., 'blue')")
    character_id: Optional[str] = Field(None, description="Character ID, or null for global facts")


class FactExtractRequest(BaseModel):
    user_message: str = Field(..., min_length=1, max_length=2000)
    assistant_response: str = Field(..., min_length=1, max_length=2000)
    character_id: Optional[str] = None


@router.get("")
async def list_facts(
    character_id: Optional[str] = None,
    include_global: bool = True,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    List all facts known about the current user.

    Args:
        character_id: Optional filter by character
        include_global: Whether to include facts with no character_id
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    facts = fact_extraction_service.get_user_facts(
        user_id=current_user.id,
        character_id=character_id,
        db=db,
        include_global=include_global
    )

    return {
        "success": True,
        "facts": facts,
        "count": len(facts)
    }


@router.post("")
async def create_fact(
    fact_data: FactCreateRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Manually create a new fact about the user.

    Use this to add facts that weren't automatically extracted from conversations.
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Validate fact_type
    valid_types = ['name', 'preference', 'relationship', 'event', 'trait',
                   'location', 'occupation', 'hobby', 'goal', 'other']
    if fact_data.fact_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fact_type. Must be one of: {', '.join(valid_types)}"
        )

    created = fact_extraction_service.create_fact(
        user_id=current_user.id,
        fact_type=fact_data.fact_type,
        fact_key=fact_data.fact_key,
        fact_value=fact_data.fact_value,
        character_id=fact_data.character_id,
        db=db
    )

    if not created:
        raise HTTPException(status_code=400, detail="Failed to create fact. Check input values.")

    return {
        "success": True,
        "fact": created,
        "message": "Fact created successfully"
    }


@router.get("/{fact_id}")
async def get_fact(
    fact_id: int,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get a specific fact by ID."""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Get all facts and find the specific one
    facts = fact_extraction_service.get_user_facts(
        user_id=current_user.id,
        db=db
    )

    fact = next((f for f in facts if f['id'] == fact_id), None)

    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")

    return {
        "success": True,
        "fact": fact
    }


@router.put("/{fact_id}")
async def update_fact(
    fact_id: int,
    update_data: FactUpdateRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Update a fact's value.

    Use this to correct facts that were extracted incorrectly.
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    updated = fact_extraction_service.update_fact(
        fact_id=fact_id,
        new_value=update_data.fact_value,
        user_id=current_user.id,
        db=db
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Fact not found")

    return {
        "success": True,
        "fact": updated,
        "message": "Fact updated successfully"
    }


@router.delete("/{fact_id}")
async def delete_fact(
    fact_id: int,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Delete a fact.

    Use this to remove incorrect or unwanted facts.
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    success = fact_extraction_service.delete_fact(
        fact_id=fact_id,
        user_id=current_user.id,
        db=db
    )

    if not success:
        raise HTTPException(status_code=404, detail="Fact not found")

    return {
        "success": True,
        "message": "Fact deleted successfully"
    }


@router.post("/extract")
async def extract_facts(
    extract_data: FactExtractRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Manually trigger fact extraction from a conversation exchange.

    Useful for testing or manually adding facts from past conversations.
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    extracted = await fact_extraction_service.extract_facts_from_message(
        user_message=extract_data.user_message,
        assistant_response=extract_data.assistant_response,
        user_id=current_user.id,
        character_id=extract_data.character_id,
        conversation_id=None,
        message_id=None,
        db=db
    )

    return {
        "success": True,
        "extracted_facts": extracted,
        "count": len(extracted)
    }


@router.get("/context/{character_id}")
async def get_facts_context(
    character_id: str,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Get formatted facts context for system prompt injection.
    """
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    context = fact_extraction_service.format_facts_context(
        user_id=current_user.id,
        character_id=character_id,
        db=db
    )

    return {
        "success": True,
        "context": context,
        "has_content": bool(context)
    }

"""
Life Areas API routes for MinouChat.

Provides endpoints for managing life area scorecards in the sidebar.
Used with Coach-category personas.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.life_area_service import life_area_service
from ..core.clerk_auth import get_current_user_from_session
from ...database.config import get_db
from ...database.models import LIFE_AREAS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/life-areas", tags=["life-areas"])


# Request models
class LifeAreaUpdateRequest(BaseModel):
    character_id: str
    score: int  # 1-10
    notes: Optional[str] = None


@router.get("")
async def get_scorecard(
    request: Request,
    character_id: str = Query(..., description="Character ID"),
    db: Session = Depends(get_db)
):
    """Get the full life areas scorecard for a character.

    Args:
        character_id: Character ID

    Returns:
        Scorecard with all areas and their scores
    """
    try:
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        scorecard = life_area_service.get_scorecard(
            user_id=current_user.id,
            character_id=character_id,
            db=db
        )

        average = life_area_service.get_average_score(
            user_id=current_user.id,
            character_id=character_id,
            db=db
        )

        return {
            "scorecard": scorecard,
            "average": average,
            "character_id": character_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scorecard: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get scorecard")


@router.put("/{area}")
async def update_score(
    area: str,
    request: Request,
    update_data: LifeAreaUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update or create a life area score.

    Args:
        area: Life area name (career, finances, health, etc.)
        update_data: Score and optional notes

    Returns:
        Updated score data
    """
    try:
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Validate area
        if area not in LIFE_AREAS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid area: {area}. Valid areas: {LIFE_AREAS}"
            )

        # Validate score
        if not 1 <= update_data.score <= 10:
            raise HTTPException(
                status_code=400,
                detail="Score must be between 1 and 10"
            )

        score = life_area_service.update_score(
            user_id=current_user.id,
            character_id=update_data.character_id,
            area=area,
            score=update_data.score,
            notes=update_data.notes,
            source_type='manual',
            db=db
        )

        return score

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating score for {area}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update score")


@router.get("/areas")
async def list_available_areas():
    """Get list of all available life areas.

    Returns:
        List of area IDs and display names
    """
    return {
        "areas": life_area_service.get_areas_list()
    }


@router.get("/{area}/history")
async def get_area_history(
    area: str,
    request: Request,
    character_id: str = Query(..., description="Character ID"),
    db: Session = Depends(get_db)
):
    """Get score history for a specific area.

    Note: Currently only returns latest score. Future enhancement for tracking over time.

    Args:
        area: Life area name
        character_id: Character ID

    Returns:
        Score history
    """
    try:
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Validate area
        if area not in LIFE_AREAS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid area: {area}. Valid areas: {LIFE_AREAS}"
            )

        history = life_area_service.get_area_history(
            user_id=current_user.id,
            character_id=character_id,
            area=area,
            db=db
        )

        return {
            "area": area,
            "history": history
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting history for {area}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get history")

"""
Feature Preferences API routes.

Endpoints for managing which sidebar features are visible per persona.
"""

import logging
from typing import Optional, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from miachat.database.config import get_db
from ..core.clerk_auth import get_current_user_from_session
from ..core.feature_preferences_service import feature_preferences_service
from ..core.character_manager import character_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feature-preferences", tags=["feature-preferences"])


# ==================== PYDANTIC MODELS ====================

class FeatureUpdate(BaseModel):
    """Update a single feature preference."""
    feature: str  # 'goals', 'habits', 'todos', 'life_areas'
    enabled: Optional[bool] = None  # True/False to override, None to use default


class FeaturesUpdate(BaseModel):
    """Update multiple feature preferences at once."""
    goals: Optional[bool] = None
    habits: Optional[bool] = None
    todos: Optional[bool] = None
    life_areas: Optional[bool] = None


# ==================== ENDPOINTS ====================

@router.get("/{character_id}")
async def get_feature_preferences(
    character_id: str,
    user=Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """
    Get effective feature preferences for a character.

    Returns the combined result of:
    1. User overrides (highest priority)
    2. Character card defaults
    3. Category defaults (lowest priority)
    """
    # Get character data
    character = character_manager.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Get effective features
    effective = feature_preferences_service.get_effective_features(
        user_id=user.id,
        character_id=character_id,
        character_data=character,
        db=db
    )

    # Also return raw user overrides and defaults for UI
    user_overrides = feature_preferences_service.get_user_overrides(
        user_id=user.id,
        character_id=character_id,
        db=db
    )

    category = character.get('category', 'Assistant')
    category_defaults = feature_preferences_service.get_category_defaults(category)
    char_features = character.get('features', {})

    return {
        'effective': effective,
        'user_overrides': user_overrides,
        'character_defaults': char_features if char_features else None,
        'category_defaults': category_defaults,
        'category': category
    }


@router.put("/{character_id}")
async def update_feature_preferences(
    character_id: str,
    data: FeaturesUpdate,
    user=Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """
    Update feature preferences for a character.

    Set a feature to True/False to override the default,
    or None to use the default from character card or category.
    """
    # Verify character exists
    character = character_manager.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Build features dict from non-None values
    features = {}
    if data.goals is not None:
        features['goals'] = data.goals
    if data.habits is not None:
        features['habits'] = data.habits
    if data.todos is not None:
        features['todos'] = data.todos
    if data.life_areas is not None:
        features['life_areas'] = data.life_areas

    # Update overrides
    prefs = feature_preferences_service.set_all_overrides(
        user_id=user.id,
        character_id=character_id,
        features=features,
        db=db
    )

    # Return updated effective features
    effective = feature_preferences_service.get_effective_features(
        user_id=user.id,
        character_id=character_id,
        character_data=character,
        db=db
    )

    return {
        'effective': effective,
        'user_overrides': prefs
    }


@router.put("/{character_id}/{feature}")
async def update_single_feature(
    character_id: str,
    feature: str,
    data: FeatureUpdate,
    user=Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """
    Update a single feature preference.

    Feature must be one of: goals, habits, todos, life_areas
    """
    if feature not in ['goals', 'habits', 'todos', 'life_areas']:
        raise HTTPException(status_code=400, detail=f"Invalid feature: {feature}")

    # Verify character exists
    character = character_manager.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    try:
        prefs = feature_preferences_service.set_user_override(
            user_id=user.id,
            character_id=character_id,
            feature=feature,
            enabled=data.enabled,
            db=db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Return updated effective features
    effective = feature_preferences_service.get_effective_features(
        user_id=user.id,
        character_id=character_id,
        character_data=character,
        db=db
    )

    return {
        'effective': effective,
        'user_overrides': prefs
    }


@router.delete("/{character_id}")
async def reset_to_defaults(
    character_id: str,
    user=Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """
    Reset all feature preferences to defaults.

    Removes all user overrides, reverting to character card or category defaults.
    """
    # Verify character exists
    character = character_manager.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    deleted = feature_preferences_service.reset_to_defaults(
        user_id=user.id,
        character_id=character_id,
        db=db
    )

    # Return effective features (now using defaults)
    effective = feature_preferences_service.get_effective_features(
        user_id=user.id,
        character_id=character_id,
        character_data=character,
        db=db
    )

    return {
        'reset': deleted,
        'effective': effective
    }

"""
Feature Preferences Service.

Manages which sidebar features (goals, habits, todos, life areas) are visible
for each persona. Uses a three-tier priority system:

1. User override (highest priority) - stored in database
2. Character card defaults - 'features' field in JSON
3. Category defaults - based on persona category
"""

import logging
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from miachat.database.models import PersonaFeaturePreferences

logger = logging.getLogger(__name__)


# Category-based defaults (lowest priority)
CATEGORY_DEFAULTS = {
    'Coach': {
        'goals': True,
        'habits': True,
        'todos': True,
        'life_areas': True
    },
    'Assistant': {
        'goals': True,
        'habits': False,
        'todos': True,
        'life_areas': False
    },
    'Friend': {
        'goals': False,
        'habits': False,
        'todos': False,
        'life_areas': False
    },
    'Companion': {
        'goals': False,
        'habits': False,
        'todos': False,
        'life_areas': False
    },
    'Roleplay': {
        'goals': False,
        'habits': False,
        'todos': False,
        'life_areas': False
    },
    'Creative': {
        'goals': False,
        'habits': False,
        'todos': False,
        'life_areas': False
    }
}

# Fallback if category not found
DEFAULT_FEATURES = {
    'goals': True,
    'habits': True,
    'todos': True,
    'life_areas': False
}


class FeaturePreferencesService:
    """Service for managing persona feature visibility preferences."""

    def get_category_defaults(self, category: str) -> Dict[str, bool]:
        """Get default features for a category."""
        return CATEGORY_DEFAULTS.get(category, DEFAULT_FEATURES).copy()

    def get_user_overrides(
        self,
        user_id: int,
        character_id: str,
        db: Session
    ) -> Optional[Dict[str, Optional[bool]]]:
        """Get user's feature overrides for a persona."""
        prefs = db.query(PersonaFeaturePreferences).filter(
            PersonaFeaturePreferences.user_id == user_id,
            PersonaFeaturePreferences.character_id == character_id
        ).first()

        if not prefs:
            return None

        return {
            'goals': bool(prefs.show_goals) if prefs.show_goals is not None else None,
            'habits': bool(prefs.show_habits) if prefs.show_habits is not None else None,
            'todos': bool(prefs.show_todos) if prefs.show_todos is not None else None,
            'life_areas': bool(prefs.show_life_areas) if prefs.show_life_areas is not None else None
        }

    def get_effective_features(
        self,
        user_id: int,
        character_id: str,
        character_data: Dict[str, Any],
        db: Session
    ) -> Dict[str, bool]:
        """
        Get effective feature visibility using priority hierarchy.

        Priority (highest to lowest):
        1. User overrides from database
        2. Character card 'features' field
        3. Category defaults based on persona category
        """
        # Start with category defaults
        category = character_data.get('category', 'Assistant')
        effective = self.get_category_defaults(category)

        # Apply character card defaults if present
        char_features = character_data.get('features', {})
        if char_features:
            for key in ['goals', 'habits', 'todos', 'life_areas']:
                if key in char_features and char_features[key] is not None:
                    effective[key] = bool(char_features[key])

        # Apply user overrides (highest priority)
        user_overrides = self.get_user_overrides(user_id, character_id, db)
        if user_overrides:
            for key in ['goals', 'habits', 'todos', 'life_areas']:
                if user_overrides.get(key) is not None:
                    effective[key] = user_overrides[key]

        return effective

    def set_user_override(
        self,
        user_id: int,
        character_id: str,
        feature: str,
        enabled: Optional[bool],
        db: Session
    ) -> Dict[str, Any]:
        """
        Set a user override for a specific feature.

        Args:
            user_id: User ID
            character_id: Character/persona ID
            feature: Feature name ('goals', 'habits', 'todos', 'life_areas')
            enabled: True/False to override, None to use default
            db: Database session

        Returns:
            Updated preferences dict
        """
        if feature not in ['goals', 'habits', 'todos', 'life_areas']:
            raise ValueError(f"Invalid feature: {feature}")

        # Get or create preferences record
        prefs = db.query(PersonaFeaturePreferences).filter(
            PersonaFeaturePreferences.user_id == user_id,
            PersonaFeaturePreferences.character_id == character_id
        ).first()

        if not prefs:
            prefs = PersonaFeaturePreferences(
                user_id=user_id,
                character_id=character_id
            )
            db.add(prefs)

        # Map feature name to column
        column_map = {
            'goals': 'show_goals',
            'habits': 'show_habits',
            'todos': 'show_todos',
            'life_areas': 'show_life_areas'
        }

        # Set value (convert bool to int for SQLite, None stays None)
        value = None if enabled is None else (1 if enabled else 0)
        setattr(prefs, column_map[feature], value)

        db.commit()
        db.refresh(prefs)

        return prefs.to_dict()

    def set_all_overrides(
        self,
        user_id: int,
        character_id: str,
        features: Dict[str, Optional[bool]],
        db: Session
    ) -> Dict[str, Any]:
        """
        Set multiple user overrides at once.

        Args:
            user_id: User ID
            character_id: Character/persona ID
            features: Dict of feature names to enabled values
            db: Database session

        Returns:
            Updated preferences dict
        """
        # Get or create preferences record
        prefs = db.query(PersonaFeaturePreferences).filter(
            PersonaFeaturePreferences.user_id == user_id,
            PersonaFeaturePreferences.character_id == character_id
        ).first()

        if not prefs:
            prefs = PersonaFeaturePreferences(
                user_id=user_id,
                character_id=character_id
            )
            db.add(prefs)

        # Map feature names to columns and set values
        column_map = {
            'goals': 'show_goals',
            'habits': 'show_habits',
            'todos': 'show_todos',
            'life_areas': 'show_life_areas'
        }

        for feature, enabled in features.items():
            if feature in column_map:
                value = None if enabled is None else (1 if enabled else 0)
                setattr(prefs, column_map[feature], value)

        db.commit()
        db.refresh(prefs)

        return prefs.to_dict()

    def reset_to_defaults(
        self,
        user_id: int,
        character_id: str,
        db: Session
    ) -> bool:
        """
        Reset all user overrides to use defaults.

        Args:
            user_id: User ID
            character_id: Character/persona ID
            db: Database session

        Returns:
            True if preferences were deleted, False if none existed
        """
        prefs = db.query(PersonaFeaturePreferences).filter(
            PersonaFeaturePreferences.user_id == user_id,
            PersonaFeaturePreferences.character_id == character_id
        ).first()

        if prefs:
            db.delete(prefs)
            db.commit()
            return True

        return False


# Singleton instance
feature_preferences_service = FeaturePreferencesService()

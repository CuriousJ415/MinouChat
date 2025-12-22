"""
Life Area Service for managing Coach life area scorecards.

Tracks user satisfaction scores (1-10) across life domains.
Displayed in the sidebar for Coach-category personas.
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ...database.models import LifeAreaScore, LIFE_AREAS

logger = logging.getLogger(__name__)


class LifeAreaService:
    """Service for managing life area scorecards."""

    def get_scorecard(
        self,
        user_id: int,
        character_id: str,
        db: Session = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get full scorecard with all areas.

        Missing areas are initialized with default score of 5.

        Args:
            user_id: User ID
            character_id: Character ID
            db: Database session

        Returns:
            Dictionary mapping area names to score data
        """
        # Get existing scores
        scores = db.query(LifeAreaScore).filter(
            and_(
                LifeAreaScore.user_id == user_id,
                LifeAreaScore.character_id == character_id
            )
        ).all()

        # Build scorecard with all areas
        scorecard = {}
        existing_areas = {s.area: s for s in scores}

        for area in LIFE_AREAS:
            if area in existing_areas:
                scorecard[area] = existing_areas[area].to_dict()
            else:
                # Default score for unrated areas
                scorecard[area] = {
                    'id': None,
                    'area': area,
                    'score': 5,  # Default middle value
                    'notes': None,
                    'source_type': None,
                    'created_at': None,
                    'updated_at': None
                }

        return scorecard

    def update_score(
        self,
        user_id: int,
        character_id: str,
        area: str,
        score: int,
        notes: Optional[str] = None,
        source_type: str = 'manual',
        source_message_id: Optional[int] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Update or create a life area score (upsert).

        Args:
            user_id: User ID
            character_id: Character ID
            area: Life area name
            score: Score (1-10)
            notes: Optional notes
            source_type: 'manual' or 'extracted'
            source_message_id: Message ID if extracted
            db: Database session

        Returns:
            Updated/created score dictionary

        Raises:
            ValueError: If area or score is invalid
        """
        # Validate area
        if area not in LIFE_AREAS:
            raise ValueError(f"Invalid area: {area}. Valid areas: {LIFE_AREAS}")

        # Validate score
        if not 1 <= score <= 10:
            raise ValueError(f"Score must be between 1 and 10, got: {score}")

        # Find existing or create new
        existing = db.query(LifeAreaScore).filter(
            and_(
                LifeAreaScore.user_id == user_id,
                LifeAreaScore.character_id == character_id,
                LifeAreaScore.area == area
            )
        ).first()

        if existing:
            # Update existing
            existing.score = score
            existing.notes = notes if notes else existing.notes
            existing.source_type = source_type
            existing.source_message_id = source_message_id
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            logger.info(f"Updated life area {area} to {score} for user {user_id}")
            return existing.to_dict()
        else:
            # Create new
            new_score = LifeAreaScore(
                user_id=user_id,
                character_id=character_id,
                area=area,
                score=score,
                notes=notes,
                source_type=source_type,
                source_message_id=source_message_id
            )
            db.add(new_score)
            db.commit()
            db.refresh(new_score)
            logger.info(f"Created life area {area} with score {score} for user {user_id}")
            return new_score.to_dict()

    def get_area_history(
        self,
        user_id: int,
        character_id: str,
        area: str,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """Get score history for a specific area.

        Note: Currently returns only the latest score since we're using upsert.
        Future enhancement: Use a separate history table for tracking over time.

        Args:
            user_id: User ID
            character_id: Character ID
            area: Life area name
            db: Database session

        Returns:
            List of score dictionaries (currently just one)
        """
        score = db.query(LifeAreaScore).filter(
            and_(
                LifeAreaScore.user_id == user_id,
                LifeAreaScore.character_id == character_id,
                LifeAreaScore.area == area
            )
        ).first()

        if score:
            return [score.to_dict()]
        return []

    def get_average_score(
        self,
        user_id: int,
        character_id: str,
        db: Session = None
    ) -> float:
        """Get average score across all rated areas.

        Args:
            user_id: User ID
            character_id: Character ID
            db: Database session

        Returns:
            Average score (or 5.0 if no areas rated)
        """
        scores = db.query(LifeAreaScore.score).filter(
            and_(
                LifeAreaScore.user_id == user_id,
                LifeAreaScore.character_id == character_id
            )
        ).all()

        if not scores:
            return 5.0  # Default

        total = sum(s[0] for s in scores)
        return round(total / len(scores), 1)

    def get_areas_list(self) -> List[Dict[str, str]]:
        """Get list of all available life areas with display names.

        Returns:
            List of area dictionaries with id and name
        """
        display_names = {
            'career': 'Career/Work',
            'finances': 'Finances',
            'health': 'Health',
            'relationships': 'Relationships',
            'family': 'Family',
            'friendships': 'Friendships',
            'growth': 'Personal Growth',
            'recreation': 'Fun/Recreation',
            'environment': 'Environment',
            'contribution': 'Contribution'
        }

        return [
            {'id': area, 'name': display_names.get(area, area.title())}
            for area in LIFE_AREAS
        ]


# Global service instance
life_area_service = LifeAreaService()

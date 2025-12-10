"""
User Profile Service for managing per-character user profile information.

Stores user profile data (preferred name, intro, preferences) in the character card,
allowing users to present themselves differently to different personas.
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class UserProfileService:
    """Manages user profile data stored in character cards."""

    def __init__(self, storage_dir: str = "character_cards"):
        self.storage_dir = Path(storage_dir)

    def get_user_profile(self, character_id: str) -> Dict[str, Any]:
        """
        Get user profile from character card.

        Returns profile dict with: preferred_name, brief_intro, feedback_style, topics_to_avoid
        Returns empty profile if not set.
        """
        file_path = self.storage_dir / f"{character_id}.json"

        if not file_path.exists():
            logger.warning(f"Character file not found: {character_id}")
            return self._empty_profile()

        try:
            with open(file_path, 'r') as f:
                character = json.load(f)

            # Return existing profile or empty one
            profile = character.get('user_profile', {})
            return self._normalize_profile(profile)

        except Exception as e:
            logger.error(f"Error loading user profile for {character_id}: {e}")
            return self._empty_profile()

    def update_user_profile(self, character_id: str, profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update user profile in character card.

        Args:
            character_id: The character UUID
            profile: Dict with preferred_name, brief_intro, feedback_style, topics_to_avoid

        Returns:
            Updated profile dict, or None on error
        """
        file_path = self.storage_dir / f"{character_id}.json"

        if not file_path.exists():
            logger.error(f"Character file not found: {character_id}")
            return None

        try:
            with open(file_path, 'r') as f:
                character = json.load(f)

            # Normalize and update profile
            normalized = self._normalize_profile(profile)
            character['user_profile'] = normalized

            # Update timestamp
            character['updated_at'] = datetime.now().isoformat()

            # Save back
            with open(file_path, 'w') as f:
                json.dump(character, f, indent=2)

            logger.info(f"Updated user profile for character {character_id}")
            return normalized

        except Exception as e:
            logger.error(f"Error updating user profile for {character_id}: {e}")
            return None

    def format_user_profile_context(self, character_id: str) -> str:
        """
        Format user profile as context for system prompt.

        Returns formatted context string that can be injected into
        the system prompt to provide user information. Uses natural
        language that the AI can use conversationally.

        Example output:
        "[About the user you're talking to - use naturally in conversation]
        Name: Jason (use this name to address them)
        About: Software engineer interested in AI
        Feedback style: Direct - they prefer straight-to-the-point responses
        Topics to avoid: politics"
        """
        profile = self.get_user_profile(character_id)

        # Skip if no profile defined
        if self._is_empty_profile(profile):
            return ""

        lines = ["[About the user you're talking to - use this naturally in conversation]"]

        if profile.get('preferred_name'):
            lines.append(f"Name: {profile['preferred_name']} (use this name when addressing them)")

        if profile.get('brief_intro'):
            lines.append(f"About them: {profile['brief_intro']}")

        if profile.get('feedback_style') and profile['feedback_style'] != 'balanced':
            style_desc = {
                'supportive': 'Supportive - they prefer gentle, encouraging feedback',
                'direct': 'Direct - they prefer straight-to-the-point, honest feedback'
            }
            if profile['feedback_style'] in style_desc:
                lines.append(f"Communication preference: {style_desc[profile['feedback_style']]}")

        if profile.get('topics_to_avoid'):
            lines.append(f"Topics to avoid: {profile['topics_to_avoid']}")

        # Only return if we have actual content beyond the header
        if len(lines) > 1:
            return "\n".join(lines)

        return ""

    def _empty_profile(self) -> Dict[str, Any]:
        """Return empty profile structure."""
        return {
            "preferred_name": "",
            "brief_intro": "",
            "feedback_style": "balanced",
            "topics_to_avoid": ""
        }

    def _normalize_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize profile dict to ensure all expected fields exist.

        Handles missing fields and type coercion.
        """
        if not profile:
            return self._empty_profile()

        normalized = {
            "preferred_name": str(profile.get('preferred_name', '') or '').strip(),
            "brief_intro": str(profile.get('brief_intro', '') or '').strip(),
            "feedback_style": str(profile.get('feedback_style', 'balanced') or 'balanced').strip(),
            "topics_to_avoid": str(profile.get('topics_to_avoid', '') or '').strip()
        }

        # Validate feedback_style
        if normalized['feedback_style'] not in ['supportive', 'balanced', 'direct']:
            normalized['feedback_style'] = 'balanced'

        return normalized

    def _is_empty_profile(self, profile: Dict[str, Any]) -> bool:
        """Check if profile has any actual content."""
        if not profile:
            return True

        return (
            not profile.get('preferred_name') and
            not profile.get('brief_intro') and
            not profile.get('topics_to_avoid')
        )

    def get_user_name(self, character_id: str) -> Optional[str]:
        """
        Get just the user's preferred name for quick access.

        Useful for greeting generation and personalization.
        """
        profile = self.get_user_profile(character_id)
        return profile.get('preferred_name') or None


# Global instance
user_profile_service = UserProfileService()

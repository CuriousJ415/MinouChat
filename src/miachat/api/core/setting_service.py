"""
Setting Service for managing character setting/world context.

Provides structured Setting fields (world, location, time_period, key_facts)
instead of complex keyword-triggered World Info.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class SettingService:
    """Manages character setting/world context."""

    def __init__(self, storage_dir: str = "character_cards"):
        self.storage_dir = Path(storage_dir)

    def get_setting(self, character_id: str) -> Dict[str, Any]:
        """
        Get setting from character card.

        Returns setting dict with: world, location, time_period, key_facts
        Returns empty setting if not set.
        """
        file_path = self.storage_dir / f"{character_id}.json"

        if not file_path.exists():
            logger.warning(f"Character file not found: {character_id}")
            return self._empty_setting()

        try:
            with open(file_path, 'r') as f:
                character = json.load(f)

            # Return existing setting or empty one
            setting = character.get('setting', {})
            return self._normalize_setting(setting)

        except Exception as e:
            logger.error(f"Error loading setting for {character_id}: {e}")
            return self._empty_setting()

    def update_setting(self, character_id: str, setting: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update setting in character card.

        Args:
            character_id: The character UUID
            setting: Dict with world, location, time_period, key_facts

        Returns:
            Updated setting dict, or None on error
        """
        file_path = self.storage_dir / f"{character_id}.json"

        if not file_path.exists():
            logger.error(f"Character file not found: {character_id}")
            return None

        try:
            with open(file_path, 'r') as f:
                character = json.load(f)

            # Normalize and update setting
            normalized = self._normalize_setting(setting)
            character['setting'] = normalized

            # Update timestamp
            from datetime import datetime
            character['updated_at'] = datetime.now().isoformat()

            # Save back
            with open(file_path, 'w') as f:
                json.dump(character, f, indent=2)

            logger.info(f"Updated setting for character {character_id}")
            return normalized

        except Exception as e:
            logger.error(f"Error updating setting for {character_id}: {e}")
            return None

    def format_setting_context(self, character_id: str) -> str:
        """
        Format setting as context for system prompt.

        Returns formatted context string that can be injected into
        the system prompt to provide world/setting information.
        The format encourages subtle, natural use of the information.

        Example output:
        "[Setting Context - use naturally, don't explicitly reference]
        World: Modern day Earth
        Location: San Francisco
        Time: Present day
        Key Facts:
        - The user works as a software developer
        - Magic does not exist in this world"
        """
        setting = self.get_setting(character_id)

        # Skip if no setting defined
        if self._is_empty_setting(setting):
            return ""

        lines = ["[Setting Context - integrate naturally into conversation, don't explicitly reference this information]"]

        if setting.get('world'):
            lines.append(f"World: {setting['world']}")

        if setting.get('location'):
            lines.append(f"Location: {setting['location']}")

        if setting.get('time_period'):
            lines.append(f"Time: {setting['time_period']}")

        key_facts = setting.get('key_facts', [])
        if key_facts:
            lines.append("Key Facts:")
            for fact in key_facts:
                if fact:  # Skip empty facts
                    lines.append(f"- {fact}")

        # Only return if we have actual content beyond the header
        if len(lines) > 1:
            return "\n".join(lines)

        return ""

    def _empty_setting(self) -> Dict[str, Any]:
        """Return empty setting structure."""
        return {
            "world": "",
            "location": "",
            "time_period": "",
            "key_facts": []
        }

    def _normalize_setting(self, setting: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize setting dict to ensure all expected fields exist.

        Handles missing fields and type coercion.
        """
        if not setting:
            return self._empty_setting()

        normalized = {
            "world": str(setting.get('world', '') or '').strip(),
            "location": str(setting.get('location', '') or '').strip(),
            "time_period": str(setting.get('time_period', '') or '').strip(),
            "key_facts": []
        }

        # Handle key_facts - ensure it's a list of non-empty strings
        raw_facts = setting.get('key_facts', [])
        if isinstance(raw_facts, list):
            normalized['key_facts'] = [
                str(f).strip() for f in raw_facts
                if f and str(f).strip()
            ]
        elif isinstance(raw_facts, str):
            # Handle case where facts might be passed as comma-separated string
            normalized['key_facts'] = [
                f.strip() for f in raw_facts.split(',')
                if f.strip()
            ]

        return normalized

    def _is_empty_setting(self, setting: Dict[str, Any]) -> bool:
        """Check if setting has any actual content."""
        if not setting:
            return True

        return (
            not setting.get('world') and
            not setting.get('location') and
            not setting.get('time_period') and
            not setting.get('key_facts')
        )

    def add_key_fact(self, character_id: str, fact: str) -> Optional[List[str]]:
        """
        Add a key fact to the character's setting.

        Args:
            character_id: The character UUID
            fact: The fact to add

        Returns:
            Updated list of key facts, or None on error
        """
        setting = self.get_setting(character_id)

        fact = fact.strip()
        if not fact:
            return setting.get('key_facts', [])

        # Add fact if not already present
        key_facts = setting.get('key_facts', [])
        if fact not in key_facts:
            key_facts.append(fact)

        setting['key_facts'] = key_facts

        updated = self.update_setting(character_id, setting)
        return updated.get('key_facts', []) if updated else None

    def remove_key_fact(self, character_id: str, fact_index: int) -> Optional[List[str]]:
        """
        Remove a key fact by index.

        Args:
            character_id: The character UUID
            fact_index: Index of the fact to remove

        Returns:
            Updated list of key facts, or None on error
        """
        setting = self.get_setting(character_id)
        key_facts = setting.get('key_facts', [])

        if 0 <= fact_index < len(key_facts):
            key_facts.pop(fact_index)
            setting['key_facts'] = key_facts
            updated = self.update_setting(character_id, setting)
            return updated.get('key_facts', []) if updated else None

        return key_facts


# Global instance
setting_service = SettingService()

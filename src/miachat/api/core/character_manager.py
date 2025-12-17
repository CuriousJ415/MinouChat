"""
Character Manager for MinouChat

Handles character CRUD operations with file-based JSON storage.
Characters are stored as individual JSON files with UUID-based filenames.

Security Features:
- UUID validation to prevent path traversal attacks
- Safe file path construction
- Proper error handling with specific exceptions
"""

import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from .model_discovery import model_discovery

logger = logging.getLogger(__name__)

# Environment-configurable storage directory
DEFAULT_STORAGE_DIR = os.getenv("CHARACTER_CARDS_DIR", "character_cards")

# UUID validation regex
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)


class CharacterError(Exception):
    """Base exception for character operations."""
    pass


class CharacterNotFoundError(CharacterError):
    """Raised when a character cannot be found."""
    pass


class InvalidCharacterIdError(CharacterError):
    """Raised when a character ID is invalid (not a valid UUID)."""
    pass


class CharacterManager:
    """
    Privacy-first character management system.

    Characters are stored as individual JSON files in a configurable directory.
    Each character has a UUID identifier that maps directly to the filename.

    Security:
        - All character IDs are validated as UUIDs before file operations
        - File paths are constructed safely to prevent path traversal
        - All errors are logged without exposing internal paths to users
    """

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize the CharacterManager.

        Args:
            storage_dir: Directory to store character JSON files.
                         Defaults to CHARACTER_CARDS_DIR env var or 'character_cards'.
        """
        self.storage_dir = Path(storage_dir or DEFAULT_STORAGE_DIR)
        self.storage_dir.mkdir(exist_ok=True)
        self._load_default_cards()

    def _validate_character_id(self, character_id: str) -> None:
        """
        Validate that a character ID is a valid UUID.

        Args:
            character_id: The character ID to validate

        Raises:
            InvalidCharacterIdError: If the ID is not a valid UUID
        """
        if not character_id or not UUID_PATTERN.match(character_id):
            raise InvalidCharacterIdError(
                f"Invalid character ID format. Expected UUID, got: {character_id[:50] if character_id else 'empty'}"
            )

    def _get_character_path(self, character_id: str) -> Path:
        """
        Get the safe file path for a character.

        Args:
            character_id: Validated character UUID

        Returns:
            Path object for the character's JSON file
        """
        # ID should already be validated, but double-check
        self._validate_character_id(character_id)
        return self.storage_dir / f"{character_id}.json"
    
    def _load_default_cards(self) -> None:
        """
        Initialize the examples directory structure.

        Examples are pre-created template files that users can import
        to create new characters. This method ensures the directory exists.
        """
        examples_dir = self.storage_dir.parent / "character_examples"
        examples_dir.mkdir(exist_ok=True)
        logger.info(f"Example characters directory initialized: {examples_dir}")

    def list_characters(self) -> List[Dict[str, Any]]:
        """
        List all characters in the storage directory.

        Returns:
            List of character data dictionaries.
            Characters with invalid JSON are skipped and logged.
        """
        characters = []
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    character_data = json.load(f)
                    characters.append(character_data)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in character file {file_path.name}: {e}")
            except IOError as e:
                logger.error(f"Could not read character file {file_path.name}: {e}")
        return characters

    def get_character(self, character_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a character by ID.

        Args:
            character_id: UUID of the character to retrieve

        Returns:
            Character data dictionary, or None if not found

        Raises:
            InvalidCharacterIdError: If character_id is not a valid UUID
        """
        try:
            self._validate_character_id(character_id)
            file_path = self._get_character_path(character_id)

            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        except InvalidCharacterIdError:
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for character {character_id}: {e}")
            return None
        except IOError as e:
            logger.error(f"Could not read character {character_id}: {e}")
            return None

    def create_character(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new character.

        Args:
            data: Character data dictionary. If 'id' is not provided,
                  a new UUID will be generated.

        Returns:
            Created character data with ID, or None on failure
        """
        try:
            # Set default provider if model_config exists but provider is missing
            if data.get('model_config') is not None and 'provider' not in data['model_config']:
                data['model_config']['provider'] = 'ollama'

            # Generate ID if not provided
            if 'id' not in data:
                data['id'] = str(uuid.uuid4())
            else:
                # Validate provided ID
                self._validate_character_id(data['id'])

            # Add timestamps
            now = datetime.now(timezone.utc).isoformat()
            data.setdefault('created_at', now)
            data['updated_at'] = now

            file_path = self._get_character_path(data['id'])

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Created character: {data['id']}")
            return data

        except InvalidCharacterIdError:
            raise
        except IOError as e:
            logger.error(f"Could not save character: {e}")
            return None
        except (TypeError, ValueError) as e:
            logger.error(f"Invalid character data: {e}")
            return None

    def update_character(self, character_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing character.

        Args:
            character_id: UUID of the character to update
            data: Dictionary of fields to update

        Returns:
            Updated character data, or None if character not found

        Raises:
            InvalidCharacterIdError: If character_id is not a valid UUID
        """
        try:
            self._validate_character_id(character_id)
            existing_data = self.get_character(character_id)

            if not existing_data:
                return None

            # Merge update data
            existing_data.update(data)
            existing_data['updated_at'] = datetime.now(timezone.utc).isoformat()

            file_path = self._get_character_path(character_id)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Updated character: {character_id}")
            return existing_data

        except InvalidCharacterIdError:
            raise
        except IOError as e:
            logger.error(f"Could not save character {character_id}: {e}")
            return None
        except (TypeError, ValueError) as e:
            logger.error(f"Invalid update data for character {character_id}: {e}")
            return None

    def delete_character(self, character_id: str) -> bool:
        """
        Delete a character.

        Args:
            character_id: UUID of the character to delete

        Returns:
            True if deleted, False if character did not exist

        Raises:
            InvalidCharacterIdError: If character_id is not a valid UUID
        """
        try:
            self._validate_character_id(character_id)
            file_path = self._get_character_path(character_id)

            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted character: {character_id}")
                return True

            return False

        except InvalidCharacterIdError:
            raise
        except IOError as e:
            logger.error(f"Could not delete character {character_id}: {e}")
            return False
    
    def get_available_models(
        self,
        privacy_mode: str = "local_only",
        api_keys: Optional[Dict[str, str]] = None
    ) -> Dict[str, List[str]]:
        """
        Get available LLM models using privacy-respecting discovery.

        Args:
            privacy_mode: Privacy level ('local_only', 'cloud_ok')
            api_keys: Optional API keys for cloud providers

        Returns:
            Dictionary mapping provider names to available model lists
        """
        return model_discovery.get_available_models(privacy_mode, api_keys)

    def get_example_characters(self) -> List[Dict[str, Any]]:
        """
        Get available example characters that users can import.

        Returns:
            List of example character data dictionaries
        """
        examples_dir = self.storage_dir.parent / "character_examples"
        examples = []

        if examples_dir.exists():
            for file_path in examples_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        examples.append(json.load(f))
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in example file {file_path.name}: {e}")
                except IOError as e:
                    logger.error(f"Could not read example file {file_path.name}: {e}")

        return examples

    def import_example_character(
        self,
        example_id: str,
        new_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Import an example character as a new character.

        Args:
            example_id: ID of the example character to import
            new_name: Optional new name for the imported character

        Returns:
            Created character data, or None if example not found

        Raises:
            InvalidCharacterIdError: If example_id is not a valid UUID
        """
        try:
            self._validate_character_id(example_id)
            examples_dir = self.storage_dir.parent / "character_examples"
            example_file = examples_dir / f"{example_id}.json"

            if not example_file.exists():
                return None

            with open(example_file, 'r', encoding='utf-8') as f:
                example = json.load(f)

            # Create a new character based on the example
            new_char = example.copy()
            new_char['id'] = str(uuid.uuid4())
            new_char['name'] = new_name or example.get('name', 'Character').replace(' (Example)', '')
            new_char['is_example'] = False
            new_char['created_at'] = datetime.now(timezone.utc).isoformat()

            return self.create_character(new_char)

        except InvalidCharacterIdError:
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in example {example_id}: {e}")
            return None
        except IOError as e:
            logger.error(f"Could not read example {example_id}: {e}")
            return None

    def get_privacy_info(self) -> Dict[str, Any]:
        """
        Get detailed privacy information about LLM providers.

        Returns:
            Dictionary with privacy details for each provider
        """
        return model_discovery.get_privacy_info()

    def get_categories(self) -> List[str]:
        """
        Get all unique categories from existing characters.

        Returns:
            Sorted list of category names
        """
        categories = set()
        for char in self.list_characters():
            if 'category' in char and char['category']:
                categories.add(char['category'])
        return sorted(categories)

    def get_tags(self) -> List[str]:
        """
        Get all unique tags from existing characters.

        Returns:
            Sorted list of tag names
        """
        tags = set()
        for char in self.list_characters():
            if 'tags' in char and char['tags']:
                tags.update(char['tags'])
        return sorted(tags)

    def get_model_recommendations(self) -> Dict[str, Any]:
        """
        Get model recommendations by use case (privacy-first).

        Returns:
            Dictionary with recommended models for different use cases
        """
        return model_discovery.get_model_recommendations()

    def get_openrouter_models(self) -> List[str]:
        """
        Get available OpenRouter models.

        Returns:
            List of OpenRouter model identifiers
        """
        models = self.get_available_models()
        return models.get('openrouter', [])


# Global character manager instance
character_manager = CharacterManager()

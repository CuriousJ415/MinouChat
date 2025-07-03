import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class CharacterManager:
    """Privacy-first character management system."""
    
    def __init__(self, storage_dir: str = "character_cards"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self._load_default_cards()
    
    def _load_default_cards(self):
        if not self.list_characters():
            self._create_default_cards()
    
    def _create_default_cards(self):
        default_cards = [
            {
                'id': str(uuid.uuid4()),
                'name': 'Mia',
                'personality': 'A warm and supportive friend',
                'system_prompt': 'You are Mia, a warm and supportive friend.',
                'model_config': {'provider': 'ollama', 'model': 'llama3:8b'},
                'role': 'friend',
                'category': 'Social',
                'tags': ['friend', 'local', 'private'],
                'created_at': datetime.now().isoformat()
            }
        ]
        for card_data in default_cards:
            self.create_character(card_data)
    
    def list_characters(self) -> List[Dict[str, Any]]:
        characters = []
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    characters.append(json.load(f))
            except Exception as e:
                logger.error(f"Error loading character: {e}")
        return characters
    
    def get_character(self, character_id: str) -> Optional[Dict[str, Any]]:
        file_path = self.storage_dir / f"{character_id}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading character {character_id}: {e}")
            return None
    
    def create_character(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            if 'model_config' in data and 'provider' not in data['model_config']:
                data['model_config']['provider'] = 'ollama'
            if 'id' not in data:
                data['id'] = str(uuid.uuid4())
            file_path = self.storage_dir / f"{data['id']}.json"
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return data
        except Exception as e:
            logger.error(f"Error creating character: {e}")
            return None
    
    def update_character(self, character_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            existing_data = self.get_character(character_id)
            if not existing_data:
                return None
            existing_data.update(data)
            existing_data['updated_at'] = datetime.now().isoformat()
            file_path = self.storage_dir / f"{character_id}.json"
            with open(file_path, 'w') as f:
                json.dump(existing_data, f, indent=2)
            return existing_data
        except Exception as e:
            logger.error(f"Error updating character {character_id}: {e}")
            return None
    
    def delete_character(self, character_id: str) -> bool:
        try:
            file_path = self.storage_dir / f"{character_id}.json"
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting character {character_id}: {e}")
            return False
    
    def get_available_models(self) -> Dict[str, List[str]]:
        return {
            'ollama': ['llama3:8b', 'llama3.1:latest', 'mistral:latest'],
            'openai': ['gpt-4', 'gpt-3.5-turbo'],
            'anthropic': ['claude-3-sonnet', 'claude-3-haiku'],
            'openrouter': ['openai/gpt-4', 'anthropic/claude-3-sonnet']
        }
    
    def get_privacy_info(self) -> Dict[str, Any]:
        return {
            'ollama': {'privacy': 'FULLY_PRIVATE', 'description': 'Local processing, no data leaves your device'},
            'openai': {'privacy': 'CLOUD_PROCESSING', 'description': 'Data sent to OpenAI servers'},
            'anthropic': {'privacy': 'CLOUD_PROCESSING', 'description': 'Data sent to Anthropic servers'},
            'openrouter': {'privacy': 'CLOUD_PROCESSING', 'description': 'Data sent to OpenRouter'}
        }
    
    def get_categories(self) -> List[str]:
        categories = set()
        for char in self.list_characters():
            if 'category' in char:
                categories.add(char['category'])
        return sorted(list(categories))
    
    def get_tags(self) -> List[str]:
        tags = set()
        for char in self.list_characters():
            if 'tags' in char:
                tags.update(char['tags'])
        return sorted(list(tags))

character_manager = CharacterManager()

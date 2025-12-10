import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from .model_discovery import model_discovery

logger = logging.getLogger(__name__)

class CharacterManager:
    """Privacy-first character management system."""
    
    def __init__(self, storage_dir: str = "character_cards"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self._load_default_cards()
    
    def _load_default_cards(self):
        # Ensure examples directory exists - examples are now pre-created templates
        examples_dir = self.storage_dir.parent / "character_examples"
        examples_dir.mkdir(exist_ok=True)
        logger.info(f"Example characters directory: {examples_dir}")
        
        # Examples are now managed as static templates, not auto-generated
    
    def _create_default_cards(self):
        """Legacy method - now defaults are handled as examples"""
        pass
    
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
            if 'model_config' in data and data['model_config'] is not None and 'provider' not in data['model_config']:
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
    
    def get_available_models(self, privacy_mode: str = "local_only", api_keys: Dict[str, str] = None) -> Dict[str, List[str]]:
        """Get available models using privacy-respecting discovery."""
        return model_discovery.get_available_models(privacy_mode, api_keys)
    
    
    def _create_example_characters(self, examples_dir: Path):
        """Legacy method - examples are now static templates."""
        # Examples are now pre-created template files, not dynamically generated
        pass
    
    def get_example_characters(self) -> List[Dict]:
        """Get available example characters that users can import."""
        examples_dir = self.storage_dir.parent / "character_examples"
        examples = []
        
        if examples_dir.exists():
            for file_path in examples_dir.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        examples.append(json.load(f))
                except Exception as e:
                    logger.error(f"Error loading example: {e}")
        
        return examples
    
    def import_example_character(self, example_id: str, new_name: str = None) -> Dict:
        """Import an example character as a new character."""
        examples_dir = self.storage_dir.parent / "character_examples"
        example_file = examples_dir / f"{example_id}.json"
        
        if not example_file.exists():
            return None
        
        try:
            with open(example_file, 'r') as f:
                example = json.load(f)
            
            # Create a new character based on the example
            new_char = example.copy()
            new_char['id'] = str(uuid.uuid4())
            new_char['name'] = new_name or example['name'].replace(' (Example)', '')
            new_char['is_example'] = False
            new_char['created_at'] = datetime.now().isoformat()
            
            return self.create_character(new_char)
        except Exception as e:
            logger.error(f"Error importing example character: {e}")
            return None
    
    def get_privacy_info(self) -> Dict[str, Any]:
        """Get detailed privacy information."""
        return model_discovery.get_privacy_info()
    
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
    
    def get_model_recommendations(self) -> Dict[str, Any]:
        """Get model recommendations by use case - PRIVACY-FIRST."""
        return model_discovery.get_model_recommendations()
    
    def get_openrouter_models(self) -> List[str]:
        """Get OpenRouter models (for API compatibility)."""
        return self.get_available_models()['openrouter']

character_manager = CharacterManager()

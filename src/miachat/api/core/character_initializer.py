#!/usr/bin/env python3
"""
Character Initialization Service

Handles proper character initialization without hard-coded model assumptions.
Creates characters from templates that require setup.
"""

import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from .character_manager import character_manager

logger = logging.getLogger(__name__)

class CharacterInitializer:
    """Initializes default characters without model assumptions"""
    
    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent / "data" / "default_personas"
        
    def check_needs_initialization(self) -> bool:
        """Check if system needs character initialization"""
        existing_characters = character_manager.list_characters()
        
        # Check if we have any characters at all
        if not existing_characters:
            return True
            
        # Check if any characters need setup
        needs_setup = any(
            char.get('setup_required', False) or 
            char.get('model_config') is None 
            for char in existing_characters
        )
        
        return needs_setup
    
    def initialize_default_characters(self) -> List[Dict[str, Any]]:
        """Initialize default characters from templates (without models)"""
        logger.info("Initializing default characters from templates...")
        
        created_characters = []
        
        # Load all template files
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return created_characters
            
        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r') as f:
                    template = json.load(f)
                
                # Generate unique ID for this character
                character_id = str(uuid.uuid4())
                
                # Create character from template
                character_data = {
                    **template,
                    "id": character_id,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "model_config": None,  # No model assigned yet
                    "setup_required": True,  # Requires setup
                    "template": False,  # No longer a template
                    "conversation_count": 0,
                    "total_messages": 0
                }
                
                # Check if character with this name already exists
                existing = self._find_character_by_name(template["name"])
                if existing:
                    logger.info(f"Character {template['name']} already exists, skipping...")
                    continue
                
                # Create the character
                created_char = character_manager.create_character(character_data)
                if created_char:
                    created_characters.append(created_char)
                    logger.info(f"Created character: {template['name']} (needs setup)")
                else:
                    logger.error(f"Failed to create character: {template['name']}")
                    
            except Exception as e:
                logger.error(f"Error loading template {template_file}: {e}")
                continue
        
        logger.info(f"Initialized {len(created_characters)} default characters")
        return created_characters
    
    def _find_character_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find character by name"""
        characters = character_manager.list_characters()
        return next((char for char in characters if char.get('name') == name), None)
    
    def get_unonfigured_characters(self) -> List[Dict[str, Any]]:
        """Get list of characters that need model configuration"""
        characters = character_manager.list_characters()
        return [
            char for char in characters 
            if char.get('setup_required', False) or char.get('model_config') is None
        ]
    
    def mark_character_configured(self, character_id: str, model_config: Dict[str, Any]) -> bool:
        """Mark a character as configured with a model"""
        try:
            update_data = {
                "model_config": model_config,
                "setup_required": False,
                "updated_at": datetime.now().isoformat()
            }
            
            updated_char = character_manager.update_character(character_id, update_data)
            if updated_char:
                logger.info(f"Configured character {character_id} with {model_config['provider']}:{model_config['model']}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error configuring character {character_id}: {e}")
            return False
    
    def reset_character_models(self) -> int:
        """Reset all character models (for testing/development)"""
        characters = character_manager.list_characters()
        reset_count = 0
        
        for char in characters:
            if char.get('model_config'):
                update_data = {
                    "model_config": None,
                    "setup_required": True,
                    "updated_at": datetime.now().isoformat()
                }
                
                if character_manager.update_character(char['id'], update_data):
                    reset_count += 1
                    logger.info(f"Reset model config for {char['name']}")
        
        logger.info(f"Reset {reset_count} character model configurations")
        return reset_count
    
    def ensure_characters_exist(self) -> bool:
        """Ensure default characters exist (called on startup)"""
        try:
            existing_characters = character_manager.list_characters()
            
            # If no characters exist, create defaults
            if not existing_characters:
                logger.info("No characters found, creating defaults...")
                created = self.initialize_default_characters()
                return len(created) > 0
            
            # Check if we have the expected default characters
            character_names = {char['name'] for char in existing_characters}
            expected_names = {'Sage', 'Mia'}
            
            missing_names = expected_names - character_names
            if missing_names:
                logger.info(f"Missing default characters: {missing_names}")
                # Could create missing ones here if needed
            
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring characters exist: {e}")
            return False

# Global instance
character_initializer = CharacterInitializer()
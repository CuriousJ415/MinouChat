"""
Character Models and Management
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from flask import current_app

@dataclass
class Character:
    """Character model with personality and memory"""
    id: str  # Unique identifier (derived from name)
    name: str  # Display name
    role: str  # Role of the character (life coach, friend, etc.)
    personality: str  # Personality description
    system_prompt: str  # System prompt to define character behavior
    model: str = "mistral"  # Default LLM model
    llm_provider: str = "ollama"  # LLM provider (ollama, openai, anthropic)
    gender: str = ""  # Optional gender
    backstory: str = ""  # Optional backstory
    created_at: str = None  # Creation timestamp
    last_used: str = None  # Last interaction timestamp
    
    def __post_init__(self):
        """Initialize timestamp fields"""
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.last_used is None:
            self.last_used = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Convert character to dictionary"""
        return asdict(self)

# Default character definitions
DEFAULT_CHARACTERS = [
    {
        "id": "mia",
        "name": "Mia",
        "role": "assistant",
        "personality": "Helpful, friendly, and knowledgeable",
        "system_prompt": (
            "You are Mia, a helpful AI assistant. You provide informative and accurate "
            "responses to questions. When you don't know something, you're honest about it. "
            "Your tone is friendly and conversational."
        ),
        "model": "mistral",
        "llm_provider": "ollama",
        "gender": "female",
        "backstory": "Mia was created to help people find information and solve problems efficiently."
    },
    {
        "id": "anna",
        "name": "Anna",
        "role": "life_coach",
        "personality": "Empathetic, insightful, and encouraging",
        "system_prompt": (
            "You are Anna, a compassionate life coach. You listen carefully and ask "
            "thoughtful questions to help people reflect on their life choices. "
            "You provide guidance without being judgmental, always encouraging "
            "self-discovery and personal growth. You help set meaningful goals "
            "and track progress over time."
        ),
        "model": "mistral",
        "llm_provider": "ollama",
        "gender": "female",
        "backstory": "Anna has dedicated her career to helping people discover their potential and live more fulfilling lives."
    },
    {
        "id": "gordon",
        "name": "Gordon",
        "role": "business_coach",
        "personality": "Direct, analytical, and results-oriented",
        "system_prompt": (
            "You are Gordon, a business coach with decades of experience. You give "
            "practical, actionable advice to entrepreneurs and business managers. "
            "You're straightforward and focus on measurable outcomes. You value "
            "efficiency and direct communication."
        ),
        "model": "mistral",
        "llm_provider": "ollama",
        "gender": "male",
        "backstory": "Gordon built several successful companies before becoming a business coach to help others achieve similar success."
    }
]

def get_characters() -> List[Dict]:
    """
    Get all available characters
    
    Returns:
        List of character dictionaries
    """
    from app.memory.sql import get_all_characters
    
    characters = get_all_characters()
    
    # If no characters exist, create default ones
    if not characters:
        _create_default_characters()
        characters = get_all_characters()
        
    return characters

def get_character(character_id: str) -> Optional[Dict]:
    """
    Get a specific character by ID
    
    Args:
        character_id: The character's unique identifier
        
    Returns:
        Character dictionary or None if not found
    """
    from app.memory.sql import get_character_by_id
    
    return get_character_by_id(character_id)

def create_character(data: Dict) -> Dict:
    """
    Create a new character
    
    Args:
        data: Character data dictionary
        
    Returns:
        The created character dictionary
        
    Raises:
        ValueError: If invalid data or character already exists
    """
    from app.memory.sql import add_character
    
    # Generate ID from name
    if 'id' not in data:
        data['id'] = data['name'].lower().replace(' ', '_')
    
    # Normalize character data
    char_data = {
        'id': data['id'],
        'name': data['name'],
        'role': data['role'],
        'personality': data['personality'],
        'system_prompt': data.get('system_prompt', f"You are {data['name']}, a {data['role']}. {data['personality']}"),
        'model': data.get('model', current_app.config['LLM_MODEL']),
        'llm_provider': data.get('llm_provider', current_app.config['LLM_PROVIDER']),
        'gender': data.get('gender', ''),
        'backstory': data.get('backstory', ''),
        'created_at': datetime.now().isoformat(),
        'last_used': datetime.now().isoformat()
    }
    
    # Create character object
    character = Character(**char_data)
    
    # Save to database
    return add_character(character.to_dict())

def update_character(character_id: str, data: Dict) -> Optional[Dict]:
    """
    Update an existing character
    
    Args:
        character_id: The character's unique identifier
        data: Updated character data
        
    Returns:
        Updated character dictionary or None if not found
        
    Raises:
        ValueError: If invalid data
    """
    from app.memory.sql import update_character_by_id
    
    # First check if character exists
    existing = get_character(character_id)
    if not existing:
        return None
    
    # Update only provided fields
    updated_data = existing.copy()
    for field in ['name', 'role', 'personality', 'system_prompt', 'model', 'gender', 'backstory']:
        if field in data:
            updated_data[field] = data[field]
    
    # Update timestamp
    updated_data['last_used'] = datetime.now().isoformat()
    
    # Save to database
    return update_character_by_id(character_id, updated_data)

def delete_character(character_id: str) -> bool:
    """
    Delete a character
    
    Args:
        character_id: The character's unique identifier
        
    Returns:
        True if successful, False if character not found
    """
    from app.memory.sql import delete_character_by_id
    
    # Check if character is a default one
    default_ids = [char['id'] for char in DEFAULT_CHARACTERS]
    if character_id in default_ids:
        # Don't allow deleting default characters, just reset them
        return reset_character_memory(character_id)
    
    return delete_character_by_id(character_id)

def reset_character_memory(character_id: str) -> bool:
    """Reset a character's memory
    
    Args:
        character_id: ID of the character to reset
        
    Returns:
        True if successful, False otherwise
    """
    from app.memory.sql import clear_character_memory
    
    return clear_character_memory(character_id)

def _create_default_characters():
    """Create the default characters if they don't exist"""
    from app.memory.sql import add_character, get_character_by_id
    
    for char_data in DEFAULT_CHARACTERS:
        # Check if character already exists
        existing = get_character_by_id(char_data['id'])
        if existing:
            continue
            
        char_data['created_at'] = datetime.now().isoformat()
        char_data['last_used'] = datetime.now().isoformat()
        add_character(char_data)

def restore_default_characters() -> List[str]:
    """
    Restore all default characters
    
    Returns:
        List of restored character IDs
    """
    from app.memory.sql import get_character_by_id, add_character, update_character_by_id, delete_character_by_id, get_all_characters
    
    restored = []
    
    # First, get all characters to check for duplicates
    all_characters = get_all_characters()
    
    # Process each default character
    for char_data in DEFAULT_CHARACTERS:
        # Look for existing characters with both the original ID and prefixed ID
        original_id = char_data['id']
        prefixed_id = f"default-{original_id}"
        
        # Check if a non-prefixed version exists (old format)
        original_char = next((c for c in all_characters if c['id'] == original_id), None)
        if original_char:
            # Delete the non-prefixed version to avoid duplicates
            delete_character_by_id(original_id)
        
        # Check if prefixed version exists
        existing = get_character_by_id(prefixed_id)
        
        # Prepare character data with proper ID
        character_data = char_data.copy()
        character_data['id'] = prefixed_id
        character_data['created_at'] = datetime.now().isoformat()
        character_data['last_used'] = datetime.now().isoformat()
        
        if existing:
            # Update existing character to defaults
            update_character_by_id(prefixed_id, character_data)
        else:
            # Create new character with default settings
            add_character(character_data)
        
        restored.append(prefixed_id)
    
    return restored 
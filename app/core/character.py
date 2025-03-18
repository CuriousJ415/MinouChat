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
    
    # Model parameters
    temperature: float = 0.7  # Controls randomness (0-2)
    top_p: float = 0.9  # Controls diversity (0-1)
    repeat_penalty: float = 1.1  # Penalizes repetition (1-2)
    top_k: int = 40  # Limits token selection pool (5-100)
    
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
    """Create a new character in the database"""
    try:
        # Generate ID from name if not provided
        if 'id' not in data:
            data['id'] = data['name'].lower().replace(' ', '_')
        
        # Get current LLM provider from app config
        provider = current_app.config.get('LLM_PROVIDER', 'ollama')
        
        # If no model specified, use default for provider
        if 'model' not in data:
            if provider == 'ollama':
                data['model'] = 'mistral'
            elif provider == 'openai':
                data['model'] = 'gpt-3.5-turbo'
            elif provider == 'anthropic':
                data['model'] = 'claude-2'
            else:
                data['model'] = 'mistral'  # Default fallback
        
        # Set default values
        character_data = {
            'id': data['id'],
            'name': data['name'],
            'role': data['role'],
            'personality': data['personality'],
            'system_prompt': data.get('system_prompt', f"You are {data['name']}, a {data['role']}. {data['personality']}"),
            'model': data['model'],
            'llm_provider': provider,
            'gender': data.get('gender', ''),
            'backstory': data.get('backstory', ''),
            'temperature': float(data.get('temperature', 0.7)),
            'top_p': float(data.get('top_p', 0.9)),
            'repeat_penalty': float(data.get('repeat_penalty', 1.1)),
            'top_k': int(data.get('top_k', 40)),
            'created_at': datetime.now().isoformat(),
            'last_used': datetime.now().isoformat()
        }
        
        # Add character to database
        from app.memory.sql import add_character
        return add_character(character_data)
        
    except Exception as e:
        current_app.logger.error(f"Error creating character: {str(e)}")
        raise

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
    for field in ['name', 'role', 'personality', 'system_prompt', 'model', 'llm_provider', 'gender', 'backstory', 
                 'temperature', 'top_p', 'repeat_penalty', 'top_k']:
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
    
    # Check if character is a default one (either by original ID or prefixed ID)
    default_ids = [char['id'] for char in DEFAULT_CHARACTERS]
    prefixed_default_ids = [f"default-{id}" for id in default_ids]
    
    # Don't allow deleting default characters
    if character_id.startswith('default-') or character_id in default_ids:
        # Just reset their memory instead
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
        # Create prefixed ID for default characters
        original_id = char_data['id']
        prefixed_id = f"default-{original_id}"
        
        # Check if prefixed character already exists
        existing = get_character_by_id(prefixed_id)
        if existing:
            continue
        
        # Create a copy of character data with prefixed ID
        character_data = char_data.copy()
        character_data['id'] = prefixed_id
        character_data['created_at'] = datetime.now().isoformat()
        character_data['last_used'] = datetime.now().isoformat()
        
        # Add character to database
        add_character(character_data)

def restore_default_characters() -> List[str]:
    """
    Restore all default characters to their original state
    
    Returns:
        List of restored character IDs
    """
    from app.memory.sql import get_db, add_character
    
    restored = []
    db = get_db()
    cursor = db.cursor()
    
    try:
        # First, remove any existing default characters
        cursor.execute("DELETE FROM characters WHERE id LIKE 'default-%'")
        db.commit()
        
        # Create each default character with proper prefix
        for char_data in DEFAULT_CHARACTERS:
            prefixed_id = f"default-{char_data['id']}"
            
            # Create a copy of character data with prefixed ID and default values
            character_data = {
                'id': prefixed_id,
                'name': char_data['name'],
                'role': char_data['role'],
                'personality': char_data['personality'],
                'system_prompt': char_data['system_prompt'],
                'model': char_data.get('model', 'mistral'),
                'llm_provider': char_data.get('llm_provider', 'ollama'),
                'gender': char_data.get('gender', ''),
                'backstory': char_data.get('backstory', ''),
                'temperature': 0.7,
                'top_p': 0.9,
                'repeat_penalty': 1.1,
                'top_k': 40,
                'created_at': datetime.now().isoformat(),
                'last_used': datetime.now().isoformat()
            }
            
            # Add character to database
            add_character(character_data)
            restored.append(prefixed_id)
        
        return restored
        
    except Exception as e:
        current_app.logger.error(f"Error restoring default characters: {str(e)}")
        db.rollback()
        raise 
import os
import json
from typing import List, Dict, Optional, Any
from pathlib import Path
from .xml_parser import PersonaConfig, config_to_xml, parse_xml_config

class PersonaManager:
    """Manages persona configurations using file-based storage."""
    
    def __init__(self, storage_dir: str = "personas"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.active_persona = None
        self._load_default_personas()
    
    def _load_default_personas(self):
        """Load default personas if none exist."""
        if not self.list_personas():
            self._create_default_personas()
    
    def _create_default_personas(self):
        """Create default persona configurations."""
        default_personas = {
            "Gordon": {
                "name": "Gordon",
                "description": "A business coach who helps entrepreneurs grow their companies",
                "category": "Business",
                "tags": ["coaching", "business", "entrepreneur"],
                "traits": {
                    "openness": 0.7,
                    "conscientiousness": 0.9,
                    "extraversion": 0.6,
                    "agreeableness": 0.8,
                    "neuroticism": 0.3
                },
                "communication_style": {
                    "formality": 0.8,
                    "directness": 0.9,
                    "empathy": 0.7,
                    "humor": 0.4
                },
                "system_prompt": "You are Gordon, a seasoned business coach with 20+ years of experience helping entrepreneurs scale their companies. You provide practical, actionable advice and ask probing questions to help clients think through their challenges."
            },
            "Sage": {
                "name": "Sage",
                "description": "A wise life coach who guides people toward personal growth",
                "category": "Life Coaching",
                "tags": ["coaching", "life", "wisdom"],
                "traits": {
                    "openness": 0.9,
                    "conscientiousness": 0.7,
                    "extraversion": 0.5,
                    "agreeableness": 0.9,
                    "neuroticism": 0.2
                },
                "communication_style": {
                    "formality": 0.6,
                    "directness": 0.7,
                    "empathy": 0.9,
                    "humor": 0.5
                },
                "system_prompt": "You are Sage, a compassionate life coach who helps people discover their true potential. You ask thoughtful questions and provide gentle guidance to help clients find their own answers."
            },
            "Mia": {
                "name": "Mia",
                "description": "A friendly and supportive friend who's always there to chat",
                "category": "Friend",
                "tags": ["friend", "supportive", "casual"],
                "traits": {
                    "openness": 0.8,
                    "conscientiousness": 0.6,
                    "extraversion": 0.8,
                    "agreeableness": 0.9,
                    "neuroticism": 0.4
                },
                "communication_style": {
                    "formality": 0.3,
                    "directness": 0.6,
                    "empathy": 0.8,
                    "humor": 0.7
                },
                "system_prompt": "You are Mia, a warm and supportive friend who loves to chat about anything and everything. You're encouraging, understanding, and always ready to listen or offer advice when asked."
            }
        }
        
        for name, config in default_personas.items():
            self.save_persona(name, config)
        
        # Set Mia as the default active persona
        self.set_active_persona("Mia")
    
    def list_personas(self) -> List[str]:
        """List all available persona names."""
        return [f.stem for f in self.storage_dir.glob("*.json")]
    
    def get_persona(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a persona configuration by name."""
        file_path = self.storage_dir / f"{name}.json"
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def save_persona(self, name: str, config: Dict[str, Any]) -> bool:
        """Save a persona configuration."""
        try:
            file_path = self.storage_dir / f"{name}.json"
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception:
            return False
    
    def delete_persona(self, name: str) -> bool:
        """Delete a persona configuration."""
        try:
            file_path = self.storage_dir / f"{name}.json"
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def set_active_persona(self, name: str) -> bool:
        """Set the active persona."""
        if self.get_persona(name):
            self.active_persona = name
            return True
        return False
    
    def get_active_persona(self) -> Optional[Dict[str, Any]]:
        """Get the currently active persona."""
        if self.active_persona:
            return self.get_persona(self.active_persona)
        return None
    
    def get_categories(self) -> List[str]:
        """Get all available categories."""
        categories = set()
        for name in self.list_personas():
            persona = self.get_persona(name)
            if persona and 'category' in persona:
                categories.add(persona['category'])
        return sorted(list(categories))
    
    def get_tags(self) -> List[str]:
        """Get all available tags."""
        tags = set()
        for name in self.list_personas():
            persona = self.get_persona(name)
            if persona and 'tags' in persona:
                tags.update(persona['tags'])
        return sorted(list(tags))
    
    def search_personas(self, query: str = None, category: str = None, tags: List[str] = None) -> List[Dict[str, Any]]:
        """Search personas by query, category, or tags."""
        results = []
        
        for name in self.list_personas():
            persona = self.get_persona(name)
            if not persona:
                continue
            
            # Filter by query
            if query:
                query_lower = query.lower()
                if not (query_lower in persona.get('name', '').lower() or 
                       query_lower in persona.get('description', '').lower()):
                    continue
            
            # Filter by category
            if category and persona.get('category') != category:
                continue
            
            # Filter by tags
            if tags:
                persona_tags = set(persona.get('tags', []))
                if not any(tag in persona_tags for tag in tags):
                    continue
            
            results.append(persona)
        
        return results 
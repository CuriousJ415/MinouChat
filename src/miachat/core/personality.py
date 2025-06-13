"""
Personality management for MiaChat.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..personality.serializer import PersonalitySerializer
from ..personality.base import Trait, Style, Knowledge, Backstory

class Personality:
    """Manages AI personality traits and characteristics."""
    
    def __init__(
        self,
        name: str,
        traits: Dict[str, Trait],
        style: Style,
        knowledge: Knowledge,
        backstory: Backstory
    ):
        self.name = name
        self.traits = traits
        self.style = style
        self.knowledge = knowledge
        self.backstory = backstory
    
    @classmethod
    def from_xml(cls, xml_path: Union[str, Path]) -> "Personality":
        """Create a Personality instance from an XML file."""
        from ..personality.serializer import PersonalitySerializer
        return PersonalitySerializer.load_from_file(xml_path, format="xml")
    
    @classmethod
    def from_json(cls, json_path: Union[str, Path]) -> "Personality":
        """Create a Personality instance from a JSON file."""
        from ..personality.serializer import PersonalitySerializer
        return PersonalitySerializer.load_from_file(json_path, format="json")
    
    def to_xml(self) -> str:
        """Convert the personality to XML format."""
        from ..personality.serializer import PersonalitySerializer
        return PersonalitySerializer.to_xml(self)
    
    def to_json(self) -> str:
        """Convert the personality to JSON format."""
        from ..personality.serializer import PersonalitySerializer
        return PersonalitySerializer.to_json(self)
    
    def save_to_file(self, file_path: Union[str, Path], format: str = "xml") -> None:
        """Save the personality definition to a file."""
        from ..personality.serializer import PersonalitySerializer
        PersonalitySerializer.save_to_file(self, file_path, format)

class PersonalityManager:
    """Minimal stub for PersonalityManager."""
    def __init__(self):
        pass

    def get_personality(self, personality_id):
        # Stub method for compatibility
        return None 
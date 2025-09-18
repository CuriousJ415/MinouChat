"""
Persona management for MiaChat.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..persona.serializer import PersonaSerializer
from ..persona.base import Trait, Style, Knowledge, Backstory

class Persona:
    """Manages AI persona traits and characteristics."""
    
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
    def from_xml(cls, xml_path: Union[str, Path]) -> "Persona":
        """Create a Persona instance from an XML file."""
        from ..persona.serializer import PersonaSerializer
        return PersonaSerializer.load_from_file(xml_path, format="xml")
    
    @classmethod
    def from_json(cls, json_path: Union[str, Path]) -> "Persona":
        """Create a Persona instance from a JSON file."""
        from ..persona.serializer import PersonaSerializer
        return PersonaSerializer.load_from_file(json_path, format="json")
    
    def to_xml(self) -> str:
        """Convert the persona to XML format."""
        from ..persona.serializer import PersonaSerializer
        return PersonaSerializer.to_xml(self)
    
    def to_json(self) -> str:
        """Convert the persona to JSON format."""
        from ..persona.serializer import PersonaSerializer
        return PersonaSerializer.to_json(self)
    
    def save_to_file(self, file_path: Union[str, Path], format: str = "xml") -> None:
        """Save the persona definition to a file."""
        from ..persona.serializer import PersonaSerializer
        PersonaSerializer.save_to_file(self, file_path, format)

class PersonaManager:
    """Minimal stub for PersonaManager."""
    def __init__(self):
        pass

    def get_persona(self, persona_id):
        # Stub method for compatibility
        return None 
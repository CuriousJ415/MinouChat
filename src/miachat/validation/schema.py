"""
Schema validation for personality definitions.
"""

from typing import Dict, List, Optional, Union
import jsonschema
import yaml
import xmlschema
import os
from pathlib import Path

from ..core.personality import (
    Personality,
    Trait,
    Style,
    Knowledge,
    Backstory
)

# JSON Schema for personality validation
PERSONALITY_JSON_SCHEMA = {
    "type": "object",
    "required": ["name", "version", "traits", "style", "knowledge", "backstory"],
    "properties": {
        "name": {"type": "string"},
        "version": {"type": "string"},
        "traits": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["name", "value"],
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "number", "minimum": 0, "maximum": 1},
                    "description": {"type": "string"}
                }
            }
        },
        "style": {
            "type": "object",
            "required": ["tone", "vocabulary_level", "formality", "humor_level"],
            "properties": {
                "tone": {"type": "string"},
                "vocabulary_level": {"type": "string", "enum": ["simple", "moderate", "advanced"]},
                "formality": {"type": "number", "minimum": 0, "maximum": 1},
                "humor_level": {"type": "number", "minimum": 0, "maximum": 1}
            }
        },
        "knowledge": {
            "type": "object",
            "required": ["domains", "skills", "interests"],
            "properties": {
                "domains": {"type": "array", "items": {"type": "string"}},
                "skills": {"type": "array", "items": {"type": "string"}},
                "interests": {"type": "array", "items": {"type": "string"}}
            }
        },
        "backstory": {
            "type": "object",
            "required": ["background", "experiences", "relationships", "goals"],
            "properties": {
                "background": {"type": "string"},
                "experiences": {"type": "array", "items": {"type": "string"}},
                "relationships": {"type": "array", "items": {"type": "string"}},
                "goals": {"type": "array", "items": {"type": "string"}}
            }
        }
    }
}

class PersonalityValidator:
    """Validates personality definitions in various formats."""
    
    def __init__(self):
        """Initialize the validator with XML schema."""
        schema_path = Path(__file__).parent / "personality.xsd"
        self.xml_schema = xmlschema.XMLSchema(str(schema_path))
    
    def validate_json(self, json_str: str) -> List[str]:
        """Validate a JSON personality definition."""
        try:
            data = yaml.safe_load(json_str)
            jsonschema.validate(instance=data, schema=PERSONALITY_JSON_SCHEMA)
            return []
        except jsonschema.exceptions.ValidationError as e:
            return [str(e)]
        except yaml.YAMLError as e:
            return [f"Invalid YAML: {str(e)}"]
    
    def validate_xml(self, xml_str: str) -> List[str]:
        """Validate an XML personality definition."""
        try:
            self.xml_schema.validate(xml_str)
            return []
        except xmlschema.XMLSchemaValidationError as e:
            return [str(e)]
        except Exception as e:
            return [f"Invalid XML: {str(e)}"]
    
    def validate_personality(self, personality: Personality) -> List[str]:
        """Validate a Personality instance."""
        errors = []
        
        # Validate traits
        for name, trait in personality.traits.items():
            if not 0 <= trait.value <= 1:
                errors.append(f"Trait '{name}' value must be between 0 and 1")
        
        # Validate style
        if personality.style.vocabulary_level not in ["simple", "moderate", "advanced"]:
            errors.append("Invalid vocabulary level")
        if not 0 <= personality.style.formality <= 1:
            errors.append("Formality must be between 0 and 1")
        if not 0 <= personality.style.humor_level <= 1:
            errors.append("Humor level must be between 0 and 1")
        
        # Validate knowledge
        if not personality.knowledge.domains:
            errors.append("At least one knowledge domain is required")
        if not personality.knowledge.skills:
            errors.append("At least one skill is required")
        if not personality.knowledge.interests:
            errors.append("At least one interest is required")
        
        # Validate backstory
        if not personality.backstory.background:
            errors.append("Background is required")
        if not personality.backstory.experiences:
            errors.append("At least one experience is required")
        if not personality.backstory.relationships:
            errors.append("At least one relationship is required")
        if not personality.backstory.goals:
            errors.append("At least one goal is required")
        
        return errors 
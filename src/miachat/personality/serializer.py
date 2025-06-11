"""
Serialization utilities for personality definitions.
"""

import json
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..personality.base import Trait, Style, Knowledge, Backstory

class PersonalitySerializer:
    """Handles serialization and deserialization of personality definitions."""
    
    @staticmethod
    def to_xml(personality: "Personality") -> str:
        """Convert a Personality instance to XML format."""
        root = ET.Element("personality", {
            "name": personality.name,
            "version": "1.0"
        })
        
        # Add traits
        traits_elem = ET.SubElement(root, "traits")
        for trait in personality.traits.values():
            ET.SubElement(traits_elem, "trait", {
                "name": trait.name,
                "value": str(trait.value),
                "description": trait.description or ""
            })
        
        # Add style
        style_elem = ET.SubElement(root, "style")
        ET.SubElement(style_elem, "tone").text = personality.style.tone
        ET.SubElement(style_elem, "vocabulary_level").text = personality.style.vocabulary_level
        ET.SubElement(style_elem, "formality").text = str(personality.style.formality)
        ET.SubElement(style_elem, "humor_level").text = str(personality.style.humor_level)
        
        # Add knowledge
        knowledge_elem = ET.SubElement(root, "knowledge")
        domains_elem = ET.SubElement(knowledge_elem, "domains")
        for domain in personality.knowledge.domains:
            ET.SubElement(domains_elem, "domain").text = domain
        
        skills_elem = ET.SubElement(knowledge_elem, "skills")
        for skill in personality.knowledge.skills:
            ET.SubElement(skills_elem, "skill").text = skill
        
        interests_elem = ET.SubElement(knowledge_elem, "interests")
        for interest in personality.knowledge.interests:
            ET.SubElement(interests_elem, "interest").text = interest
        
        # Add backstory
        backstory_elem = ET.SubElement(root, "backstory")
        ET.SubElement(backstory_elem, "background").text = personality.backstory.background
        
        experiences_elem = ET.SubElement(backstory_elem, "experiences")
        for experience in personality.backstory.experiences:
            ET.SubElement(experiences_elem, "experience").text = experience
        
        relationships_elem = ET.SubElement(backstory_elem, "relationships")
        for relationship in personality.backstory.relationships:
            ET.SubElement(relationships_elem, "relationship").text = relationship
        
        goals_elem = ET.SubElement(backstory_elem, "goals")
        for goal in personality.backstory.goals:
            ET.SubElement(goals_elem, "goal").text = goal
        
        return ET.tostring(root, encoding="unicode", method="xml")
    
    @staticmethod
    def from_xml(xml_str: str) -> "Personality":
        """Create a Personality instance from XML string."""
        from ..core.personality import Personality
        root = ET.fromstring(xml_str)
        
        # Parse traits
        traits = {}
        for trait_elem in root.find("traits").findall("trait"):
            traits[trait_elem.get("name")] = Trait(
                name=trait_elem.get("name"),
                value=float(trait_elem.get("value")),
                description=trait_elem.get("description")
            )
        
        # Parse style
        style_elem = root.find("style")
        style = Style(
            tone=style_elem.find("tone").text,
            vocabulary_level=style_elem.find("vocabulary_level").text,
            formality=float(style_elem.find("formality").text),
            humor_level=float(style_elem.find("humor_level").text)
        )
        
        # Parse knowledge
        knowledge_elem = root.find("knowledge")
        knowledge = Knowledge(
            domains=[d.text for d in knowledge_elem.find("domains").findall("domain")],
            skills=[s.text for s in knowledge_elem.find("skills").findall("skill")],
            interests=[i.text for i in knowledge_elem.find("interests").findall("interest")]
        )
        
        # Parse backstory
        backstory_elem = root.find("backstory")
        backstory = Backstory(
            background=backstory_elem.find("background").text,
            experiences=[e.text for e in backstory_elem.find("experiences").findall("experience")],
            relationships=[r.text for r in backstory_elem.find("relationships").findall("relationship")],
            goals=[g.text for g in backstory_elem.find("goals").findall("goal")]
        )
        
        return Personality(
            name=root.get("name"),
            traits=traits,
            style=style,
            knowledge=knowledge,
            backstory=backstory
        )
    
    @staticmethod
    def to_json(personality: "Personality") -> str:
        """Convert a Personality instance to JSON format."""
        data = {
            "name": personality.name,
            "version": "1.0",
            "traits": {
                name: asdict(trait)
                for name, trait in personality.traits.items()
            },
            "style": asdict(personality.style),
            "knowledge": asdict(personality.knowledge),
            "backstory": asdict(personality.backstory)
        }
        return json.dumps(data, indent=2)
    
    @staticmethod
    def from_json(json_str: str) -> "Personality":
        """Create a Personality instance from JSON string."""
        from ..core.personality import Personality
        data = json.loads(json_str)
        
        # Parse traits
        traits = {
            name: Trait(**trait_data)
            for name, trait_data in data["traits"].items()
        }
        
        # Create personality instance
        return Personality(
            name=data["name"],
            traits=traits,
            style=Style(**data["style"]),
            knowledge=Knowledge(**data["knowledge"]),
            backstory=Backstory(**data["backstory"])
        )
    
    @classmethod
    def save_to_file(
        cls,
        personality: "Personality",
        file_path: Union[str, Path],
        format: str = "xml"
    ) -> None:
        """Save a personality definition to a file."""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == "xml":
            content = cls.to_xml(personality)
        elif format.lower() == "json":
            content = cls.to_json(personality)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        file_path.write_text(content)
    
    @classmethod
    def load_from_file(
        cls,
        file_path: Union[str, Path],
        format: Optional[str] = None
    ) -> "Personality":
        """Load a personality definition from a file."""
        from ..core.personality import Personality
        file_path = Path(file_path)
        
        if format is None:
            format = file_path.suffix[1:].lower()
        
        content = file_path.read_text()
        
        if format == "xml":
            return cls.from_xml(content)
        elif format == "json":
            return cls.from_json(content)
        else:
            raise ValueError(f"Unsupported format: {format}") 
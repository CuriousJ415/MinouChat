"""
Personality definition loader and validator
"""
import json
from pathlib import Path
from typing import Dict, Optional

from lxml import etree

from miachat.core.config import settings
from miachat.personality.schema import PersonalityDefinition


class PersonalityLoader:
    """Loads and validates personality definitions"""
    
    def __init__(self, personality_dir: Optional[Path] = None):
        self.personality_dir = personality_dir or settings.CONFIG_DIR / "personalities"
        self.personality_dir.mkdir(parents=True, exist_ok=True)
        self._personalities: Dict[str, PersonalityDefinition] = {}
    
    def load_personality(self, name: str) -> PersonalityDefinition:
        """Load a personality definition by name"""
        if name in self._personalities:
            return self._personalities[name]
        
        # Try loading from JSON first
        json_path = self.personality_dir / f"{name}.json"
        if json_path.exists():
            with open(json_path) as f:
                data = json.load(f)
                personality = PersonalityDefinition(**data)
                self._personalities[name] = personality
                return personality
        
        # Try loading from XML
        xml_path = self.personality_dir / f"{name}.xml"
        if xml_path.exists():
            personality = self._load_from_xml(xml_path)
            self._personalities[name] = personality
            return personality
        
        raise ValueError(f"Personality '{name}' not found")
    
    def _load_from_xml(self, path: Path) -> PersonalityDefinition:
        """Load personality definition from XML file"""
        tree = etree.parse(str(path))
        root = tree.getroot()
        
        # Convert XML to dictionary
        data = {
            "name": root.get("name"),
            "version": root.get("version", "1.0"),
            "traits": [],
            "backstory": {
                "background": "",
                "experiences": [],
                "relationships": {},
                "goals": []
            },
            "knowledge": {
                "domains": [],
                "skills": [],
                "interests": []
            },
            "style": {
                "tone": "",
                "vocabulary_level": "moderate",
                "formality": 0.5,
                "humor_level": 0.5
            }
        }
        
        # Parse traits
        for trait in root.findall(".//trait"):
            data["traits"].append({
                "name": trait.get("name"),
                "value": float(trait.get("value", 0.5)),
                "description": trait.text
            })
        
        # Parse backstory
        backstory = root.find(".//backstory")
        if backstory is not None:
            data["backstory"]["background"] = backstory.findtext("background", "")
            data["backstory"]["experiences"] = [exp.text for exp in backstory.findall("experiences/experience")]
            data["backstory"]["goals"] = [goal.text for goal in backstory.findall("goals/goal")]
            
            for rel in backstory.findall("relationships/relationship"):
                data["backstory"]["relationships"][rel.get("type")] = rel.text
        
        # Parse knowledge
        knowledge = root.find(".//knowledge")
        if knowledge is not None:
            data["knowledge"]["domains"] = [domain.text for domain in knowledge.findall("domains/domain")]
            data["knowledge"]["skills"] = [skill.text for skill in knowledge.findall("skills/skill")]
            data["knowledge"]["interests"] = [interest.text for interest in knowledge.findall("interests/interest")]
        
        # Parse style
        style = root.find(".//style")
        if style is not None:
            data["style"]["tone"] = style.findtext("tone", "")
            data["style"]["vocabulary_level"] = style.findtext("vocabulary_level", "moderate")
            data["style"]["formality"] = float(style.findtext("formality", "0.5"))
            data["style"]["humor_level"] = float(style.findtext("humor_level", "0.5"))
        
        return PersonalityDefinition(**data)
    
    def save_personality(self, personality: PersonalityDefinition) -> None:
        """Save a personality definition to disk"""
        # Save as JSON
        json_path = self.personality_dir / f"{personality.name}.json"
        with open(json_path, "w") as f:
            json.dump(personality.dict(), f, indent=2)
        
        # Save as XML
        xml_path = self.personality_dir / f"{personality.name}.xml"
        root = etree.Element("personality", name=personality.name, version=personality.version)
        
        # Add traits
        traits_elem = etree.SubElement(root, "traits")
        for trait in personality.traits:
            trait_elem = etree.SubElement(traits_elem, "trait", name=trait.name, value=str(trait.value))
            if trait.description:
                trait_elem.text = trait.description
        
        # Add backstory
        backstory_elem = etree.SubElement(root, "backstory")
        etree.SubElement(backstory_elem, "background").text = personality.backstory.background
        
        experiences_elem = etree.SubElement(backstory_elem, "experiences")
        for exp in personality.backstory.experiences:
            etree.SubElement(experiences_elem, "experience").text = exp
        
        relationships_elem = etree.SubElement(backstory_elem, "relationships")
        for rel_type, rel_desc in personality.backstory.relationships.items():
            etree.SubElement(relationships_elem, "relationship", type=rel_type).text = rel_desc
        
        goals_elem = etree.SubElement(backstory_elem, "goals")
        for goal in personality.backstory.goals:
            etree.SubElement(goals_elem, "goal").text = goal
        
        # Add knowledge
        knowledge_elem = etree.SubElement(root, "knowledge")
        
        domains_elem = etree.SubElement(knowledge_elem, "domains")
        for domain in personality.knowledge.domains:
            etree.SubElement(domains_elem, "domain").text = domain
        
        skills_elem = etree.SubElement(knowledge_elem, "skills")
        for skill in personality.knowledge.skills:
            etree.SubElement(skills_elem, "skill").text = skill
        
        interests_elem = etree.SubElement(knowledge_elem, "interests")
        for interest in personality.knowledge.interests:
            etree.SubElement(interests_elem, "interest").text = interest
        
        # Add style
        style_elem = etree.SubElement(root, "style")
        etree.SubElement(style_elem, "tone").text = personality.style.tone
        etree.SubElement(style_elem, "vocabulary_level").text = personality.style.vocabulary_level
        etree.SubElement(style_elem, "formality").text = str(personality.style.formality)
        etree.SubElement(style_elem, "humor_level").text = str(personality.style.humor_level)
        
        # Write XML file
        tree = etree.ElementTree(root)
        tree.write(str(xml_path), pretty_print=True, xml_declaration=True, encoding="UTF-8")
        
        # Update cache
        self._personalities[personality.name] = personality 
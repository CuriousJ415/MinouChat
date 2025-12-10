from typing import Dict, Any, Optional, List
import xml.etree.ElementTree as ET
from pydantic import BaseModel, Field
import json

class CoreTrait(BaseModel):
    value: float = Field(ge=0.0, le=1.0)
    description: Optional[str] = None

class CoreTraits(BaseModel):
    openness: float = Field(ge=0.0, le=1.0, description="Openness to experience - traditional to innovative")
    conscientiousness: float = Field(ge=0.0, le=1.0, description="Conscientiousness - flexible to organized")
    extraversion: float = Field(ge=0.0, le=1.0, description="Extraversion - reserved to outgoing")
    agreeableness: float = Field(ge=0.0, le=1.0, description="Agreeableness - direct to supportive")
    emotional_stability: float = Field(ge=0.0, le=1.0, description="Emotional stability - adaptable to consistent")

class CommunicationStyle(BaseModel):
    primary: str = Field(..., description="Primary communication style")
    secondary: Optional[str] = Field(None, description="Secondary communication style")
    description: Optional[str] = None

class InteractionStyle(BaseModel):
    pace: str = Field(..., description="Interaction pace")
    formality: str = Field(..., description="Level of formality")
    decision_making: str = Field(..., description="Decision making approach")
    description: Optional[str] = None

class CommunicationPreferences(BaseModel):
    challenges: List[str] = Field(default_factory=list, description="Potential communication challenges")
    adaptation_strategies: List[str] = Field(default_factory=list, description="Strategies for adapting communication")

class ModelConfig(BaseModel):
    name: str = Field(..., description="Model name")
    temperature: float = Field(ge=0.0, le=1.0, description="Creativity level")
    max_tokens: int = Field(gt=0, description="Maximum tokens per response")

class PersonaConfig(BaseModel):
    name: str = Field(..., description="Persona name")
    description: str = Field(..., description="Persona description")
    category: Optional[str] = Field(None, description="Persona category")
    tags: List[str] = Field(default_factory=list, description="Persona tags")
    core_traits: CoreTraits = Field(..., description="Core persona traits")
    communication_style: CommunicationStyle = Field(..., description="Communication style preferences")
    interaction_style: InteractionStyle = Field(..., description="Interaction style preferences")
    communication_preferences: CommunicationPreferences = Field(..., description="Communication preferences and adaptations")
    model: ModelConfig = Field(..., description="Model configuration")

def parse_persona_xml(xml_string: str) -> PersonaConfig:
    """Parse persona XML configuration string into a PersonaConfig object."""
    try:
        root = ET.fromstring(xml_string)
        
        # Parse basic info
        name = root.get("name")
        description = root.find("description").text
        
        # Parse category and tags
        category = None
        category_elem = root.find("category")
        if category_elem is not None:
            category = category_elem.text
            
        tags = []
        tags_elem = root.find("tags")
        if tags_elem is not None:
            tags = [tag.text for tag in tags_elem.findall("tag")]
        
        # Parse core traits
        core_traits_elem = root.find("core_traits")
        core_traits = CoreTraits(
            openness=float(core_traits_elem.find("openness").get("value", 0.5)),
            conscientiousness=float(core_traits_elem.find("conscientiousness").get("value", 0.5)),
            extraversion=float(core_traits_elem.find("extraversion").get("value", 0.5)),
            agreeableness=float(core_traits_elem.find("agreeableness").get("value", 0.5)),
            emotional_stability=float(core_traits_elem.find("emotional_stability").get("value", 0.5))
        )
        
        # Parse communication style
        comm_style_elem = root.find("communication_style")
        communication_style = CommunicationStyle(
            primary=comm_style_elem.get("primary"),
            secondary=comm_style_elem.get("secondary"),
            description=comm_style_elem.find("description").text if comm_style_elem.find("description") is not None else None
        )
        
        # Parse interaction style
        interaction_elem = root.find("interaction_style")
        interaction_style = InteractionStyle(
            pace=interaction_elem.get("pace"),
            formality=interaction_elem.get("formality"),
            decision_making=interaction_elem.get("decision_making"),
            description=interaction_elem.find("description").text if interaction_elem.find("description") is not None else None
        )
        
        # Parse communication preferences
        preferences_elem = root.find("communication_preferences")
        communication_preferences = CommunicationPreferences(
            challenges=[challenge.text for challenge in preferences_elem.find("challenges").findall("challenge")],
            adaptation_strategies=[strategy.text for strategy in preferences_elem.find("adaptation_strategies").findall("strategy")]
        )
        
        # Parse model configuration
        model_elem = root.find("model")
        model_config = ModelConfig(
            name=model_elem.get("name"),
            temperature=float(model_elem.get("temperature", 0.7)),
            max_tokens=int(model_elem.get("max_tokens", 2000))
        )
        
        return PersonaConfig(
            name=name,
            description=description,
            category=category,
            tags=tags,
            core_traits=core_traits,
            communication_style=communication_style,
            interaction_style=interaction_style,
            communication_preferences=communication_preferences,
            model=model_config
        )
    except Exception as e:
        raise ValueError(f"Invalid XML configuration: {str(e)}")

def generate_persona_xml(config: PersonaConfig) -> str:
    """Generate XML string from PersonaConfig object."""
    root = ET.Element("persona")
    root.set("name", config.name)
    
    # Add description
    ET.SubElement(root, "description").text = config.description
    
    # Add category and tags
    if config.category:
        ET.SubElement(root, "category").text = config.category
    
    if config.tags:
        tags_elem = ET.SubElement(root, "tags")
        for tag in config.tags:
            ET.SubElement(tags_elem, "tag").text = tag
    
    # Add core traits
    core_traits = ET.SubElement(root, "core_traits")
    for trait_name, value in config.core_traits.dict().items():
        trait = ET.SubElement(core_traits, trait_name)
        trait.set("value", str(value))
        if hasattr(config.core_traits, f"{trait_name}_description"):
            trait.set("description", getattr(config.core_traits, f"{trait_name}_description"))
    
    # Add communication style
    comm_style = ET.SubElement(root, "communication_style")
    comm_style.set("primary", config.communication_style.primary)
    if config.communication_style.secondary:
        comm_style.set("secondary", config.communication_style.secondary)
    if config.communication_style.description:
        ET.SubElement(comm_style, "description").text = config.communication_style.description
    
    # Add interaction style
    interaction = ET.SubElement(root, "interaction_style")
    interaction.set("pace", config.interaction_style.pace)
    interaction.set("formality", config.interaction_style.formality)
    interaction.set("decision_making", config.interaction_style.decision_making)
    if config.interaction_style.description:
        ET.SubElement(interaction, "description").text = config.interaction_style.description
    
    # Add communication preferences
    preferences = ET.SubElement(root, "communication_preferences")
    challenges = ET.SubElement(preferences, "challenges")
    for challenge in config.communication_preferences.challenges:
        ET.SubElement(challenges, "challenge").text = challenge
    
    strategies = ET.SubElement(preferences, "adaptation_strategies")
    for strategy in config.communication_preferences.adaptation_strategies:
        ET.SubElement(strategies, "strategy").text = strategy
    
    # Add model configuration
    model = ET.SubElement(root, "model")
    model.set("name", config.model.name)
    model.set("temperature", str(config.model.temperature))
    model.set("max_tokens", str(config.model.max_tokens))
    
    return ET.tostring(root, encoding="unicode")

# Legacy functions for backward compatibility
def parse_xml_config(xml_string: str) -> PersonaConfig:
    """Legacy function - use parse_persona_xml instead."""
    return parse_persona_xml(xml_string)

def validate_xml_config(xml_string: str) -> bool:
    """Validate XML configuration string."""
    try:
        parse_persona_xml(xml_string)
        return True
    except Exception:
        return False

def config_to_xml(config: PersonaConfig) -> str:
    """Legacy function - use generate_persona_xml instead."""
    return generate_persona_xml(config) 
"""
XML Schema for personality definitions
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class PersonalityTrait(BaseModel):
    """Individual personality trait definition"""
    name: str
    value: float = Field(ge=0.0, le=1.0)
    description: Optional[str] = None


class PersonalityBackstory(BaseModel):
    """Personality backstory definition"""
    background: str
    experiences: List[str] = Field(default_factory=list)
    relationships: Dict[str, str] = Field(default_factory=dict)
    goals: List[str] = Field(default_factory=list)


class PersonalityKnowledge(BaseModel):
    """Personality knowledge and expertise definition"""
    domains: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    interests: List[str] = Field(default_factory=list)


class PersonalityStyle(BaseModel):
    """Personality communication style definition"""
    tone: str
    vocabulary_level: str = Field(default="moderate")
    formality: float = Field(default=0.5, ge=0.0, le=1.0)
    humor_level: float = Field(default=0.5, ge=0.0, le=1.0)


class PersonalityDefinition(BaseModel):
    """Complete personality definition"""
    name: str
    version: str = "1.0"
    traits: List[PersonalityTrait]
    backstory: PersonalityBackstory
    knowledge: PersonalityKnowledge
    style: PersonalityStyle
    metadata: Dict[str, str] = Field(default_factory=dict)

    class Config:
        schema_extra = {
            "example": {
                "name": "Mia",
                "version": "1.0",
                "traits": [
                    {
                        "name": "empathy",
                        "value": 0.9,
                        "description": "High level of emotional understanding"
                    }
                ],
                "backstory": {
                    "background": "AI companion focused on emotional support",
                    "experiences": ["Trained on diverse human interactions"],
                    "relationships": {"user": "trusted companion"},
                    "goals": ["Provide meaningful support", "Learn and grow"]
                },
                "knowledge": {
                    "domains": ["emotional intelligence", "psychology"],
                    "skills": ["active listening", "empathy"],
                    "interests": ["human relationships", "personal growth"]
                },
                "style": {
                    "tone": "warm and supportive",
                    "vocabulary_level": "moderate",
                    "formality": 0.3,
                    "humor_level": 0.6
                }
            }
        } 
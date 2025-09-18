"""
Base data classes for personality definitions.
"""

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Trait:
    """Represents a personality trait."""
    name: str
    value: float
    description: Optional[str] = None

@dataclass
class Style:
    """Represents communication style."""
    tone: str
    vocabulary_level: str
    formality: float
    humor_level: float

@dataclass
class Knowledge:
    """Represents character knowledge."""
    domains: List[str]
    skills: List[str]
    interests: List[str]

@dataclass
class Backstory:
    """Represents character backstory."""
    background: str
    experiences: List[str]
    relationships: List[str]
    goals: List[str] 
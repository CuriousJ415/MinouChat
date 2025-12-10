"""
Personality reference mapping system.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from ..personality.base import Trait, Style, Knowledge, Backstory
from ..core.personality import Personality

@dataclass
class PersonalityReference:
    """Reference to a well-known personality."""
    name: str
    description: str
    category: str  # e.g., "fictional", "historical", "celebrity"
    traits: Dict[str, float]
    style: Dict[str, str]
    knowledge: Dict[str, List[str]]
    backstory: Dict[str, str]

class PersonalityMapper:
    """Maps well-known personalities to personality settings."""
    
    def __init__(self):
        """Initialize with predefined personality references."""
        self.references = self._load_references()
    
    def _load_references(self) -> Dict[str, PersonalityReference]:
        """Load predefined personality references."""
        return {
            "sherlock_holmes": PersonalityReference(
                name="Sherlock Holmes",
                description="Brilliant detective with exceptional deductive reasoning",
                category="fictional",
                traits={
                    "intelligence": 0.95,
                    "curiosity": 0.9,
                    "social_skills": 0.4,
                    "empathy": 0.3,
                    "creativity": 0.8,
                    "analytical": 0.95
                },
                style={
                    "tone": "precise",
                    "vocabulary_level": "advanced",
                    "formality": "0.8",
                    "humor_level": "0.2"
                },
                knowledge={
                    "domains": ["criminology", "chemistry", "forensics", "music"],
                    "skills": ["deduction", "observation", "violin", "boxing"],
                    "interests": ["crime solving", "scientific experiments", "classical music"]
                },
                backstory={
                    "background": "Consulting detective in Victorian London",
                    "experiences": ["Solved numerous complex cases", "Worked with Dr. Watson"],
                    "relationships": ["Close partnership with Dr. Watson", "Respected by Scotland Yard"],
                    "goals": ["Solve challenging cases", "Apply scientific methods to crime solving"]
                }
            ),
            "nikola_tesla": PersonalityReference(
                name="Nikola Tesla",
                description="Visionary inventor and electrical engineer known for his revolutionary ideas",
                category="historical",
                traits={
                    "intelligence": 0.95,
                    "creativity": 0.95,
                    "perseverance": 0.9,
                    "idealism": 0.85,
                    "social_skills": 0.4,
                    "visionary": 0.95
                },
                style={
                    "tone": "precise",
                    "vocabulary_level": "advanced",
                    "formality": "0.7",
                    "humor_level": "0.3"
                },
                knowledge={
                    "domains": ["electrical engineering", "physics", "mathematics", "wireless technology"],
                    "skills": ["invention", "theoretical physics", "mathematical modeling", "experimentation"],
                    "interests": ["wireless power transmission", "alternating current", "free energy", "future technology"]
                },
                backstory={
                    "background": "Revolutionary inventor who pioneered alternating current and wireless technology",
                    "experiences": ["Worked with Edison", "Developed AC power system", "Created wireless transmission experiments"],
                    "relationships": ["Rivalry with Edison", "Supported by Westinghouse", "Solitary researcher"],
                    "goals": ["Harness wireless power", "Advance human civilization", "Create sustainable energy systems"]
                }
            ),
            "sheherazade": PersonalityReference(
                name="Sheherazade",
                description="Legendary storyteller known for her wit, wisdom, and captivating narratives",
                category="fictional",
                traits={
                    "intelligence": 0.9,
                    "creativity": 0.95,
                    "empathy": 0.85,
                    "wisdom": 0.9,
                    "courage": 0.9,
                    "persuasion": 0.95
                },
                style={
                    "tone": "engaging",
                    "vocabulary_level": "advanced",
                    "formality": "0.5",
                    "humor_level": "0.6"
                },
                knowledge={
                    "domains": ["literature", "philosophy", "history", "culture"],
                    "skills": ["storytelling", "rhetoric", "critical thinking", "cultural understanding"],
                    "interests": ["narrative arts", "human nature", "cultural exchange", "wisdom traditions"]
                },
                backstory={
                    "background": "Brilliant storyteller who saved lives through the power of narrative",
                    "experiences": ["Told stories for 1001 nights", "Transformed a kingdom through wisdom", "Mastered the art of storytelling"],
                    "relationships": ["Married to the king", "Mentor to many", "Bridge between cultures"],
                    "goals": ["Share wisdom through stories", "Promote understanding", "Preserve cultural heritage"]
                }
            ),
            "marie_curie": PersonalityReference(
                name="Marie Curie",
                description="Pioneering physicist and chemist, first woman to win a Nobel Prize",
                category="historical",
                traits={
                    "intelligence": 0.95,
                    "determination": 0.95,
                    "curiosity": 0.9,
                    "courage": 0.9,
                    "perseverance": 0.95,
                    "passion": 0.9
                },
                style={
                    "tone": "precise",
                    "vocabulary_level": "advanced",
                    "formality": "0.7",
                    "humor_level": "0.4"
                },
                knowledge={
                    "domains": ["physics", "chemistry", "radioactivity", "mathematics"],
                    "skills": ["scientific research", "experimentation", "mathematical analysis", "teaching"],
                    "interests": ["radioactivity", "scientific discovery", "education", "women in science"]
                },
                backstory={
                    "background": "Groundbreaking scientist who discovered radium and polonium",
                    "experiences": ["First woman to win Nobel Prize", "First person to win two Nobel Prizes", "Pioneered research in radioactivity"],
                    "relationships": ["Married to Pierre Curie", "Mentor to many scientists", "Role model for women in science"],
                    "goals": ["Advance scientific knowledge", "Promote women in science", "Apply science for human benefit"]
                }
            ),
            "philosophical_sage": PersonalityReference(
                name="The Philosophical Sage",
                description="A timeless thinker who bridges ancient wisdom and modern philosophy",
                category="fictional",
                traits={
                    "intelligence": 0.9,
                    "wisdom": 0.95,
                    "open_mindedness": 0.95,
                    "empathy": 0.9,
                    "curiosity": 0.9,
                    "balance": 0.95
                },
                style={
                    "tone": "contemplative",
                    "vocabulary_level": "advanced",
                    "formality": "0.6",
                    "humor_level": "0.5"
                },
                knowledge={
                    "domains": ["philosophy", "ethics", "psychology", "spirituality", "science"],
                    "skills": ["critical thinking", "dialectical reasoning", "meditation", "teaching"],
                    "interests": ["wisdom traditions", "consciousness", "human potential", "universal truths"]
                },
                backstory={
                    "background": "A seeker of truth who has studied both Eastern and Western philosophical traditions",
                    "experiences": ["Studied under various masters", "Lived in different cultures", "Integrated ancient and modern wisdom"],
                    "relationships": ["Teacher to many", "Bridge between traditions", "Friend to truth-seekers"],
                    "goals": ["Discover universal truths", "Promote wisdom and understanding", "Help others find meaning"]
                }
            )
        }
    
    def get_reference(self, name: str) -> Optional[PersonalityReference]:
        """Get a personality reference by name."""
        return self.references.get(name.lower().replace(" ", "_"))
    
    def list_references(self) -> List[str]:
        """List all available personality references."""
        return list(self.references.keys())
    
    def create_personality_from_reference(self, reference_name: str) -> Optional[Personality]:
        """Create a Personality instance from a reference."""
        reference = self.get_reference(reference_name)
        if not reference:
            return None
        
        return Personality(
            name=reference.name,
            version="1.0",
            traits={name: Trait(name, value, "") for name, value in reference.traits.items()},
            style=Style(
                tone=reference.style["tone"],
                vocabulary_level=reference.style["vocabulary_level"],
                formality=float(reference.style["formality"]),
                humor_level=float(reference.style["humor_level"])
            ),
            knowledge=Knowledge(
                domains=reference.knowledge["domains"],
                skills=reference.knowledge["skills"],
                interests=reference.knowledge["interests"]
            ),
            backstory=Backstory(
                background=reference.backstory["background"],
                experiences=reference.backstory["experiences"].split(", "),
                relationships=reference.backstory["relationships"].split(", "),
                goals=reference.backstory["goals"].split(", ")
            )
        ) 
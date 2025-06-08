"""
Personality Analysis and Management
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import json
import os
from pathlib import Path

@dataclass
class PersonalityAnalysis:
    """Results of character analysis"""
    traits: Dict[str, float]  # Personality traits and their values
    style: Dict[str, str]  # Communication style
    knowledge: Dict[str, List[str]]  # Knowledge domains, skills, and interests
    backstory: Dict[str, str]  # Background, experiences, and goals

def analyze_character_description(description: str) -> PersonalityAnalysis:
    """
    Analyze a character description and suggest personality traits.
    Uses the LLM to analyze the description and extract personality traits.
    """
    from app.llm.adapter import get_llm_adapter
    
    # Get LLM adapter
    llm = get_llm_adapter()
    
    # Create prompt for character analysis
    prompt = f"""Analyze the following character description and extract personality traits, communication style, knowledge, and backstory:

{description}

Provide the analysis in the following JSON format:
{{
    "traits": {{
        "empathy": 0.0-1.0,
        "intelligence": 0.0-1.0,
        "creativity": 0.0-1.0,
        "adaptability": 0.0-1.0,
        "reliability": 0.0-1.0
    }},
    "style": {{
        "tone": "warm/professional/casual",
        "vocabulary_level": "simple/moderate/advanced",
        "formality": 0.0-1.0,
        "humor_level": 0.0-1.0
    }},
    "knowledge": {{
        "domains": ["domain1", "domain2"],
        "skills": ["skill1", "skill2"],
        "interests": ["interest1", "interest2"]
    }},
    "backstory": {{
        "background": "character background",
        "experiences": ["experience1", "experience2"],
        "goals": ["goal1", "goal2"]
    }}
}}"""
    
    # Get analysis from LLM
    response = llm.generate(prompt)
    
    try:
        # Parse JSON response
        analysis_data = json.loads(response)
        
        # Create PersonalityAnalysis object
        return PersonalityAnalysis(
            traits=analysis_data["traits"],
            style=analysis_data["style"],
            knowledge=analysis_data["knowledge"],
            backstory=analysis_data["backstory"]
        )
    except Exception as e:
        raise ValueError(f"Failed to parse character analysis: {str(e)}")

def save_personality_definition(data: Dict) -> bool:
    """
    Save a personality definition to a file.
    The data should contain traits, style, knowledge, and backstory.
    """
    try:
        # Create personalities directory if it doesn't exist
        personalities_dir = Path("config/personalities")
        personalities_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename from traits
        name = data.get("name", "custom_personality")
        filename = f"{name.lower().replace(' ', '_')}.json"
        filepath = personalities_dir / filename
        
        # Save personality definition
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        return True
    except Exception as e:
        raise ValueError(f"Failed to save personality definition: {str(e)}")

def load_personality_definition(name: str) -> Optional[Dict]:
    """
    Load a personality definition from a file.
    """
    try:
        filepath = Path("config/personalities") / f"{name.lower().replace(' ', '_')}.json"
        if not filepath.exists():
            return None
        
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to load personality definition: {str(e)}") 
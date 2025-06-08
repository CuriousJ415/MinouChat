#!/usr/bin/env python3
"""
Test script for personality framework
"""
import json
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from miachat.personality.loader import PersonalityLoader
from miachat.personality.schema import PersonalityDefinition


def main():
    """Main function"""
    # Create loader
    loader = PersonalityLoader()
    
    # Load Mia personality
    try:
        personality = loader.load_personality("mia")
        print(f"\nLoaded personality: {personality.name} (v{personality.version})")
        
        # Print traits
        print("\nTraits:")
        for trait in personality.traits:
            print(f"- {trait.name}: {trait.value} ({trait.description})")
        
        # Print backstory
        print("\nBackstory:")
        print(f"Background: {personality.backstory.background}")
        print("\nExperiences:")
        for exp in personality.backstory.experiences:
            print(f"- {exp}")
        print("\nRelationships:")
        for rel_type, rel_desc in personality.backstory.relationships.items():
            print(f"- {rel_type}: {rel_desc}")
        print("\nGoals:")
        for goal in personality.backstory.goals:
            print(f"- {goal}")
        
        # Print knowledge
        print("\nKnowledge:")
        print("Domains:")
        for domain in personality.knowledge.domains:
            print(f"- {domain}")
        print("\nSkills:")
        for skill in personality.knowledge.skills:
            print(f"- {skill}")
        print("\nInterests:")
        for interest in personality.knowledge.interests:
            print(f"- {interest}")
        
        # Print style
        print("\nStyle:")
        print(f"Tone: {personality.style.tone}")
        print(f"Vocabulary Level: {personality.style.vocabulary_level}")
        print(f"Formality: {personality.style.formality}")
        print(f"Humor Level: {personality.style.humor_level}")
        
        # Save as JSON for inspection
        json_path = Path("mia_personality.json")
        with open(json_path, "w") as f:
            json.dump(personality.model_dump(), f, indent=2)
        print(f"\nSaved personality definition to {json_path}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main() 
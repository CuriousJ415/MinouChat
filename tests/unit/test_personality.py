"""
Unit tests for personality framework
"""
import pytest
from pathlib import Path

from miachat.personality.loader import PersonalityLoader
from miachat.personality.schema import PersonalityDefinition


def test_load_personality():
    """Test loading a personality definition"""
    loader = PersonalityLoader()
    personality = loader.load_personality("mia")
    
    assert isinstance(personality, PersonalityDefinition)
    assert personality.name == "Mia"
    assert personality.version == "1.0"
    
    # Test traits
    assert len(personality.traits) == 5
    empathy_trait = next(t for t in personality.traits if t.name == "empathy")
    assert empathy_trait.value == 0.9
    assert "emotional understanding" in empathy_trait.description.lower()
    
    # Test backstory
    assert "emotional intelligence" in personality.backstory.background.lower()
    assert len(personality.backstory.experiences) == 3
    assert personality.backstory.relationships["user"] == "trusted companion and guide"
    assert len(personality.backstory.goals) == 4
    
    # Test knowledge
    assert "emotional intelligence" in personality.knowledge.domains
    assert "active listening" in personality.knowledge.skills
    assert "human relationships" in personality.knowledge.interests
    
    # Test style
    assert "warm" in personality.style.tone.lower()
    assert personality.style.vocabulary_level == "moderate"
    assert personality.style.formality == 0.3
    assert personality.style.humor_level == 0.6


def test_save_personality(tmp_path):
    """Test saving a personality definition"""
    # Create a temporary personality directory
    personality_dir = tmp_path / "personalities"
    personality_dir.mkdir()
    
    # Create a test personality
    personality = PersonalityDefinition(
        name="TestPersonality",
        version="1.0",
        traits=[
            {
                "name": "test_trait",
                "value": 0.5,
                "description": "Test trait description"
            }
        ],
        backstory={
            "background": "Test background",
            "experiences": ["Test experience"],
            "relationships": {"test": "test relationship"},
            "goals": ["Test goal"]
        },
        knowledge={
            "domains": ["test domain"],
            "skills": ["test skill"],
            "interests": ["test interest"]
        },
        style={
            "tone": "test tone",
            "vocabulary_level": "moderate",
            "formality": 0.5,
            "humor_level": 0.5
        }
    )
    
    # Save the personality
    loader = PersonalityLoader(personality_dir)
    loader.save_personality(personality)
    
    # Verify files were created
    assert (personality_dir / "TestPersonality.json").exists()
    assert (personality_dir / "TestPersonality.xml").exists()
    
    # Load the personality back
    loaded_personality = loader.load_personality("TestPersonality")
    
    # Verify the loaded personality matches the original
    assert loaded_personality.name == personality.name
    assert loaded_personality.version == personality.version
    assert len(loaded_personality.traits) == len(personality.traits)
    assert loaded_personality.backstory.background == personality.backstory.background
    assert loaded_personality.knowledge.domains == personality.knowledge.domains
    assert loaded_personality.style.tone == personality.style.tone 
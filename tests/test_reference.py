"""
Tests for personality reference system.
"""

import pytest
from miachat.personality.reference import PersonalityMapper, PersonalityReference

def test_list_references():
    """Test listing available personality references."""
    mapper = PersonalityMapper()
    references = mapper.list_references()
    
    assert len(references) == 5  # We now have 5 personalities
    assert "sherlock_holmes" in references
    assert "nikola_tesla" in references
    assert "sheherazade" in references
    assert "marie_curie" in references
    assert "philosophical_sage" in references

def test_get_reference():
    """Test getting a personality reference."""
    mapper = PersonalityMapper()
    
    # Test getting existing reference
    reference = mapper.get_reference("Marie Curie")
    assert reference is not None
    assert reference.name == "Marie Curie"
    assert reference.category == "historical"
    assert "intelligence" in reference.traits
    assert reference.traits["intelligence"] == 0.95
    
    # Test getting non-existent reference
    reference = mapper.get_reference("Non Existent")
    assert reference is None

def test_create_personality_from_reference():
    """Test creating a personality from a reference."""
    mapper = PersonalityMapper()
    
    # Test creating from existing reference
    personality = mapper.create_personality_from_reference("Sheherazade")
    assert personality is not None
    assert personality.name == "Sheherazade"
    assert personality.style.tone == "engaging"
    assert personality.style.vocabulary_level == "advanced"
    assert personality.style.formality == 0.5
    assert personality.style.humor_level == 0.6
    assert "literature" in personality.knowledge.domains
    assert "storytelling" in personality.knowledge.skills
    assert "narrative arts" in personality.knowledge.interests
    
    # Test creating from non-existent reference
    personality = mapper.create_personality_from_reference("Non Existent")
    assert personality is None

def test_reference_attributes():
    """Test personality reference attributes."""
    mapper = PersonalityMapper()
    reference = mapper.get_reference("Nikola Tesla")
    
    assert reference is not None
    assert reference.name == "Nikola Tesla"
    assert reference.description == "Visionary inventor and electrical engineer known for his revolutionary ideas"
    assert reference.category == "historical"
    
    # Test traits
    assert "intelligence" in reference.traits
    assert "creativity" in reference.traits
    assert "visionary" in reference.traits
    assert all(0 <= value <= 1 for value in reference.traits.values())
    
    # Test style
    assert "tone" in reference.style
    assert "vocabulary_level" in reference.style
    assert "formality" in reference.style
    assert "humor_level" in reference.style
    assert reference.style["vocabulary_level"] in ["simple", "moderate", "advanced"]
    
    # Test knowledge
    assert "domains" in reference.knowledge
    assert "skills" in reference.knowledge
    assert "interests" in reference.knowledge
    assert len(reference.knowledge["domains"]) > 0
    assert len(reference.knowledge["skills"]) > 0
    assert len(reference.knowledge["interests"]) > 0
    
    # Test backstory
    assert "background" in reference.backstory
    assert "experiences" in reference.backstory
    assert "relationships" in reference.backstory
    assert "goals" in reference.backstory
    assert len(reference.backstory["background"]) > 0
    assert len(reference.backstory["experiences"]) > 0
    assert len(reference.backstory["relationships"]) > 0
    assert len(reference.backstory["goals"]) > 0

def test_philosophical_sage():
    """Test the philosophical sage personality."""
    mapper = PersonalityMapper()
    reference = mapper.get_reference("The Philosophical Sage")
    
    assert reference is not None
    assert reference.name == "The Philosophical Sage"
    assert reference.category == "fictional"
    assert "wisdom" in reference.traits
    assert "open_mindedness" in reference.traits
    assert "balance" in reference.traits
    assert reference.style["tone"] == "contemplative"
    assert "philosophy" in reference.knowledge["domains"]
    assert "wisdom traditions" in reference.knowledge["interests"] 
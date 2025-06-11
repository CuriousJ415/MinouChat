"""
Unit tests for the PersonalitySerializer class.
"""

import json
import tempfile
from pathlib import Path

import pytest
import xml.etree.ElementTree as ET

from miachat.core.personality import (
    Personality,
    Trait,
    Style,
    Knowledge,
    Backstory
)
from miachat.personality.serializer import PersonalitySerializer

@pytest.fixture
def sample_personality():
    """Create a sample personality for testing."""
    traits = {
        "empathy": Trait("empathy", 0.8, "High emotional understanding"),
        "intelligence": Trait("intelligence", 0.9, "High analytical capabilities")
    }
    
    style = Style(
        tone="warm",
        vocabulary_level="advanced",
        formality=0.7,
        humor_level=0.6
    )
    
    knowledge = Knowledge(
        domains=["science", "technology"],
        skills=["problem-solving", "communication"],
        interests=["AI", "ethics"]
    )
    
    backstory = Backstory(
        background="An AI assistant designed for meaningful dialogue",
        experiences=["Extensive interaction with humans"],
        relationships=["Trusted companion to users"],
        goals=["Provide helpful and engaging conversation"]
    )
    
    return Personality(
        name="TestAI",
        traits=traits,
        style=style,
        knowledge=knowledge,
        backstory=backstory
    )

def test_xml_serialization(sample_personality):
    """Test XML serialization and deserialization."""
    # Convert to XML
    xml_str = PersonalitySerializer.to_xml(sample_personality)
    
    # Parse XML to verify structure
    root = ET.fromstring(xml_str)
    assert root.tag == "personality"
    assert root.get("name") == "TestAI"
    assert root.get("version") == "1.0"
    
    # Verify traits
    traits_elem = root.find("traits")
    assert len(traits_elem.findall("trait")) == 2
    
    # Convert back to Personality
    personality = PersonalitySerializer.from_xml(xml_str)
    assert personality.name == sample_personality.name
    assert len(personality.traits) == len(sample_personality.traits)
    assert personality.style.tone == sample_personality.style.tone
    assert len(personality.knowledge.domains) == len(sample_personality.knowledge.domains)
    assert personality.backstory.background == sample_personality.backstory.background

def test_json_serialization(sample_personality):
    """Test JSON serialization and deserialization."""
    # Convert to JSON
    json_str = PersonalitySerializer.to_json(sample_personality)
    
    # Parse JSON to verify structure
    data = json.loads(json_str)
    assert data["name"] == "TestAI"
    assert data["version"] == "1.0"
    assert len(data["traits"]) == 2
    
    # Convert back to Personality
    personality = PersonalitySerializer.from_json(json_str)
    assert personality.name == sample_personality.name
    assert len(personality.traits) == len(sample_personality.traits)
    assert personality.style.tone == sample_personality.style.tone
    assert len(personality.knowledge.domains) == len(sample_personality.knowledge.domains)
    assert personality.backstory.background == sample_personality.backstory.background

def test_file_operations(sample_personality):
    """Test saving and loading personality definitions from files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test XML file operations
        xml_path = Path(temp_dir) / "test.xml"
        PersonalitySerializer.save_to_file(sample_personality, xml_path, format="xml")
        loaded_personality = PersonalitySerializer.load_from_file(xml_path)
        assert loaded_personality.name == sample_personality.name
        
        # Test JSON file operations
        json_path = Path(temp_dir) / "test.json"
        PersonalitySerializer.save_to_file(sample_personality, json_path, format="json")
        loaded_personality = PersonalitySerializer.load_from_file(json_path)
        assert loaded_personality.name == sample_personality.name

def test_invalid_format():
    """Test handling of invalid format."""
    with pytest.raises(ValueError):
        PersonalitySerializer.save_to_file(
            sample_personality,
            "test.txt",
            format="txt"
        ) 
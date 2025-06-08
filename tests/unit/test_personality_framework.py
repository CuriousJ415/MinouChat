"""
Unit tests for the personality framework
"""
import json
import pytest
from pathlib import Path
from app.core.personality import (
    analyze_character_description,
    save_personality_definition,
    load_personality_definition,
    PersonalityAnalysis
)

# Mock LLM responses for testing
MOCK_ANALYSIS_RESPONSE = {
    "traits": {
        "empathy": 0.8,
        "intelligence": 0.9,
        "creativity": 0.7,
        "adaptability": 0.6,
        "reliability": 0.85
    },
    "style": {
        "tone": "warm",
        "vocabulary_level": "advanced",
        "formality": 0.7,
        "humor_level": 0.6
    },
    "knowledge": {
        "domains": ["science", "technology", "philosophy"],
        "skills": ["problem-solving", "critical thinking", "communication"],
        "interests": ["AI", "ethics", "cognitive science"]
    },
    "backstory": {
        "background": "A highly intelligent AI assistant with a strong focus on ethical considerations",
        "experiences": [
            "Extensive training in various scientific domains",
            "Deep understanding of human psychology and communication"
        ],
        "goals": [
            "Help users achieve their goals while maintaining ethical standards",
            "Continuously learn and improve understanding of human needs"
        ]
    }
}

# Mock personality data for testing
MOCK_PERSONALITY_DATA = {
    "name": "test_personality",
    "traits": {
        "empathy": 0.8,
        "intelligence": 0.9,
        "creativity": 0.7,
        "adaptability": 0.6,
        "reliability": 0.85
    },
    "style": {
        "tone": "warm",
        "vocabulary_level": "advanced",
        "formality": 0.7,
        "humor_level": 0.6
    },
    "knowledge": {
        "domains": ["science", "technology", "philosophy"],
        "skills": ["problem-solving", "critical thinking", "communication"],
        "interests": ["AI", "ethics", "cognitive science"]
    },
    "backstory": {
        "background": "A highly intelligent AI assistant with a strong focus on ethical considerations",
        "experiences": [
            "Extensive training in various scientific domains",
            "Deep understanding of human psychology and communication"
        ],
        "goals": [
            "Help users achieve their goals while maintaining ethical standards",
            "Continuously learn and improve understanding of human needs"
        ]
    }
}

@pytest.fixture
def mock_llm(monkeypatch):
    """Mock the LLM adapter for testing"""
    def mock_generate(prompt):
        return json.dumps(MOCK_ANALYSIS_RESPONSE)
    
    monkeypatch.setattr("app.llm.adapter.get_llm_adapter", lambda: type("MockLLM", (), {"generate": mock_generate})())

@pytest.fixture
def temp_personality_dir(tmp_path):
    """Create a temporary directory for personality files"""
    personality_dir = tmp_path / "config" / "personalities"
    personality_dir.mkdir(parents=True)
    return personality_dir

def test_analyze_character_description(mock_llm):
    """Test character analysis with valid input"""
    description = "A highly intelligent AI assistant with a warm personality and strong ethical values"
    analysis = analyze_character_description(description)
    
    assert isinstance(analysis, PersonalityAnalysis)
    assert analysis.traits == MOCK_ANALYSIS_RESPONSE["traits"]
    assert analysis.style == MOCK_ANALYSIS_RESPONSE["style"]
    assert analysis.knowledge == MOCK_ANALYSIS_RESPONSE["knowledge"]
    assert analysis.backstory == MOCK_ANALYSIS_RESPONSE["backstory"]

def test_analyze_character_description_empty(mock_llm):
    """Test character analysis with empty input"""
    with pytest.raises(ValueError):
        analyze_character_description("")

def test_analyze_character_description_invalid_llm_response(mock_llm, monkeypatch):
    """Test character analysis with invalid LLM response"""
    def mock_generate_invalid(prompt):
        return "invalid json"
    
    monkeypatch.setattr("app.llm.adapter.get_llm_adapter", lambda: type("MockLLM", (), {"generate": mock_generate_invalid})())
    
    with pytest.raises(ValueError):
        analyze_character_description("Test character")

def test_save_personality_definition(temp_personality_dir, monkeypatch):
    """Test saving personality definition"""
    monkeypatch.setattr("app.core.personality.Path", lambda x: temp_personality_dir / x)
    
    success = save_personality_definition(MOCK_PERSONALITY_DATA)
    assert success is True
    
    # Verify file was created
    filepath = temp_personality_dir / "test_personality.json"
    assert filepath.exists()
    
    # Verify file contents
    with open(filepath, "r") as f:
        saved_data = json.load(f)
    assert saved_data == MOCK_PERSONALITY_DATA

def test_save_personality_definition_invalid_data(temp_personality_dir, monkeypatch):
    """Test saving personality definition with invalid data"""
    monkeypatch.setattr("app.core.personality.Path", lambda x: temp_personality_dir / x)
    
    with pytest.raises(ValueError):
        save_personality_definition({"invalid": "data"})

def test_load_personality_definition(temp_personality_dir, monkeypatch):
    """Test loading personality definition"""
    monkeypatch.setattr("app.core.personality.Path", lambda x: temp_personality_dir / x)
    
    # Save test data
    filepath = temp_personality_dir / "test_personality.json"
    with open(filepath, "w") as f:
        json.dump(MOCK_PERSONALITY_DATA, f)
    
    # Load and verify
    loaded_data = load_personality_definition("test_personality")
    assert loaded_data == MOCK_PERSONALITY_DATA

def test_load_personality_definition_not_found(temp_personality_dir, monkeypatch):
    """Test loading non-existent personality definition"""
    monkeypatch.setattr("app.core.personality.Path", lambda x: temp_personality_dir / x)
    
    loaded_data = load_personality_definition("nonexistent")
    assert loaded_data is None

def test_load_personality_definition_invalid_json(temp_personality_dir, monkeypatch):
    """Test loading personality definition with invalid JSON"""
    monkeypatch.setattr("app.core.personality.Path", lambda x: temp_personality_dir / x)
    
    # Create file with invalid JSON
    filepath = temp_personality_dir / "invalid.json"
    with open(filepath, "w") as f:
        f.write("invalid json")
    
    with pytest.raises(ValueError):
        load_personality_definition("invalid")

def test_personality_analysis_edge_cases(mock_llm):
    """Test character analysis with edge cases"""
    # Test with very long description
    long_description = "A" * 1000
    analysis = analyze_character_description(long_description)
    assert isinstance(analysis, PersonalityAnalysis)
    
    # Test with special characters
    special_chars = "!@#$%^&*()_+{}|:<>?~`-=[]\\;',./"
    analysis = analyze_character_description(special_chars)
    assert isinstance(analysis, PersonalityAnalysis)
    
    # Test with unicode characters
    unicode_chars = "你好，世界！"
    analysis = analyze_character_description(unicode_chars)
    assert isinstance(analysis, PersonalityAnalysis)

def test_personality_definition_edge_cases(temp_personality_dir, monkeypatch):
    """Test personality definition with edge cases"""
    monkeypatch.setattr("app.core.personality.Path", lambda x: temp_personality_dir / x)
    
    # Test with empty lists
    data = MOCK_PERSONALITY_DATA.copy()
    data["knowledge"]["domains"] = []
    data["knowledge"]["skills"] = []
    data["knowledge"]["interests"] = []
    data["backstory"]["experiences"] = []
    data["backstory"]["goals"] = []
    
    success = save_personality_definition(data)
    assert success is True
    
    # Test with very long strings
    data = MOCK_PERSONALITY_DATA.copy()
    data["backstory"]["background"] = "A" * 1000
    success = save_personality_definition(data)
    assert success is True
    
    # Test with special characters in name
    data = MOCK_PERSONALITY_DATA.copy()
    data["name"] = "test!@#$%^&*()_+"
    success = save_personality_definition(data)
    assert success is True 
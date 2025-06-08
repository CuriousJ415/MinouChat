"""
Unit tests for the personality API endpoints
"""
import json
import pytest
from flask import Flask
from app.api.characters import characters_bp
from app.core.personality import PersonalityAnalysis

# Mock personality analysis response
MOCK_ANALYSIS = PersonalityAnalysis(
    traits={
        "empathy": 0.8,
        "intelligence": 0.9,
        "creativity": 0.7,
        "adaptability": 0.6,
        "reliability": 0.85
    },
    style={
        "tone": "warm",
        "vocabulary_level": "advanced",
        "formality": 0.7,
        "humor_level": 0.6
    },
    knowledge={
        "domains": ["science", "technology", "philosophy"],
        "skills": ["problem-solving", "critical thinking", "communication"],
        "interests": ["AI", "ethics", "cognitive science"]
    },
    backstory={
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
)

@pytest.fixture
def app():
    """Create a test Flask application"""
    app = Flask(__name__)
    app.register_blueprint(characters_bp, url_prefix='/api/characters')
    return app

@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()

@pytest.fixture
def mock_analyze_character(monkeypatch):
    """Mock the analyze_character_description function"""
    def mock_analyze(description):
        return MOCK_ANALYSIS
    monkeypatch.setattr("app.core.personality.analyze_character_description", mock_analyze)

@pytest.fixture
def mock_save_personality(monkeypatch):
    """Mock the save_personality_definition function"""
    def mock_save(data):
        return True
    monkeypatch.setattr("app.core.personality.save_personality_definition", mock_save)

def test_analyze_character_endpoint(client, mock_analyze_character):
    """Test the analyze-character endpoint with valid input"""
    response = client.post('/api/characters/analyze-character', json={
        "description": "A highly intelligent AI assistant with a warm personality"
    })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["traits"] == MOCK_ANALYSIS.traits
    assert data["style"] == MOCK_ANALYSIS.style
    assert data["knowledge"] == MOCK_ANALYSIS.knowledge
    assert data["backstory"] == MOCK_ANALYSIS.backstory

def test_analyze_character_endpoint_missing_description(client):
    """Test the analyze-character endpoint with missing description"""
    response = client.post('/api/characters/analyze-character', json={})
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False
    assert "error" in data

def test_analyze_character_endpoint_empty_description(client):
    """Test the analyze-character endpoint with empty description"""
    response = client.post('/api/characters/analyze-character', json={
        "description": ""
    })
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False
    assert "error" in data

def test_analyze_character_endpoint_invalid_json(client):
    """Test the analyze-character endpoint with invalid JSON"""
    response = client.post('/api/characters/analyze-character', data="invalid json")
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False
    assert "error" in data

def test_save_personality_endpoint(client, mock_save_personality):
    """Test the save-personality endpoint with valid data"""
    personality_data = {
        "name": "test_personality",
        "traits": MOCK_ANALYSIS.traits,
        "style": MOCK_ANALYSIS.style,
        "knowledge": MOCK_ANALYSIS.knowledge,
        "backstory": MOCK_ANALYSIS.backstory
    }
    
    response = client.post('/api/characters/save-personality', json=personality_data)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert "message" in data

def test_save_personality_endpoint_missing_data(client):
    """Test the save-personality endpoint with missing data"""
    response = client.post('/api/characters/save-personality', json={})
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False
    assert "error" in data

def test_save_personality_endpoint_invalid_data(client):
    """Test the save-personality endpoint with invalid data"""
    response = client.post('/api/characters/save-personality', json={
        "invalid": "data"
    })
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False
    assert "error" in data

def test_save_personality_endpoint_invalid_json(client):
    """Test the save-personality endpoint with invalid JSON"""
    response = client.post('/api/characters/save-personality', data="invalid json")
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False
    assert "error" in data

def test_analyze_character_endpoint_error_handling(client, mock_analyze_character, monkeypatch):
    """Test error handling in the analyze-character endpoint"""
    def mock_analyze_error(description):
        raise ValueError("Test error")
    
    monkeypatch.setattr("app.core.personality.analyze_character_description", mock_analyze_error)
    
    response = client.post('/api/characters/analyze-character', json={
        "description": "Test character"
    })
    
    assert response.status_code == 500
    data = json.loads(response.data)
    assert data["success"] is False
    assert "error" in data

def test_save_personality_endpoint_error_handling(client, mock_save_personality, monkeypatch):
    """Test error handling in the save-personality endpoint"""
    def mock_save_error(data):
        raise ValueError("Test error")
    
    monkeypatch.setattr("app.core.personality.save_personality_definition", mock_save_error)
    
    response = client.post('/api/characters/save-personality', json={
        "name": "test_personality",
        "traits": MOCK_ANALYSIS.traits
    })
    
    assert response.status_code == 500
    data = json.loads(response.data)
    assert data["success"] is False
    assert "error" in data 
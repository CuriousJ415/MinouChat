"""
Tests for personality validation.
"""

import pytest
from miachat.validation.schema import PersonalityValidator
from miachat.core.personality import (
    Personality,
    Trait,
    Style,
    Knowledge,
    Backstory
)

def test_validate_valid_json():
    """Test validation of valid JSON personality definition."""
    valid_json = """
    name: Test Personality
    version: 1.0
    traits:
      friendliness:
        name: Friendliness
        value: 0.8
        description: Very friendly and approachable
    style:
      tone: friendly
      vocabulary_level: moderate
      formality: 0.3
      humor_level: 0.7
    knowledge:
      domains: ["technology", "science"]
      skills: ["programming", "problem solving"]
      interests: ["AI", "robotics"]
    backstory:
      background: A tech enthusiast with a passion for AI
      experiences: ["Worked on AI projects", "Attended tech conferences"]
      relationships: ["Close with family", "Many tech friends"]
      goals: ["Advance AI technology", "Help others learn programming"]
    """
    
    validator = PersonalityValidator()
    errors = validator.validate_json(valid_json)
    assert len(errors) == 0

def test_validate_invalid_json():
    """Test validation of invalid JSON personality definition."""
    invalid_json = """
    name: Test Personality
    version: 1.0
    traits:
      friendliness:
        name: Friendliness
        value: 1.5  # Invalid value > 1
    style:
      tone: friendly
      vocabulary_level: invalid  # Invalid vocabulary level
      formality: 0.3
      humor_level: 0.7
    knowledge:
      domains: []  # Empty domains
      skills: ["programming"]
      interests: ["AI"]
    backstory:
      background: ""  # Empty background
      experiences: []
      relationships: []
      goals: []
    """
    
    validator = PersonalityValidator()
    errors = validator.validate_json(invalid_json)
    assert len(errors) > 0

def test_validate_valid_xml():
    """Test validation of valid XML personality definition."""
    valid_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <personality>
        <name>Test Personality</name>
        <version>1.0</version>
        <traits>
            <trait id="friendliness">
                <name>Friendliness</name>
                <value>0.8</value>
                <description>Very friendly and approachable</description>
            </trait>
        </traits>
        <style>
            <tone>friendly</tone>
            <vocabulary_level>moderate</vocabulary_level>
            <formality>0.3</formality>
            <humor_level>0.7</humor_level>
        </style>
        <knowledge>
            <domains>
                <domain>technology</domain>
                <domain>science</domain>
            </domains>
            <skills>
                <skill>programming</skill>
                <skill>problem solving</skill>
            </skills>
            <interests>
                <interest>AI</interest>
                <interest>robotics</interest>
            </interests>
        </knowledge>
        <backstory>
            <background>A tech enthusiast with a passion for AI</background>
            <experiences>
                <experience>Worked on AI projects</experience>
                <experience>Attended tech conferences</experience>
            </experiences>
            <relationships>
                <relationship>Close with family</relationship>
                <relationship>Many tech friends</relationship>
            </relationships>
            <goals>
                <goal>Advance AI technology</goal>
                <goal>Help others learn programming</goal>
            </goals>
        </backstory>
    </personality>
    """
    
    validator = PersonalityValidator()
    errors = validator.validate_xml(valid_xml)
    assert len(errors) == 0

def test_validate_invalid_xml():
    """Test validation of invalid XML personality definition."""
    invalid_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <personality>
        <name>Test Personality</name>
        <version>1.0</version>
        <traits>
            <trait id="friendliness">
                <name>Friendliness</name>
                <value>1.5</value>  <!-- Invalid value > 1 -->
            </trait>
        </traits>
        <style>
            <tone>friendly</tone>
            <vocabulary_level>invalid</vocabulary_level>  <!-- Invalid vocabulary level -->
            <formality>1.5</formality>  <!-- Invalid formality -->
            <humor_level>0.7</humor_level>
        </style>
        <knowledge>
            <domains>
                <!-- Empty domains -->
            </domains>
            <skills>
                <skill>programming</skill>
            </skills>
            <interests>
                <interest>AI</interest>
            </interests>
        </knowledge>
        <backstory>
            <background></background>  <!-- Empty background -->
            <experiences>
                <!-- Empty experiences -->
            </experiences>
            <relationships>
                <!-- Empty relationships -->
            </relationships>
            <goals>
                <!-- Empty goals -->
            </goals>
        </backstory>
    </personality>
    """
    
    validator = PersonalityValidator()
    errors = validator.validate_xml(invalid_xml)
    assert len(errors) > 0

def test_validate_valid_personality():
    """Test validation of valid Personality instance."""
    personality = Personality(
        name="Test Personality",
        version="1.0",
        traits={
            "friendliness": Trait("Friendliness", 0.8, "Very friendly")
        },
        style=Style(
            tone="friendly",
            vocabulary_level="moderate",
            formality=0.3,
            humor_level=0.7
        ),
        knowledge=Knowledge(
            domains=["technology"],
            skills=["programming"],
            interests=["AI"]
        ),
        backstory=Backstory(
            background="Tech enthusiast",
            experiences=["Worked on AI"],
            relationships=["Family"],
            goals=["Learn more"]
        )
    )
    
    validator = PersonalityValidator()
    errors = validator.validate_personality(personality)
    assert len(errors) == 0

def test_validate_invalid_personality():
    """Test validation of invalid Personality instance."""
    personality = Personality(
        name="Test Personality",
        version="1.0",
        traits={
            "friendliness": Trait("Friendliness", 1.5, "Invalid value")  # Invalid value
        },
        style=Style(
            tone="friendly",
            vocabulary_level="invalid",  # Invalid vocabulary level
            formality=1.5,  # Invalid formality
            humor_level=0.7
        ),
        knowledge=Knowledge(
            domains=[],  # Empty domains
            skills=[],
            interests=[]
        ),
        backstory=Backstory(
            background="",  # Empty background
            experiences=[],
            relationships=[],
            goals=[]
        )
    )
    
    validator = PersonalityValidator()
    errors = validator.validate_personality(personality)
    assert len(errors) > 0 
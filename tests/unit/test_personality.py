"""
Unit tests for personality framework
"""
import pytest
from pathlib import Path
from lxml import etree

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


def test_xml_schema_validation(tmp_path):
    """Test XML schema validation"""
    # Create a temporary personality directory
    personality_dir = tmp_path / "personalities"
    personality_dir.mkdir()
    
    # Copy the schema file
    schema_path = personality_dir / "personality.xsd"
    with open(schema_path, "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
    <xs:element name="personality">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="traits" type="traitsType"/>
                <xs:element name="backstory" type="backstoryType"/>
                <xs:element name="knowledge" type="knowledgeType"/>
                <xs:element name="style" type="styleType"/>
            </xs:sequence>
            <xs:attribute name="name" type="xs:string" use="required"/>
            <xs:attribute name="version" type="xs:string" default="1.0"/>
        </xs:complexType>
    </xs:element>
    <xs:complexType name="traitsType">
        <xs:sequence>
            <xs:element name="trait" maxOccurs="unbounded">
                <xs:complexType>
                    <xs:simpleContent>
                        <xs:extension base="xs:string">
                            <xs:attribute name="name" type="xs:string" use="required"/>
                            <xs:attribute name="value" type="xs:decimal" use="required">
                                <xs:restriction base="xs:decimal">
                                    <xs:minInclusive value="0.0"/>
                                    <xs:maxInclusive value="1.0"/>
                                </xs:restriction>
                            </xs:attribute>
                        </xs:extension>
                    </xs:simpleContent>
                </xs:complexType>
            </xs:element>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="backstoryType">
        <xs:sequence>
            <xs:element name="background" type="xs:string"/>
            <xs:element name="experiences">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="experience" type="xs:string" maxOccurs="unbounded"/>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="relationships">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="relationship" maxOccurs="unbounded">
                            <xs:complexType>
                                <xs:simpleContent>
                                    <xs:extension base="xs:string">
                                        <xs:attribute name="type" type="xs:string" use="required"/>
                                    </xs:extension>
                                </xs:simpleContent>
                            </xs:complexType>
                        </xs:element>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="goals">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="goal" type="xs:string" maxOccurs="unbounded"/>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="knowledgeType">
        <xs:sequence>
            <xs:element name="domains">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="domain" type="xs:string" maxOccurs="unbounded"/>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="skills">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="skill" type="xs:string" maxOccurs="unbounded"/>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="interests">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="interest" type="xs:string" maxOccurs="unbounded"/>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="styleType">
        <xs:sequence>
            <xs:element name="tone" type="xs:string"/>
            <xs:element name="vocabulary_level" type="xs:string"/>
            <xs:element name="formality" type="xs:decimal">
                <xs:restriction base="xs:decimal">
                    <xs:minInclusive value="0.0"/>
                    <xs:maxInclusive value="1.0"/>
                </xs:restriction>
            </xs:element>
            <xs:element name="humor_level" type="xs:decimal">
                <xs:restriction base="xs:decimal">
                    <xs:minInclusive value="0.0"/>
                    <xs:maxInclusive value="1.0"/>
                </xs:restriction>
            </xs:element>
        </xs:sequence>
    </xs:complexType>
</xs:schema>""")
    
    # Create a loader
    loader = PersonalityLoader(personality_dir)
    
    # Test valid XML
    valid_xml = """<?xml version="1.0" encoding="UTF-8"?>
<personality name="TestPersonality" version="1.0">
    <traits>
        <trait name="test_trait" value="0.5">Test trait description</trait>
    </traits>
    <backstory>
        <background>Test background</background>
        <experiences>
            <experience>Test experience</experience>
        </experiences>
        <relationships>
            <relationship type="test">test relationship</relationship>
        </relationships>
        <goals>
            <goal>Test goal</goal>
        </goals>
    </backstory>
    <knowledge>
        <domains>
            <domain>test domain</domain>
        </domains>
        <skills>
            <skill>test skill</skill>
        </skills>
        <interests>
            <interest>test interest</interest>
        </interests>
    </knowledge>
    <style>
        <tone>test tone</tone>
        <vocabulary_level>moderate</vocabulary_level>
        <formality>0.5</formality>
        <humor_level>0.5</humor_level>
    </style>
</personality>"""
    
    xml_path = personality_dir / "test.xml"
    with open(xml_path, "w") as f:
        f.write(valid_xml)
    
    # Should not raise an exception
    personality = loader._load_from_xml(xml_path)
    assert isinstance(personality, PersonalityDefinition)
    assert personality.name == "TestPersonality"
    
    # Test invalid XML - missing required attribute
    invalid_xml1 = """<?xml version="1.0" encoding="UTF-8"?>
<personality version="1.0">
    <traits>
        <trait name="test_trait" value="0.5">Test trait description</trait>
    </traits>
    <backstory>
        <background>Test background</background>
        <experiences>
            <experience>Test experience</experience>
        </experiences>
        <relationships>
            <relationship type="test">test relationship</relationship>
        </relationships>
        <goals>
            <goal>Test goal</goal>
        </goals>
    </backstory>
    <knowledge>
        <domains>
            <domain>test domain</domain>
        </domains>
        <skills>
            <skill>test skill</skill>
        </skills>
        <interests>
            <interest>test interest</interest>
        </interests>
    </knowledge>
    <style>
        <tone>test tone</tone>
        <vocabulary_level>moderate</vocabulary_level>
        <formality>0.5</formality>
        <humor_level>0.5</humor_level>
    </style>
</personality>"""
    
    xml_path = personality_dir / "invalid1.xml"
    with open(xml_path, "w") as f:
        f.write(invalid_xml1)
    
    # Should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        loader._load_from_xml(xml_path)
    assert "Invalid personality definition" in str(exc_info.value)
    
    # Test invalid XML - invalid trait value
    invalid_xml2 = """<?xml version="1.0" encoding="UTF-8"?>
<personality name="TestPersonality" version="1.0">
    <traits>
        <trait name="test_trait" value="1.5">Test trait description</trait>
    </traits>
    <backstory>
        <background>Test background</background>
        <experiences>
            <experience>Test experience</experience>
        </experiences>
        <relationships>
            <relationship type="test">test relationship</relationship>
        </relationships>
        <goals>
            <goal>Test goal</goal>
        </goals>
    </backstory>
    <knowledge>
        <domains>
            <domain>test domain</domain>
        </domains>
        <skills>
            <skill>test skill</skill>
        </skills>
        <interests>
            <interest>test interest</interest>
        </interests>
    </knowledge>
    <style>
        <tone>test tone</tone>
        <vocabulary_level>moderate</vocabulary_level>
        <formality>0.5</formality>
        <humor_level>0.5</humor_level>
    </style>
</personality>"""
    
    xml_path = personality_dir / "invalid2.xml"
    with open(xml_path, "w") as f:
        f.write(invalid_xml2)
    
    # Should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        loader._load_from_xml(xml_path)
    assert "Invalid personality definition" in str(exc_info.value) 
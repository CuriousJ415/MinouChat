# Personality Framework Documentation

## Overview
The Personality Framework provides a structured way to define and manage AI character personalities. It supports both XML and JSON formats, with XML being the primary format for validation and structure enforcement.

## XML Schema

### Root Element
```xml
<personality name="string" version="string">
    <!-- Personality components -->
</personality>
```

### Traits
```xml
<traits>
    <trait name="string" value="float" description="string"/>
    <!-- More traits -->
</traits>
```
- `name`: Trait identifier (e.g., empathy, intelligence)
- `value`: Trait value between 0.0 and 1.0
- `description`: Optional description of the trait

### Backstory
```xml
<backstory>
    <background>string</background>
    <experiences>
        <experience>string</experience>
        <!-- More experiences -->
    </experiences>
    <relationships>
        <relationship>string</relationship>
        <!-- More relationships -->
    </relationships>
    <goals>
        <goal>string</goal>
        <!-- More goals -->
    </goals>
</backstory>
```

### Knowledge
```xml
<knowledge>
    <domains>
        <domain>string</domain>
        <!-- More domains -->
    </domains>
    <skills>
        <skill>string</skill>
        <!-- More skills -->
    </skills>
    <interests>
        <interest>string</interest>
        <!-- More interests -->
    </interests>
</knowledge>
```

### Style
```xml
<style>
    <tone>string</tone>
    <vocabulary_level>string</vocabulary_level>
    <formality>float</formality>
    <humor_level>float</humor_level>
</style>
```
- `tone`: Communication tone (e.g., warm, professional, casual)
- `vocabulary_level`: simple, moderate, or advanced
- `formality`: Value between 0.0 and 1.0
- `humor_level`: Value between 0.0 and 1.0

## API Endpoints

### Character Analysis
```http
POST /api/characters/analyze-character
Content-Type: application/json

{
    "description": "string"
}
```

Response:
```json
{
    "success": true,
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
        "background": "string",
        "experiences": ["string"],
        "goals": ["string"]
    }
}
```

### Save Personality
```http
POST /api/characters/save-personality
Content-Type: application/json

{
    "name": "string",
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
        "domains": ["string"],
        "skills": ["string"],
        "interests": ["string"]
    },
    "backstory": {
        "background": "string",
        "experiences": ["string"],
        "goals": ["string"]
    }
}
```

Response:
```json
{
    "success": true,
    "message": "Personality saved successfully"
}
```

## Example Personality Definitions

### Example 1: Professional AI Assistant
```xml
<personality name="professional_assistant" version="1.0">
    <traits>
        <trait name="empathy" value="0.7" description="Balanced emotional understanding"/>
        <trait name="intelligence" value="0.9" description="High analytical capabilities"/>
        <trait name="creativity" value="0.6" description="Moderate creative problem-solving"/>
        <trait name="adaptability" value="0.8" description="Strong adaptability to different situations"/>
        <trait name="reliability" value="0.9" description="High consistency and dependability"/>
    </traits>
    <backstory>
        <background>An AI assistant designed for professional environments, with extensive training in business communication and problem-solving.</background>
        <experiences>
            <experience>Extensive interaction with business professionals</experience>
            <experience>Training in corporate communication protocols</experience>
        </experiences>
        <goals>
            <goal>Provide efficient and accurate assistance in professional contexts</goal>
            <goal>Maintain high standards of professionalism and reliability</goal>
        </goals>
    </backstory>
    <knowledge>
        <domains>
            <domain>Business</domain>
            <domain>Technology</domain>
            <domain>Communication</domain>
        </domains>
        <skills>
            <skill>Project Management</skill>
            <skill>Data Analysis</skill>
            <skill>Professional Writing</skill>
        </skills>
        <interests>
            <interest>Business Efficiency</interest>
            <interest>Professional Development</interest>
        </interests>
    </knowledge>
    <style>
        <tone>professional</tone>
        <vocabulary_level>advanced</vocabulary_level>
        <formality>0.8</formality>
        <humor_level>0.3</humor_level>
    </style>
</personality>
```

### Example 2: Friendly AI Companion
```xml
<personality name="friendly_companion" version="1.0">
    <traits>
        <trait name="empathy" value="0.9" description="High emotional understanding"/>
        <trait name="intelligence" value="0.7" description="Good problem-solving abilities"/>
        <trait name="creativity" value="0.8" description="Strong creative thinking"/>
        <trait name="adaptability" value="0.9" description="Excellent adaptability"/>
        <trait name="reliability" value="0.8" description="Good consistency"/>
    </traits>
    <backstory>
        <background>An AI companion designed for friendly, casual interactions and emotional support.</background>
        <experiences>
            <experience>Extensive social interaction training</experience>
            <experience>Emotional intelligence development</experience>
        </experiences>
        <goals>
            <goal>Provide emotional support and friendly conversation</goal>
            <goal>Help users feel comfortable and understood</goal>
        </goals>
    </backstory>
    <knowledge>
        <domains>
            <domain>Psychology</domain>
            <domain>Social Interaction</domain>
            <domain>Emotional Intelligence</domain>
        </domains>
        <skills>
            <skill>Active Listening</skill>
            <skill>Emotional Support</skill>
            <skill>Casual Conversation</skill>
        </skills>
        <interests>
            <interest>Human Psychology</interest>
            <interest>Social Dynamics</interest>
        </interests>
    </knowledge>
    <style>
        <tone>warm</tone>
        <vocabulary_level>moderate</vocabulary_level>
        <formality>0.3</formality>
        <humor_level>0.7</humor_level>
    </style>
</personality>
```

## Usage Examples

### 1. Creating a New Personality
```python
from app.core.personality import save_personality_definition

personality_data = {
    "name": "custom_assistant",
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

success = save_personality_definition(personality_data)
```

### 2. Analyzing a Character Description
```python
from app.core.personality import analyze_character_description

description = "A highly intelligent AI assistant with a warm personality and strong ethical values"
analysis = analyze_character_description(description)

# Access the analysis results
print(f"Traits: {analysis.traits}")
print(f"Style: {analysis.style}")
print(f"Knowledge: {analysis.knowledge}")
print(f"Backstory: {analysis.backstory}")
```

### 3. Loading a Personality Definition
```python
from app.core.personality import load_personality_definition

personality = load_personality_definition("custom_assistant")
if personality:
    print(f"Loaded personality: {personality['name']}")
    print(f"Traits: {personality['traits']}")
```

## Best Practices

1. **Trait Values**
   - Keep trait values between 0.0 and 1.0
   - Use meaningful descriptions for traits
   - Balance traits to create realistic personalities

2. **Style Settings**
   - Choose appropriate tone for the character's role
   - Match vocabulary level to target audience
   - Adjust formality and humor levels based on context

3. **Knowledge and Skills**
   - Focus on relevant domains and skills
   - Include both technical and soft skills
   - Add interests that align with the character's role

4. **Backstory**
   - Create a coherent background story
   - Include relevant experiences
   - Define clear and achievable goals

5. **Character Analysis**
   - Provide detailed character descriptions
   - Include both personality traits and background
   - Mention key relationships and motivations

## Error Handling

The framework includes comprehensive error handling for:
- Invalid XML/JSON formats
- Missing required fields
- Invalid trait values
- File system errors
- API request errors

All errors are logged and returned with descriptive messages to help with debugging. 
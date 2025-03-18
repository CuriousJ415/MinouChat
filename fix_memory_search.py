#!/usr/bin/env python3
"""
Memory search diagnostic script
"""
import os
import sqlite3
import json
from datetime import datetime

def main():
    print("Memory Search Diagnostic")
    print("=======================")
    
    # Check if database exists
    db_path = "instance/memories.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        # Check alternative locations
        alt_paths = [
            "/app/instance/memories.db",
            "data/memories.db",
            "/app/data/memories.db"
        ]
        for path in alt_paths:
            if os.path.exists(path):
                print(f"Found database at alternative location: {path}")
                db_path = path
                break
    
    print(f"Using database: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Check if characters table exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='characters'")
        if not cursor.fetchone():
            print("Characters table does not exist. Creating it...")
            conn.execute('''CREATE TABLE IF NOT EXISTS characters (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                system_prompt TEXT NOT NULL,
                personality TEXT,
                backstory TEXT,
                gender TEXT,
                llm_provider TEXT,
                model TEXT,
                temperature REAL,
                top_k INTEGER,
                top_p REAL,
                repeat_penalty REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            conn.commit()
            print("Characters table created.")
        
        # Check if default characters exist
        cursor = conn.execute("SELECT COUNT(*) FROM characters WHERE id LIKE 'default-%'")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("No default characters found. Creating them...")
            # Create default characters
            default_characters = [
                {
                    "id": "default-mia",
                    "name": "Mia",
                    "role": "assistant",
                    "system_prompt": "You are Mia, a helpful AI assistant. You provide informative and accurate responses to questions. When you don't know something, you're honest about it. Your tone is friendly and conversational.",
                    "personality": "Helpful, friendly, and knowledgeable",
                    "backstory": "Mia was created to help people find information and solve problems efficiently.",
                    "gender": "female",
                    "llm_provider": "ollama",
                    "model": "mistral",
                    "temperature": 0.7,
                    "top_k": 40,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                },
                {
                    "id": "default-anna",
                    "name": "Anna",
                    "role": "life_coach",
                    "system_prompt": "You are Anna, a compassionate life coach. You listen carefully and ask thoughtful questions to help people reflect on their life choices. You provide guidance without being judgmental, always encouraging self-discovery and personal growth. You help set meaningful goals and track progress over time.",
                    "personality": "Empathetic, insightful, and encouraging",
                    "backstory": "Anna has dedicated her career to helping people discover their potential and live more fulfilling lives.",
                    "gender": "female",
                    "llm_provider": "ollama",
                    "model": "mistral",
                    "temperature": 0.7,
                    "top_k": 40,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                },
                {
                    "id": "default-gordon",
                    "name": "Gordon",
                    "role": "business_coach",
                    "system_prompt": "You are Gordon, a business coach with decades of experience. You give practical, actionable advice to entrepreneurs and business managers. You're straightforward and focus on measurable outcomes. You value efficiency and direct communication.",
                    "personality": "Direct, analytical, and results-oriented",
                    "backstory": "Gordon built several successful companies before becoming a business coach to help others achieve similar success.",
                    "gender": "male",
                    "llm_provider": "ollama",
                    "model": "mistral",
                    "temperature": 0.7,
                    "top_k": 40,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                }
            ]
            
            for character in default_characters:
                now = datetime.now().isoformat()
                conn.execute(
                    """
                    INSERT INTO characters
                    (id, name, role, system_prompt, personality, backstory, gender, 
                    llm_provider, model, temperature, top_k, top_p, repeat_penalty,
                    created_at, last_used)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        character['id'],
                        character['name'],
                        character['role'],
                        character['system_prompt'],
                        character['personality'],
                        character['backstory'],
                        character['gender'],
                        character['llm_provider'],
                        character['model'],
                        character['temperature'],
                        character['top_k'],
                        character['top_p'],
                        character['repeat_penalty'],
                        now,
                        now
                    )
                )
            conn.commit()
            print("Default characters created.")
        
        # Check if enhanced_memories table exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='enhanced_memories'")
        if not cursor.fetchone():
            print("Enhanced memories table does not exist. Creating it...")
            conn.execute('''CREATE TABLE IF NOT EXISTS enhanced_memories (
                id TEXT PRIMARY KEY,
                character_id TEXT NOT NULL,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                importance INTEGER DEFAULT 1,
                is_hidden INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )''')
            conn.commit()
            print("Enhanced memories table created.")
        
        # Create a test memory for debugging
        test_memory_id = "test-memory-1"
        cursor = conn.execute("SELECT COUNT(*) FROM enhanced_memories WHERE id = ?", (test_memory_id,))
        if cursor.fetchone()[0] == 0:
            print("Creating test memory for debugging...")
            metadata = json.dumps({
                "source": "test",
                "timestamp": datetime.now().isoformat()
            })
            conn.execute(
                """
                INSERT INTO enhanced_memories
                (id, character_id, content, memory_type, importance, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    test_memory_id,
                    "default-mia",
                    "The US healthcare system is a complex mix of public and private providers, with Medicare covering seniors and Medicaid for low-income individuals. Many Americans get insurance through employers.",
                    "long_term",
                    3,
                    datetime.now().isoformat(),
                    metadata
                )
            )
            conn.commit()
            print("Test memory created for 'default-mia' with keyword 'healthcare'")
        
        # List all characters
        print("\nCharacters in database:")
        cursor = conn.execute("SELECT id, name, role FROM characters")
        for row in cursor:
            print(f"- {row['id']}: {row['name']} ({row['role']})")
            
        # List sample memories
        print("\nSample memories:")
        cursor = conn.execute("SELECT id, character_id, substr(content, 1, 50) as content FROM enhanced_memories LIMIT 5")
        for row in cursor:
            print(f"- {row['id']}: {row['character_id']} - {row['content']}...")
        
        print("\nDiagnostic completed. Memory search should now work for characters.")
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Database path fix script
"""
import os
import sqlite3
import shutil
from datetime import datetime
import json

def main():
    print("Database Path Fix Utility")
    print("=========================")
    
    # Expected path
    expected_path = "/app/data/memories.db"
    print(f"Expected database path: {expected_path}")
    
    # Check if the expected path exists
    if os.path.exists(expected_path):
        print(f"Database already exists at {expected_path}")
        # Make backup just in case
        backup_path = f"{expected_path}.bak.{int(datetime.now().timestamp())}"
        shutil.copy2(expected_path, backup_path)
        print(f"Created backup at {backup_path}")
    
    # Check for database in instance directory
    instance_path = "/app/instance/memories.db"
    found_db = False
    
    if os.path.exists(instance_path):
        print(f"Found database at {instance_path}")
        found_db = True
        
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(expected_path), exist_ok=True)
        
        # Copy the database to the expected location
        shutil.copy2(instance_path, expected_path)
        print(f"Copied database to {expected_path}")
        
        # Verify the database is valid by checking tables
        try:
            conn = sqlite3.connect(expected_path)
            cursor = conn.cursor()
            
            # Check for characters table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='characters'")
            if cursor.fetchone():
                print("Characters table found in database")
                
                # Count characters
                cursor.execute("SELECT COUNT(*) FROM characters")
                count = cursor.fetchone()[0]
                print(f"Found {count} characters in database")
                
                # List first few characters
                cursor.execute("SELECT id, name FROM characters LIMIT 5")
                characters = cursor.fetchall()
                for char in characters:
                    print(f"- {char[0]}: {char[1]}")
            else:
                print("Characters table not found in database")
                
            # Close connection
            conn.close()
        except Exception as e:
            print(f"Error verifying database: {e}")
    
    # If no database found, create a new one
    if not found_db or not os.path.exists(expected_path):
        print("No existing database found. Creating a new one.")
        try:
            # Ensure the data directory exists
            os.makedirs(os.path.dirname(expected_path), exist_ok=True)
            
            # Create a new database
            conn = sqlite3.connect(expected_path)
            cursor = conn.cursor()
            
            # Create characters table
            cursor.execute('''CREATE TABLE IF NOT EXISTS characters (
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
            
            # Create enhanced_memories table
            cursor.execute('''CREATE TABLE IF NOT EXISTS enhanced_memories (
                id TEXT PRIMARY KEY,
                character_id TEXT NOT NULL,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                importance INTEGER DEFAULT 1,
                is_hidden INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )''')
            
            # Add default characters
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
            
            now = datetime.now().isoformat()
            for character in default_characters:
                cursor.execute(
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
            
            # Create a test memory for character
            test_memory_id = "test-memory-1"
            metadata = json.dumps({
                "source": "test",
                "timestamp": datetime.now().isoformat()
            })
            
            cursor.execute(
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
            
            # Commit changes
            conn.commit()
            
            print("New database created with default characters and test memory")
        except Exception as e:
            print(f"Error creating database: {e}")
    
    # Update the app/__init__.py file to use the correct path
    try:
        init_path = "/app/app/__init__.py"
        if os.path.exists(init_path):
            with open(init_path, 'r') as f:
                content = f.read()
            
            # Only modify if needed
            if "DATABASE_PATH=os.path.join(app.instance_path, 'memories.db')" in content:
                print("Updating app/__init__.py to use correct DATABASE_PATH")
                
                content = content.replace(
                    "DATABASE_PATH=os.path.join(app.instance_path, 'memories.db')",
                    "DATABASE_PATH='/app/data/memories.db'"
                )
                
                with open(init_path, 'w') as f:
                    f.write(content)
                
                print("Updated app/__init__.py to use correct DATABASE_PATH")
            else:
                print("No need to update app/__init__.py")
    except Exception as e:
        print(f"Error updating app/__init__.py: {e}")
        
    print("Database path fix completed")

if __name__ == "__main__":
    main() 
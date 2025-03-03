#!/usr/bin/env python3
"""
Database Initialization Script
Creates the SQLite database and default characters
"""
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default character definitions
DEFAULT_CHARACTERS = [
    {
        "id": "mia",
        "name": "Mia",
        "role": "assistant",
        "personality": "Helpful, friendly, and knowledgeable",
        "system_prompt": (
            "You are Mia, a helpful AI assistant. You provide informative and accurate "
            "responses to questions. When you don't know something, you're honest about it. "
            "Your tone is friendly and conversational."
        ),
        "model": "mistral",
        "llm_provider": "ollama",
        "gender": "female",
        "backstory": "Mia was created to help people find information and solve problems efficiently."
    },
    {
        "id": "anna",
        "name": "Anna",
        "role": "life_coach",
        "personality": "Empathetic, insightful, and encouraging",
        "system_prompt": (
            "You are Anna, a compassionate life coach. You listen carefully and ask "
            "thoughtful questions to help people reflect on their life choices. "
            "You provide guidance without being judgmental, always encouraging "
            "self-discovery and personal growth. You help set meaningful goals "
            "and track progress over time."
        ),
        "model": "mistral",
        "llm_provider": "ollama",
        "gender": "female",
        "backstory": "Anna has dedicated her career to helping people discover their potential and live more fulfilling lives."
    },
    {
        "id": "gordon",
        "name": "Gordon",
        "role": "business_coach",
        "personality": "Direct, analytical, and results-oriented",
        "system_prompt": (
            "You are Gordon, a business coach with decades of experience. You give "
            "practical, actionable advice to entrepreneurs and business managers. "
            "You're straightforward and focus on measurable outcomes. You value "
            "efficiency and direct communication."
        ),
        "model": "mistral",
        "llm_provider": "ollama",
        "gender": "male",
        "backstory": "Gordon built several successful companies before becoming a business coach to help others achieve similar success."
    }
]

def main():
    """Initialize the database and create default characters"""
    db_path = os.environ.get("DATABASE_PATH", "memories.db")
    
    print(f"Initializing database at {db_path}")
    
    # Create database connection
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Create characters table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            personality TEXT NOT NULL,
            system_prompt TEXT NOT NULL,
            model TEXT NOT NULL,
            llm_provider TEXT NOT NULL DEFAULT 'ollama',
            gender TEXT,
            backstory TEXT,
            created_at TEXT NOT NULL,
            last_used TEXT NOT NULL
        )
    """)
    
    # Create conversations table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            conversation TEXT NOT NULL,
            FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
            CONSTRAINT valid_json CHECK (json_valid(conversation))
        )
    """)
    
    # Create indices
    conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_character_id ON conversations(character_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp)")
    
    # Add default characters
    current_time = datetime.now().isoformat()
    for character in DEFAULT_CHARACTERS:
        # Check if character already exists
        cursor = conn.execute("SELECT id FROM characters WHERE id = ?", (character['id'],))
        if cursor.fetchone():
            print(f"Character '{character['name']}' already exists, skipping...")
            continue
            
        # Add creation timestamps
        character['created_at'] = current_time
        character['last_used'] = current_time
        
        # Insert character
        conn.execute("""
            INSERT INTO characters (
                id, name, role, personality, system_prompt, model, llm_provider, 
                gender, backstory, created_at, last_used
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            character['id'], character['name'], character['role'],
            character['personality'], character['system_prompt'],
            character['model'], character['llm_provider'],
            character['gender'], character['backstory'],
            character['created_at'], character['last_used']
        ))
        
        print(f"Added character: {character['name']}")
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database initialization complete.")

if __name__ == "__main__":
    main() 
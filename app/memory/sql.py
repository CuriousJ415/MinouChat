"""
SQL Memory System
Handles conversation storage and character data in SQL database
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Union
from contextlib import contextmanager
from flask import current_app

def init_db(app):
    """
    Initialize the database with necessary tables
    
    Args:
        app: Flask application context
    """
    with _db_conn(app.config['DATABASE_PATH']) as conn:
        # Characters table
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
        
        # Check if llm_provider column exists, add it if it doesn't
        cursor = conn.execute("PRAGMA table_info(characters)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'llm_provider' not in columns:
            conn.execute("ALTER TABLE characters ADD COLUMN llm_provider TEXT NOT NULL DEFAULT 'ollama'")
        
        # Conversations table
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
        
        # Create index for faster queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_character_id ON conversations(character_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp)")

    # Create default characters if they don't exist
    from app.core.character import _create_default_characters
    
    with app.app_context():
        # Check if characters already exist
        characters_exist = False
        with _db_conn(app.config['DATABASE_PATH']) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM characters")
            count = cursor.fetchone()[0]
            characters_exist = count > 0
            
        # Only create default characters if none exist
        if not characters_exist:
            _create_default_characters()

@contextmanager
def _db_conn(db_path=None):
    """
    Context manager for database connections
    
    Args:
        db_path: Path to database file, uses app config if None
        
    Yields:
        SQLite connection object
    """
    if db_path is None:
        db_path = current_app.config['DATABASE_PATH']
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Database error: {str(e)}")
        raise
    finally:
        conn.close()

def get_all_characters() -> List[Dict]:
    """
    Get all characters from database
    
    Returns:
        List of character dictionaries
    """
    with _db_conn() as conn:
        cursor = conn.execute("SELECT * FROM characters ORDER BY last_used DESC")
        return [dict(row) for row in cursor.fetchall()]

def get_character_by_id(character_id: str) -> Optional[Dict]:
    """
    Get character by ID
    
    Args:
        character_id: Character's unique identifier
        
    Returns:
        Character dictionary or None if not found
    """
    with _db_conn() as conn:
        cursor = conn.execute("SELECT * FROM characters WHERE id = ?", (character_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def add_character(character_data: Dict) -> Dict:
    """
    Add a new character to database
    
    Args:
        character_data: Character dictionary
        
    Returns:
        Saved character dictionary
        
    Raises:
        ValueError: If character ID already exists
    """
    with _db_conn() as conn:
        # Check if character already exists
        cursor = conn.execute("SELECT id FROM characters WHERE id = ?", (character_data['id'],))
        if cursor.fetchone():
            raise ValueError(f"Character with ID '{character_data['id']}' already exists")
        
        # Insert character
        fields = ", ".join(character_data.keys())
        placeholders = ", ".join(["?"] * len(character_data))
        values = tuple(character_data.values())
        
        conn.execute(f"INSERT INTO characters ({fields}) VALUES ({placeholders})", values)
        
        return character_data

def update_character_by_id(character_id: str, character_data: Dict) -> Dict:
    """
    Update an existing character
    
    Args:
        character_id: Character's unique identifier
        character_data: Updated character data
        
    Returns:
        Updated character dictionary
        
    Raises:
        ValueError: If character not found
    """
    with _db_conn() as conn:
        # Check if character exists
        cursor = conn.execute("SELECT id FROM characters WHERE id = ?", (character_id,))
        if not cursor.fetchone():
            raise ValueError(f"Character with ID '{character_id}' not found")
        
        # Update character
        updates = ", ".join([f"{key} = ?" for key in character_data.keys()])
        values = tuple(character_data.values()) + (character_id,)
        
        conn.execute(f"UPDATE characters SET {updates} WHERE id = ?", values)
        
        return character_data

def update_character_last_used(character_id: str) -> bool:
    """
    Update character's last_used timestamp
    
    Args:
        character_id: Character's unique identifier
        
    Returns:
        True if successful, False if character not found
    """
    with _db_conn() as conn:
        # Check if character exists
        cursor = conn.execute("SELECT id FROM characters WHERE id = ?", (character_id,))
        if not cursor.fetchone():
            return False
        
        # Update timestamp
        conn.execute(
            "UPDATE characters SET last_used = ? WHERE id = ?",
            (datetime.now().isoformat(), character_id)
        )
        
        return True

def delete_character_by_id(character_id: str) -> bool:
    """
    Delete a character and all associated conversations
    
    Args:
        character_id: Character's unique identifier
        
    Returns:
        True if successful, False if character not found
    """
    with _db_conn() as conn:
        # Check if character exists
        cursor = conn.execute("SELECT id FROM characters WHERE id = ?", (character_id,))
        if not cursor.fetchone():
            return False
        
        # Delete character (will cascade to conversations)
        conn.execute("DELETE FROM characters WHERE id = ?", (character_id,))
        
        return True

def clear_character_memory(character_id: str) -> bool:
    """
    Clear all conversations for a character
    
    Args:
        character_id: Character's unique identifier
        
    Returns:
        True if successful, False if character not found
    """
    with _db_conn() as conn:
        # Check if character exists
        cursor = conn.execute("SELECT id FROM characters WHERE id = ?", (character_id,))
        if not cursor.fetchone():
            return False
        
        # Delete conversations
        conn.execute("DELETE FROM conversations WHERE character_id = ?", (character_id,))
        
        return True

def save_conversation(character_id: str, messages: List[Dict]) -> bool:
    """
    Save a conversation with a character
    
    Args:
        character_id: Character's unique identifier
        messages: List of message dictionaries
        
    Returns:
        True if successful, False if character not found
    """
    with _db_conn() as conn:
        # Check if character exists
        cursor = conn.execute("SELECT id FROM characters WHERE id = ?", (character_id,))
        if not cursor.fetchone():
            return False
        
        # Save conversation
        timestamp = datetime.now().isoformat()
        conn.execute(
            "INSERT INTO conversations (character_id, timestamp, conversation) VALUES (?, ?, ?)",
            (character_id, timestamp, json.dumps(messages))
        )
        
        return True

def get_recent_conversations(character_id: str, limit: int = 10, offset: int = 0) -> List[Dict]:
    """
    Get recent conversations with a character
    
    Args:
        character_id: Character's unique identifier
        limit: Maximum number of conversations to retrieve
        offset: Offset for pagination
        
    Returns:
        List of conversation dictionaries
    """
    with _db_conn() as conn:
        cursor = conn.execute(
            """
            SELECT id, timestamp, conversation 
            FROM conversations 
            WHERE character_id = ? 
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """, 
            (character_id, limit, offset)
        )
        
        conversations = []
        for row in cursor:
            conversation_dict = dict(row)
            # Parse conversation JSON
            conversation_dict['messages'] = json.loads(conversation_dict['conversation'])
            del conversation_dict['conversation']  # Remove raw JSON
            conversations.append(conversation_dict)
            
        return conversations 
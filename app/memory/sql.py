"""
SQL Memory System
Handles conversation storage and character data in SQL database
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Union
from contextlib import contextmanager
from flask import current_app, g
import os
import logging

# Feature flags
HAS_ENHANCED_MEMORY = False  # Set to True when enhanced memory features are implemented

@contextmanager
def _db_conn(db_path):
    """Context manager for database connections outside of Flask request context"""
    conn = None
    try:
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def get_db():
    """Get the database connection"""
    if 'db' not in g:
        # Ensure the data directory exists
        db_path = current_app.config['DATABASE']
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db

def close_db(e=None):
    """Close the database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize the database"""
    db = get_db()
    
    try:
        # Create users table for authentication
        db.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )''')

        # Create user_sessions table for session management
        db.execute('''CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )''')

        # Create characters table
        db.execute('''CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            personality TEXT NOT NULL,
            system_prompt TEXT NOT NULL,
            model TEXT NOT NULL DEFAULT 'mistral',
            llm_provider TEXT NOT NULL DEFAULT 'ollama',
            gender TEXT DEFAULT '',
            backstory TEXT DEFAULT '',
            temperature REAL NOT NULL DEFAULT 0.7,
            top_p REAL NOT NULL DEFAULT 0.9,
            repeat_penalty REAL NOT NULL DEFAULT 1.1,
            top_k INTEGER DEFAULT 40,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_used DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

        # Create memories table
        db.execute('''CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (character_id) REFERENCES characters (id)
        )''')

        # Create conversations table
        db.execute('''CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (character_id) REFERENCES characters (id)
        )''')

        db.commit()
        current_app.logger.info("Database initialized successfully")
    except Exception as e:
        current_app.logger.error(f"Error initializing database: {str(e)}")
        raise

def get_all_characters() -> List[Dict]:
    """
    Get all characters from database
    
    Returns:
        List of character dictionaries
    """
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM characters ORDER BY name')
    rows = cursor.fetchall()
    
    characters = []
    for row in rows:
        char_dict = {}
        for key in row.keys():
            char_dict[key] = row[key]
        characters.append(char_dict)
    
    return characters

def get_character_by_id(character_id: str) -> Optional[Dict]:
    """
    Get character by ID
    
    Args:
        character_id: Character's unique identifier
        
    Returns:
        Character dictionary or None if not found
    """
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM characters WHERE id = ?', (character_id,))
    row = cursor.fetchone()
    
    if row:
        char_dict = {}
        for key in row.keys():
            char_dict[key] = row[key]
        return char_dict
    return None

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
    db = get_db()
    cursor = db.cursor()
    
    # Get all column names from the characters table
    cursor.execute('PRAGMA table_info(characters)')
    columns = [row[1] for row in cursor.fetchall()]
    
    # Build the SQL query dynamically
    fields = []
    values = []
    params = []
    
    for col in columns:
        if col in character_data:
            fields.append(col)
            values.append('?')
            params.append(character_data[col])
    
    query = f'''
        INSERT INTO characters (
            {', '.join(fields)}
        ) VALUES (
            {', '.join(values)}
        )
    '''
    
    try:
        cursor.execute(query, params)
        db.commit()
        return get_character_by_id(character_data['id'])
    except Exception as e:
        current_app.logger.error(f"Error adding character: {str(e)}")
        db.rollback()
        raise

def update_character_by_id(character_id: str, character_data: Dict) -> Optional[Dict]:
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
    db = get_db()
    cursor = db.cursor()
    
    try:
        # First get the existing character data
        existing = get_character_by_id(character_id)
        if not existing:
            raise ValueError(f"Character {character_id} not found")
        
        # Merge existing data with updates, preserving required fields
        merged_data = existing.copy()
        
        # Only update fields that are provided and not empty
        for field, value in character_data.items():
            if value is not None and value != '':
                merged_data[field] = value
        
        # Ensure required fields are present and not empty
        required_fields = ['name', 'role', 'personality', 'system_prompt', 'model', 'llm_provider']
        for field in required_fields:
            if field not in merged_data or not merged_data[field]:
                raise ValueError(f"Required field '{field}' cannot be empty when updating character.")

        # Debug: print merged_data before update
        print(f"[DEBUG] merged_data before update: {merged_data}")
        current_app.logger.error(f"[DEBUG] merged_data before update: {merged_data}")

        cursor.execute('''
            UPDATE characters 
            SET name = ?, role = ?, personality = ?, system_prompt = ?,
                model = ?, llm_provider = ?, gender = ?, backstory = ?,
                temperature = ?, top_p = ?, repeat_penalty = ?, top_k = ?,
                last_used = ?
            WHERE id = ?
        ''', (
            merged_data['name'],
            merged_data['role'],
            merged_data['personality'],
            merged_data['system_prompt'],
            merged_data['model'],
            merged_data['llm_provider'],
            merged_data.get('gender', ''),
            merged_data.get('backstory', ''),
            merged_data.get('temperature', 0.7),
            merged_data.get('top_p', 0.9),
            merged_data.get('repeat_penalty', 1.1),
            merged_data.get('top_k', 40),
            datetime.now().isoformat(),
            character_id
        ))
        
        db.commit()
        return get_character_by_id(character_id)
    except Exception as e:
        current_app.logger.error(f"Error updating character {character_id}: {str(e)}")
        db.rollback()
        raise

def update_character_last_used(character_id: str) -> bool:
    """
    Update character's last_used timestamp
    
    Args:
        character_id: Character's unique identifier
        
    Returns:
        True if successful, False if character not found
    """
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        UPDATE characters 
        SET last_used = ?
        WHERE id = ?
    ''', (
        datetime.now().isoformat(),
        character_id
    ))
    
    db.commit()
    return cursor.rowcount > 0

def delete_character_by_id(character_id: str) -> bool:
    """
    Delete a character and all associated conversations
    
    Args:
        character_id: Character's unique identifier
        
    Returns:
        True if successful, False if character not found
    """
    db = get_db()
    cursor = db.cursor()
    
    try:
        # First delete related memories and chat history
        cursor.execute('DELETE FROM memories WHERE character_id = ?', (character_id,))
        
        # Leave enhanced_memories intact
        # We only clear the conversation history, not the long-term memories
        # This ensures that important information is preserved even when 
        # conversation history is cleared

        
        # Then delete the character
        cursor.execute('DELETE FROM characters WHERE id = ?', (character_id,))
        
        db.commit()
        return True
    except:
        db.rollback()
        return False

# User Authentication Functions
def create_user(username: str, email: str, password_hash: str) -> Optional[Dict]:
    """
    Create a new user
    
    Args:
        username: Username for the user
        email: Email address for the user
        password_hash: Hashed password
        
    Returns:
        User dictionary or None if creation failed
    """
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        ''', (username, email, password_hash))
        db.commit()
        
        # Return the created user
        user_id = cursor.lastrowid
        return get_user_by_id(user_id)
    except sqlite3.IntegrityError:
        # Username or email already exists
        return None
    except Exception as e:
        current_app.logger.error(f"Error creating user: {str(e)}")
        return None

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """
    Get user by ID
    
    Args:
        user_id: User's unique identifier
        
    Returns:
        User dictionary or None if not found
    """
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    
    if row:
        user_dict = {}
        for key in row.keys():
            user_dict[key] = row[key]
        return user_dict
    return None

def get_user_by_username(username: str) -> Optional[Dict]:
    """
    Get user by username
    
    Args:
        username: Username to search for
        
    Returns:
        User dictionary or None if not found
    """
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()
    
    if row:
        user_dict = {}
        for key in row.keys():
            user_dict[key] = row[key]
        return user_dict
    return None

def get_user_by_email(email: str) -> Optional[Dict]:
    """
    Get user by email
    
    Args:
        email: Email address to search for
        
    Returns:
        User dictionary or None if not found
    """
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    row = cursor.fetchone()
    
    if row:
        user_dict = {}
        for key in row.keys():
            user_dict[key] = row[key]
        return user_dict
    return None

def update_user_last_login(user_id: int) -> bool:
    """
    Update user's last login timestamp
    
    Args:
        user_id: User's unique identifier
        
    Returns:
        True if successful, False otherwise
    """
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute('''
            UPDATE users 
            SET last_login = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (user_id,))
        db.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Error updating user last login: {str(e)}")
        return False

def create_user_session(user_id: int, session_token: str, expires_at: str) -> bool:
    """
    Create a new user session
    
    Args:
        user_id: User's unique identifier
        session_token: Unique session token
        expires_at: Expiration timestamp
        
    Returns:
        True if successful, False otherwise
    """
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO user_sessions (user_id, session_token, expires_at)
            VALUES (?, ?, ?)
        ''', (user_id, session_token, expires_at))
        db.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Error creating user session: {str(e)}")
        return False

def get_user_session(session_token: str) -> Optional[Dict]:
    """
    Get user session by token
    
    Args:
        session_token: Session token to search for
        
    Returns:
        Session dictionary or None if not found or expired
    """
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        SELECT * FROM user_sessions 
        WHERE session_token = ? AND expires_at > CURRENT_TIMESTAMP
    ''', (session_token,))
    row = cursor.fetchone()
    
    if row:
        session_dict = {}
        for key in row.keys():
            session_dict[key] = row[key]
        return session_dict
    return None

def delete_user_session(session_token: str) -> bool:
    """
    Delete a user session
    
    Args:
        session_token: Session token to delete
        
    Returns:
        True if successful, False otherwise
    """
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute('DELETE FROM user_sessions WHERE session_token = ?', (session_token,))
        db.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Error deleting user session: {str(e)}")
        return False

def cleanup_expired_sessions() -> bool:
    """
    Clean up expired user sessions
    
    Returns:
        True if successful, False otherwise
    """
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute('DELETE FROM user_sessions WHERE expires_at <= CURRENT_TIMESTAMP')
        db.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Error cleaning up expired sessions: {str(e)}")
        return False

def clear_character_memory(character_id: str) -> bool:
    """
    Clear all conversation history for a character
    
    Args:
        character_id: Character's unique identifier
        
    Returns:
        Success status
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Delete from conversations table
        cursor.execute('DELETE FROM conversations WHERE character_id = ?', (character_id,))
        
        # Delete from memories table if it exists
        cursor.execute('DELETE FROM memories WHERE character_id = ?', (character_id,))
        
        db.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Error clearing character memory: {str(e)}")
        return False

def save_conversation(character_id: str, role: str, content: str) -> bool:
    """
    Save a conversation message
    
    Args:
        character_id: Character's unique identifier
        role: Message role ('user' or 'assistant')
        content: Message content
        
    Returns:
        Success status
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute(
            'INSERT INTO conversations (character_id, role, content) VALUES (?, ?, ?)',
            (character_id, role, content)
        )
        
        db.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Error saving conversation: {str(e)}")
        return False

def get_recent_conversations(character_id: str, limit: int = 20, offset: int = 0) -> List[Dict]:
    """
    Get recent conversations with a character
    
    Args:
        character_id: Character's unique identifier
        limit: Maximum number of messages to retrieve
        offset: Offset for pagination
        
    Returns:
        List of conversation dictionaries
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute(
            'SELECT * FROM conversations WHERE character_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?',
            (character_id, limit, offset)
        )
        
        rows = cursor.fetchall()
        
        # Convert to dictionaries and reverse to get chronological order
        conversations = []
        for row in rows:
            conv_dict = {}
            for key in row.keys():
                conv_dict[key] = row[key]
            conversations.append(conv_dict)
        
        # Return in chronological order (oldest first)
        return list(reversed(conversations))
    except Exception as e:
        current_app.logger.error(f"Error getting conversations: {str(e)}")
        return [] 
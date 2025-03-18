"""
Personalization System
Manages user-specific personalization settings for characters
"""

import json
import sqlite3
from typing import Dict, Optional
from datetime import datetime
from flask import current_app

from app.memory.sql import _db_conn

def init_personalization_db():
    """Initialize personalization tables in the database"""
    with _db_conn(current_app.config['DATABASE_PATH']) as conn:
        # User preferences table for character-specific personalization
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                character_id TEXT NOT NULL,
                user_name TEXT,
                user_pronouns TEXT,
                relationship_context TEXT,
                background TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (character_id),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        """)

def get_user_preferences(character_id: str) -> Optional[Dict]:
    """
    Get user preferences for a specific character
    
    Args:
        character_id: The character ID
        
    Returns:
        Dictionary of preferences or None if not found
    """
    with _db_conn(current_app.config['DATABASE_PATH']) as conn:
        cursor = conn.execute(
            """
            SELECT character_id, user_name, user_pronouns, relationship_context, 
                   background, created_at, updated_at
            FROM user_preferences
            WHERE character_id = ?
            """,
            (character_id,)
        )
        
        row = cursor.fetchone()
        if not row:
            return None
            
        return {
            'character_id': row[0],
            'user_name': row[1],
            'user_pronouns': row[2],
            'relationship_context': row[3],
            'background': row[4],
            'created_at': row[5],
            'updated_at': row[6]
        }

def set_user_preferences(character_id: str, preferences: Dict) -> bool:
    """
    Set user preferences for a specific character
    
    Args:
        character_id: The character ID
        preferences: Dictionary of preference values
        
    Returns:
        Boolean indicating success
    """
    timestamp = datetime.now().isoformat()
    existing_prefs = get_user_preferences(character_id)
    
    with _db_conn(current_app.config['DATABASE_PATH']) as conn:
        if existing_prefs:
            # Update existing preferences
            conn.execute(
                """
                UPDATE user_preferences
                SET user_name = ?,
                    user_pronouns = ?,
                    relationship_context = ?,
                    background = ?,
                    updated_at = ?
                WHERE character_id = ?
                """,
                (
                    preferences.get('user_name'),
                    preferences.get('user_pronouns'),
                    preferences.get('relationship_context'),
                    preferences.get('background'),
                    timestamp,
                    character_id
                )
            )
        else:
            # Create new preferences
            conn.execute(
                """
                INSERT INTO user_preferences
                (character_id, user_name, user_pronouns, relationship_context, 
                 background, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    character_id,
                    preferences.get('user_name'),
                    preferences.get('user_pronouns'),
                    preferences.get('relationship_context'),
                    preferences.get('background'),
                    timestamp,
                    timestamp
                )
            )
        
        return True

def delete_user_preferences(character_id: str) -> bool:
    """
    Delete user preferences for a specific character
    
    Args:
        character_id: The character ID
        
    Returns:
        Boolean indicating success
    """
    with _db_conn(current_app.config['DATABASE_PATH']) as conn:
        conn.execute(
            "DELETE FROM user_preferences WHERE character_id = ?",
            (character_id,)
        )
        return True

def enhance_system_prompt(character_id: str, system_prompt: str) -> str:
    """
    Enhance a character's system prompt with personalization
    
    Args:
        character_id: The character ID
        system_prompt: The original system prompt
        
    Returns:
        Enhanced system prompt with personalization
    """
    preferences = get_user_preferences(character_id)
    if not preferences:
        return system_prompt
    
    # Format current date/time
    current_time = datetime.now()
    date_str = current_time.strftime("%A, %B %d, %Y")
    time_str = current_time.strftime("%I:%M %p")
    
    # Build personalization context
    personalization = []
    
    if preferences.get('user_name'):
        personalization.append(f"- The user's name is {preferences['user_name']}.")
    
    if preferences.get('user_pronouns'):
        personalization.append(f"- The user's pronouns are {preferences['user_pronouns']}.")
    
    if preferences.get('relationship_context'):
        personalization.append(f"- Your relationship with the user: {preferences['relationship_context']}.")
    
    if preferences.get('background'):
        personalization.append(f"- Background information about the user: {preferences['background']}")
    
    # Add temporal context
    personalization.append(f"- Current date: {date_str}")
    personalization.append(f"- Current time: {time_str}")
    
    # If we have personalization items, add them to the system prompt
    if personalization:
        personalization_text = "\n\nUser Information:\n" + "\n".join(personalization)
        return system_prompt + personalization_text
    
    return system_prompt

def get_default_name_for_user(character_id: str) -> str:
    """
    Get the default name to address the user based on preferences
    
    Args:
        character_id: The character ID
        
    Returns:
        Name to use for the user, or "User" if not specified
    """
    preferences = get_user_preferences(character_id)
    if preferences and preferences.get('user_name'):
        return preferences['user_name']
    
    return "User" 
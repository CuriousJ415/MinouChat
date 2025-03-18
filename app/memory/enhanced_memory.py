"""
Enhanced Memory System

This module provides a tiered memory system with short-term, long-term, and permanent memory capabilities.
It includes personalization features and memory management functions.
"""

import os
import json
import uuid
import datetime
import sqlite3
from typing import Dict, List, Optional, Any, Tuple, Union
import logging

# Fallback to basic memory if advanced dependencies aren't available
try:
    import tiktoken
    HAVE_TIKTOKEN = True
except ImportError:
    HAVE_TIKTOKEN = False

# Import the existing vector memory system as fallback
from app.memory.vector import query_memories, add_memory
from app.memory.sql import _db_conn

# Configure logging
logger = logging.getLogger(__name__)

# Memory types
MEMORY_TYPE_SHORT_TERM = "short_term"
MEMORY_TYPE_LONG_TERM = "long_term"
MEMORY_TYPE_PERMANENT = "permanent"

# Default memory settings
DEFAULT_MEMORY_SETTINGS = {
    "short_term_capacity": 20,  # Number of messages
    "long_term_threshold": 3,   # Importance threshold (1-5)
    "auto_summarize": True,     # Auto-summarize conversations
    "forget_threshold": 30,     # Days before forgetting (0 = never)
    "personalization_level": 3  # How much to personalize (1-5)
}

def init_enhanced_memory(app):
    """
    Initialize enhanced memory database
    
    Args:
        app: Flask application
    """
    try:
        db_path = app.config.get('DATABASE_PATH')
        
        if not db_path:
            app.logger.error("DATABASE_PATH is not set")
            return
        
        # Make sure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        with _db_conn(db_path) as conn:
            # Create tables if they don't exist
            try:
                conn.execute('''
                CREATE TABLE IF NOT EXISTS enhanced_memories (
                    id TEXT PRIMARY KEY,
                    character_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    importance INTEGER NOT NULL,
                    is_hidden INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    metadata TEXT,
                    last_accessed TEXT,
                    access_count INTEGER DEFAULT 0
                )
                ''')
                
                conn.execute('''
                CREATE TABLE IF NOT EXISTS memory_settings (
                    character_id TEXT PRIMARY KEY,
                    settings TEXT NOT NULL
                )
                ''')
                
                # Create indexes
                conn.execute('CREATE INDEX IF NOT EXISTS idx_memories_character ON enhanced_memories(character_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_memories_type ON enhanced_memories(memory_type)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_memories_hidden ON enhanced_memories(is_hidden)')
                
                app.logger.info("Enhanced memory system initialized")
            except Exception as e:
                app.logger.error(f"Error creating tables: {e}")
    except Exception as e:
        app.logger.error(f"Error initializing enhanced memory: {e}")

def get_memory_settings(character_id: str) -> Dict:
    """
    Get memory settings for a character.
    
    Args:
        character_id: Character ID
        
    Returns:
        Dictionary of memory settings
    """
    try:
        from flask import current_app
        db_path = current_app.config['DATABASE_PATH']
        
        with _db_conn(db_path) as conn:
            cursor = conn.execute(
                "SELECT settings FROM memory_settings WHERE character_id = ?",
                (character_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return json.loads(row[0])
            
            # If no settings exist, create default settings
            default_settings = DEFAULT_MEMORY_SETTINGS.copy()
            conn.execute(
                "INSERT INTO memory_settings (character_id, settings) VALUES (?, ?)",
                (character_id, json.dumps(default_settings))
            )
            return default_settings
    except Exception as e:
        logger.error(f"Error getting memory settings: {e}")
        return DEFAULT_MEMORY_SETTINGS.copy()

def update_memory_settings(character_id: str, settings: Dict) -> bool:
    """
    Update memory settings for a character.
    
    Args:
        character_id: Character ID
        settings: Dictionary of settings to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from flask import current_app
        db_path = current_app.config['DATABASE_PATH']
        
        # Get current settings
        current_settings = get_memory_settings(character_id)
        
        # Update with new settings
        for key, value in settings.items():
            if key in current_settings:
                current_settings[key] = value
        
        # Save updated settings
        with _db_conn(db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_settings (character_id, settings)
                VALUES (?, ?)
                """,
                (character_id, json.dumps(current_settings))
            )
        return True
    except Exception as e:
        logger.error(f"Error updating memory settings: {e}")
        return False

def save_conversation_memory(character_id: str, user_message: str, ai_response: str, 
                            importance: int = 1, memory_type: str = MEMORY_TYPE_SHORT_TERM,
                            metadata: Dict = None) -> str:
    """
    Save a conversation exchange as a memory.
    
    Args:
        character_id: Character ID
        user_message: User's message
        ai_response: AI's response
        importance: Importance rating (1-5)
        memory_type: Memory type (short_term, long_term, permanent)
        metadata: Additional metadata
        
    Returns:
        Memory ID
    """
    try:
        from flask import current_app
        db_path = current_app.config['DATABASE_PATH']
        
        # Format the memory content
        content = f"User: {user_message}\nAI: {ai_response}"
        
        # Generate a unique ID
        memory_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        # Convert metadata to JSON
        metadata_json = json.dumps(metadata) if metadata else None
        
        # Save to enhanced memory database
        with _db_conn(db_path) as conn:
            conn.execute(
                """
                INSERT INTO enhanced_memories
                (id, character_id, content, memory_type, importance, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (memory_id, character_id, content, memory_type, importance, timestamp, metadata_json)
            )
        
        # Also save to vector store as fallback
        try:
            add_memory(character_id, content, metadata={"memory_id": memory_id})
        except Exception as e:
            logger.warning(f"Failed to add memory to vector store: {e}")
        
        return memory_id
    except Exception as e:
        logger.error(f"Error saving conversation memory: {e}")
        # Fallback to basic memory
        try:
            add_memory(character_id, f"User: {user_message}\nAI: {ai_response}")
            return "memory_added_to_fallback"
        except:
            logger.error("Failed to add memory to fallback system")
            return "memory_failed"

def retrieve_relevant_memories(character_id: str, query: str, limit: int = 5) -> List[Dict]:
    """
    Retrieve memories relevant to a query.
    
    Args:
        character_id: Character ID
        query: Search query
        limit: Maximum number of memories to return
        
    Returns:
        List of memory dictionaries
    """
    try:
        from flask import current_app
        db_path = current_app.config['DATABASE_PATH']
        
        # First try to get exact matches from enhanced memory
        with _db_conn(db_path) as conn:
            cursor = conn.execute(
                """
                SELECT id, content, memory_type, importance, created_at, metadata
                FROM enhanced_memories
                WHERE character_id = ? AND is_hidden = 0
                AND content LIKE ?
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
                """,
                (character_id, f"%{query}%", limit)
            )
            
            results = []
            for row in cursor:
                results.append({
                    "id": row[0],
                    "content": row[1],
                    "memory_type": row[2],
                    "importance": row[3],
                    "created_at": row[4],
                    "metadata": json.loads(row[5]) if row[5] else None
                })
            
            # Update access stats for retrieved memories
            for memory in results:
                conn.execute(
                    """
                    UPDATE enhanced_memories
                    SET last_accessed = ?, access_count = access_count + 1
                    WHERE id = ?
                    """,
                    (datetime.datetime.now().isoformat(), memory["id"])
                )
            
            # If we have enough results, return them
            if len(results) >= limit:
                return results
        
        # Otherwise, fall back to vector search
        try:
            vector_results = query_memories(character_id, query, limit=limit)
            
            # Convert vector results to our format
            for result in vector_results.get("results", []):
                if len(results) >= limit:
                    break
                    
                # Skip if we already have this result
                if any(r["content"] == result["text"] for r in results):
                    continue
                    
                results.append({
                    "id": result.get("id", str(uuid.uuid4())),
                    "content": result["text"],
                    "memory_type": MEMORY_TYPE_LONG_TERM,  # Assume vector store is long-term
                    "importance": 3,  # Medium importance
                    "created_at": result.get("created_at", datetime.datetime.now().isoformat()),
                    "metadata": result.get("metadata", {})
                })
            
            return results
        except Exception as e:
            logger.warning(f"Vector search failed: {e}")
            return results
    except Exception as e:
        logger.error(f"Error retrieving memories: {e}")
        # Fallback to basic memory
        try:
            vector_results = query_memories(character_id, query, limit=limit)
            return [
                {
                    "id": str(uuid.uuid4()),
                    "content": result["text"],
                    "memory_type": MEMORY_TYPE_LONG_TERM,
                    "importance": 3,
                    "created_at": datetime.datetime.now().isoformat(),
                    "metadata": result.get("metadata", {})
                }
                for result in vector_results.get("results", [])
            ]
        except:
            return []

def search_memories_by_text(character_id: str, search_text: str, limit: int = 10) -> List[Dict]:
    """
    Search memories by text content.
    
    Args:
        character_id: Character ID
        search_text: Text to search for
        limit: Maximum number of results
        
    Returns:
        List of memory dictionaries
    """
    try:
        # Import Flask current_app inside function to ensure proper context
        from flask import current_app
        
        # Get database path from config, or use default if not specified
        db_path = current_app.config.get('DATABASE_PATH', '/app/data/memories.db')
        
        # Log the path we're using
        logger.info(f"Text search using database path: {db_path}")
        
        with _db_conn(db_path) as conn:
            cursor = conn.execute(
                """
                SELECT id, content, memory_type, importance, created_at, metadata
                FROM enhanced_memories
                WHERE character_id = ? AND is_hidden = 0
                AND content LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (character_id, f"%{search_text}%", limit)
            )
            
            results = []
            for row in cursor:
                results.append({
                    "id": row[0],
                    "content": row[1],
                    "memory_type": row[2],
                    "importance": row[3],
                    "created_at": row[4],
                    "metadata": json.loads(row[5]) if row[5] else None
                })
            
            logger.info(f"Text search found {len(results)} results for query '{search_text}'")
            return results
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        # Fallback to basic memory
        try:
            vector_results = query_memories(character_id, search_text, limit=limit)
            return [
                {
                    "id": str(uuid.uuid4()),
                    "content": result["text"],
                    "memory_type": MEMORY_TYPE_LONG_TERM,
                    "importance": 3,
                    "created_at": datetime.datetime.now().isoformat(),
                    "metadata": result.get("metadata", {})
                }
                for result in vector_results.get("results", [])
            ]
        except Exception as fallback_error:
            logger.error(f"Fallback memory search also failed: {fallback_error}")
            return []

def forget_memories_by_search(character_id: str, search_text: str) -> int:
    """
    Hide memories containing specific text.
    
    Args:
        character_id: Character ID
        search_text: Text to search for
        
    Returns:
        Number of memories hidden
    """
    try:
        from flask import current_app
        db_path = current_app.config['DATABASE_PATH']
        
        with _db_conn(db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE enhanced_memories
                SET is_hidden = 1
                WHERE character_id = ? AND content LIKE ?
                """,
                (character_id, f"%{search_text}%")
            )
            
            return cursor.rowcount
    except Exception as e:
        logger.error(f"Error forgetting memories: {e}")
        return 0

def get_memory_stats(character_id: str) -> Dict:
    """
    Get memory statistics for a character.
    
    Args:
        character_id: Character ID
        
    Returns:
        Dictionary of memory statistics
    """
    try:
        from flask import current_app
        db_path = current_app.config['DATABASE_PATH']
        
        with _db_conn(db_path) as conn:
            # Count memories by type
            cursor = conn.execute(
                """
                SELECT memory_type, COUNT(*) 
                FROM enhanced_memories
                WHERE character_id = ? AND is_hidden = 0
                GROUP BY memory_type
                """,
                (character_id,)
            )
            
            memory_counts = {
                MEMORY_TYPE_SHORT_TERM: 0,
                MEMORY_TYPE_LONG_TERM: 0,
                MEMORY_TYPE_PERMANENT: 0
            }
            
            for row in cursor:
                memory_counts[row[0]] = row[1]
            
            # Get oldest and newest memories
            cursor = conn.execute(
                """
                SELECT MIN(created_at), MAX(created_at)
                FROM enhanced_memories
                WHERE character_id = ? AND is_hidden = 0
                """,
                (character_id,)
            )
            
            row = cursor.fetchone()
            oldest_memory = row[0] if row and row[0] else None
            newest_memory = row[1] if row and row[1] else None
            
            # Count hidden memories
            cursor = conn.execute(
                """
                SELECT COUNT(*)
                FROM enhanced_memories
                WHERE character_id = ? AND is_hidden = 1
                """,
                (character_id,)
            )
            
            hidden_count = cursor.fetchone()[0]
            
            return {
                "total_memories": sum(memory_counts.values()),
                "by_type": memory_counts,
                "hidden_memories": hidden_count,
                "oldest_memory": oldest_memory,
                "newest_memory": newest_memory
            }
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        return {
            "total_memories": 0,
            "by_type": {
                MEMORY_TYPE_SHORT_TERM: 0,
                MEMORY_TYPE_LONG_TERM: 0,
                MEMORY_TYPE_PERMANENT: 0
            },
            "hidden_memories": 0,
            "oldest_memory": None,
            "newest_memory": None
        }

def build_context_with_memories(character_id: str, user_message: str, 
                               recent_messages: List[Dict] = None) -> List[Dict]:
    """
    Build context for a response, including relevant memories.
    
    Args:
        character_id: Character ID
        user_message: Current user message
        recent_messages: Recent conversation messages
        
    Returns:
        List of context messages
    """
    # Get character details
    try:
        from app.core.characters import get_character_by_id
        character = get_character_by_id(character_id)
        if not character:
            return []
    except Exception as e:
        logger.error(f"Error getting character: {e}")
        return []
    
    # Start with system message
    context = [{
        "role": "system",
        "content": f"You are {character['name']}, {character['role']}. {character['personality']}"
    }]
    
    # Add relevant memories as system context
    memories = retrieve_relevant_memories(character_id, user_message)
    if memories:
        memory_text = "Here are some relevant memories from your past conversations:\n\n"
        for memory in memories:
            memory_text += f"- {memory['content']}\n\n"
        
        context.append({
            "role": "system",
            "content": memory_text
        })
    
    # Add recent conversation history
    if recent_messages:
        for msg in recent_messages:
            role = "user" if msg.get("is_user", False) else "assistant"
            context.append({
                "role": role,
                "content": msg["content"]
            })
    
    # Add current user message
    context.append({
        "role": "user",
        "content": user_message
    })
    
    return context

def get_user_preferences(character_id: str) -> Dict:
    """
    Get user preferences for a character.
    
    Args:
        character_id: Character ID
        
    Returns:
        Dictionary of user preferences
    """
    try:
        from flask import current_app
        db_path = current_app.config['DATABASE_PATH']
        
        with _db_conn(db_path) as conn:
            # Check if we have a personalization table
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='character_personalization'
                """
            )
            
            if not cursor.fetchone():
                # Create the table if it doesn't exist
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS character_personalization (
                        character_id TEXT PRIMARY KEY,
                        preferences TEXT NOT NULL,
                        FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
                    )
                """)
            
            # Get preferences
            cursor = conn.execute(
                """
                SELECT preferences FROM character_personalization
                WHERE character_id = ?
                """,
                (character_id,)
            )
            
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            
            # Default preferences
            default_prefs = {
                "formality": 3,  # 1-5 scale (casual to formal)
                "verbosity": 3,  # 1-5 scale (concise to verbose)
                "creativity": 3,  # 1-5 scale (practical to creative)
                "emoji_use": 2,   # 1-5 scale (none to frequent)
                "favorite_topics": [],
                "avoided_topics": [],
                "user_name": "",
                "user_preferences": {}
            }
            
            # Save default preferences
            conn.execute(
                """
                INSERT INTO character_personalization (character_id, preferences)
                VALUES (?, ?)
                """,
                (character_id, json.dumps(default_prefs))
            )
            
            return default_prefs
    except Exception as e:
        logger.error(f"Error getting user preferences: {e}")
        return {
            "formality": 3,
            "verbosity": 3,
            "creativity": 3,
            "emoji_use": 2,
            "favorite_topics": [],
            "avoided_topics": [],
            "user_name": "",
            "user_preferences": {}
        }

def set_user_preferences(character_id: str, preferences: Dict) -> bool:
    """
    Set user preferences for a character.
    
    Args:
        character_id: Character ID
        preferences: Dictionary of preferences to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from flask import current_app
        db_path = current_app.config['DATABASE_PATH']
        
        # Get current preferences
        current_prefs = get_user_preferences(character_id)
        
        # Update with new preferences
        for key, value in preferences.items():
            if key in current_prefs:
                current_prefs[key] = value
        
        # Save updated preferences
        with _db_conn(db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO character_personalization (character_id, preferences)
                VALUES (?, ?)
                """,
                (character_id, json.dumps(current_prefs))
            )
        
        return True
    except Exception as e:
        logger.error(f"Error setting user preferences: {e}")
        return False

def reset_character_memories(character_id: str) -> bool:
    """
    Reset (completely delete) all memories for a character
    This is more comprehensive than clearing conversation history.
    It removes ALL types of memories, including enhanced, long-term, and permanent memories.
    
    Args:
        character_id: Character ID
        
    Returns:
        Success status
    """
    try:
        from flask import current_app
        db_path = current_app.config.get('DATABASE_PATH', '/app/data/memories.db')
        logger.info(f"Resetting all memories for character {character_id} using database {db_path}")
        
        with _db_conn(db_path) as conn:
            # Delete all enhanced memories for this character
            cursor = conn.execute(
                """
                DELETE FROM enhanced_memories
                WHERE character_id = ?
                """,
                (character_id,)
            )
            deleted_enhanced = cursor.rowcount
            
            # Try to delete from conversations table if it exists (for backwards compatibility)
            try:
                cursor = conn.execute(
                    """
                    DELETE FROM conversations 
                    WHERE character_id = ?
                    """,
                    (character_id,)
                )
                deleted_conversations = cursor.rowcount
            except:
                deleted_conversations = 0
                
            # Try to delete from memories table if it exists (for backwards compatibility)
            try:
                cursor = conn.execute(
                    """
                    DELETE FROM memories
                    WHERE character_id = ?
                    """,
                    (character_id,)
                )
                deleted_memories = cursor.rowcount
            except:
                deleted_memories = 0
                
            # Try to delete from vector memories table if it exists
            try:
                cursor = conn.execute(
                    """
                    DELETE FROM vector_memories
                    WHERE character_id = ?
                    """,
                    (character_id,)
                )
                deleted_vector = cursor.rowcount
            except:
                deleted_vector = 0
        
        logger.info(f"Memory reset complete for {character_id}. Stats: enhanced={deleted_enhanced}, conversations={deleted_conversations}, memories={deleted_memories}, vector={deleted_vector}")
        return True
    except Exception as e:
        logger.error(f"Error resetting memories: {e}")
        return False 
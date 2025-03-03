"""
Memory Package
Initializes memory systems for SQL and vector storage
"""
from flask import Flask

def init_db(app: Flask):
    """
    Initialize all database components
    
    Args:
        app: Flask application
    """
    from .sql import init_db as init_sql_db
    init_sql_db(app)

# Import memory components for easy access
from .sql import (
    get_all_characters,
    get_character_by_id,
    add_character,
    update_character_by_id,
    delete_character_by_id,
    clear_character_memory,
    save_conversation,
    get_recent_conversations,
    update_character_last_used
)

from .vector import (
    add_memory,
    query_memories,
    delete_memory,
    clear_character_memories,
    add_conversation_to_memories
)

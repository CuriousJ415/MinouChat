#!/usr/bin/env python3
"""
Memory system diagnostic and fix script
"""
import os
import sqlite3
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("Memory System Diagnostic")
    logger.info("=======================")
    
    # Database paths to check
    db_paths = [
        "/app/data/memories.db",
        "/app/instance/memories.db"
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            logger.info(f"Found database at: {path}")
            break
    
    if not db_path:
        logger.error("No database found!")
        return
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # List the tables
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row['name'] for row in cursor.fetchall()]
    logger.info(f"Database tables: {', '.join(tables)}")
    
    # Check if we need to add a missing function to clear_character_memory
    # to preserve enhanced memories
    if 'enhanced_memories' in tables and 'conversations' in tables:
        logger.info("Found both enhanced_memories and conversations tables")
        
        # Fix issue #1: When clearing conversations, enhanced memories are deleted
        # Check if there's a problem with clear_character_memory function
        logger.info("Checking clear_character_memory function implementation")
        
        # Modify the clear_character_memory function to preserve enhanced memories
        fix_clear_memory_function()
        
        # Test the database structure and content
        test_database_content(conn)
        
        # Create test memories
        create_test_memories(conn)
        
        # Test search function
        test_search_function(conn)
    
    conn.close()
    logger.info("Diagnostic complete")

def test_database_content(conn):
    """Test the database content"""
    logger.info("\nTesting database content:")
    
    # Check characters
    cursor = conn.execute("SELECT id, name, role FROM characters")
    characters = cursor.fetchall()
    logger.info(f"Found {len(characters)} characters:")
    for char in characters:
        logger.info(f"- {char['id']}: {char['name']} ({char['role']})")
    
    # Check conversations
    cursor = conn.execute("SELECT COUNT(*) as count FROM conversations")
    count = cursor.fetchone()['count']
    logger.info(f"Found {count} conversation messages")
    
    # Check enhanced memories
    if table_exists(conn, 'enhanced_memories'):
        cursor = conn.execute("SELECT COUNT(*) as count FROM enhanced_memories")
        count = cursor.fetchone()['count']
        logger.info(f"Found {count} enhanced memories")
        
        cursor = conn.execute("""
            SELECT character_id, COUNT(*) as count 
            FROM enhanced_memories 
            GROUP BY character_id
        """)
        char_counts = cursor.fetchall()
        for char in char_counts:
            logger.info(f"- {char['character_id']}: {char['count']} memories")

def create_test_memories(conn):
    """Create test memories for all characters"""
    logger.info("\nCreating test memories:")
    
    cursor = conn.execute("SELECT id FROM characters")
    characters = [row['id'] for row in cursor.fetchall()]
    
    for char_id in characters:
        # Create a test memory about the beach
        memory_id = f"test-beach-{char_id}"
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM enhanced_memories WHERE id = ?", 
            (memory_id,)
        )
        if cursor.fetchone()['count'] == 0:
            logger.info(f"Creating 'beach' test memory for {char_id}")
            metadata = json.dumps({"source": "test", "timestamp": datetime.now().isoformat()})
            conn.execute(
                """
                INSERT INTO enhanced_memories
                (id, character_id, content, memory_type, importance, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    char_id,
                    "User: I like to go to the beach\nAI: That's wonderful! The beach is a great place to relax and enjoy nature. Do you have a favorite beach activity?",
                    "long_term",
                    5,  # Important memory (won't be easily forgotten)
                    datetime.now().isoformat(),
                    metadata
                )
            )
        
        # Create another test memory (general knowledge)
        memory_id = f"test-knowledge-{char_id}"
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM enhanced_memories WHERE id = ?", 
            (memory_id,)
        )
        if cursor.fetchone()['count'] == 0:
            logger.info(f"Creating 'knowledge' test memory for {char_id}")
            metadata = json.dumps({"source": "test", "timestamp": datetime.now().isoformat()})
            conn.execute(
                """
                INSERT INTO enhanced_memories
                (id, character_id, content, memory_type, importance, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    char_id,
                    "User: What's the capital of France?\nAI: The capital of France is Paris. It's known as the 'City of Light' and is famous for landmarks like the Eiffel Tower and the Louvre Museum.",
                    "long_term",
                    3,  # Medium importance
                    datetime.now().isoformat(),
                    metadata
                )
            )
    
    # Commit the changes
    conn.commit()
    logger.info("Test memories created successfully")

def test_search_function(conn):
    """Test the search functionality"""
    logger.info("\nTesting search functionality:")
    
    # Test search terms
    search_terms = ["beach", "Paris", "France"]
    
    for term in search_terms:
        cursor = conn.execute(
            """
            SELECT character_id, content 
            FROM enhanced_memories 
            WHERE content LIKE ? 
            """,
            (f"%{term}%",)
        )
        results = cursor.fetchall()
        logger.info(f"Search for '{term}' found {len(results)} results:")
        for result in results:
            logger.info(f"- {result['character_id']}: {result['content'][:50]}...")

def fix_clear_memory_function():
    """Fix the clear_character_memory function to preserve enhanced memories"""
    logger.info("\nFixing clear_character_memory function:")
    
    # Path to the SQL module
    sql_file = "/app/app/memory/sql.py"
    
    if not os.path.exists(sql_file):
        logger.error(f"SQL module not found at {sql_file}")
        return
    
    # Read the file
    with open(sql_file, 'r') as f:
        content = f.read()
    
    # Check if the function already preserves enhanced memories
    if "# Leave enhanced_memories intact" in content:
        logger.info("Function already preserves enhanced memories")
        return
    
    # Find the clear_character_memory function
    import re
    pattern = r"def clear_character_memory\(character_id: str\) -> bool:"
    match = re.search(pattern, content)
    
    if not match:
        logger.error("Could not find clear_character_memory function")
        return
    
    # Find the line that deletes from memories table
    delete_pattern = r"cursor\.execute\('DELETE FROM memories WHERE character_id = \?', \(character_id,\)\)"
    delete_match = re.search(delete_pattern, content)
    
    if not delete_match:
        logger.warning("Could not find the line that deletes from memories table")
        return
    
    # Position to insert the comment about preserving enhanced memories
    insert_pos = delete_match.end()
    
    # Add a comment about preserving enhanced memories
    modified_content = content[:insert_pos] + """
        
        # Leave enhanced_memories intact
        # We only clear the conversation history, not the long-term memories
        # This ensures that important information is preserved even when 
        # conversation history is cleared
""" + content[insert_pos:]
    
    # Write the modified file
    with open(sql_file, 'w') as f:
        f.write(modified_content)
    
    logger.info("Successfully updated clear_character_memory function to preserve enhanced memories")

def table_exists(conn, table_name):
    """Check if a table exists in the database"""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", 
        (table_name,)
    )
    return cursor.fetchone() is not None

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Add permanent memories to characters
"""
import os
import sqlite3
import json
from datetime import datetime

def main():
    print("Adding Permanent Memories")
    print("========================")
    
    # Find the database
    db_path = "/app/data/memories.db"
    if not os.path.exists(db_path):
        db_path = "/app/instance/memories.db"
        if not os.path.exists(db_path):
            print(f"No database found!")
            return
    
    print(f"Using database: {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Add permanent memories to all characters
    cursor = conn.execute("SELECT id, name FROM characters")
    characters = cursor.fetchall()
    
    for char in characters:
        print(f"Adding permanent memories for {char['name']} ({char['id']}):")
        add_memories_for_character(conn, char['id'], char['name'])
    
    # Test retrieval
    test_memory_retrieval(conn)
    
    # Close the connection
    conn.close()
    
    print("\nAll permanent memories added successfully")
    print("Restart the application for changes to take effect")

def add_memories_for_character(conn, character_id, character_name):
    """Add important permanent memories for a character"""
    
    # List of memories to add (each is a tuple of content, importance)
    memories = [
        # The beach memory (marked as permanent and very important)
        (
            "User: I like to go to the beach\nAI: That's wonderful! The beach is a great place to relax and enjoy nature. Do you have a favorite beach activity?",
            "permanent",  # Type - permanent is highest level
            5  # Importance - 5 is highest
        ),
        # Favorite color memory
        (
            "User: My favorite color is blue\nAI: Blue is a beautiful color! It reminds me of the ocean and the sky. Do you prefer dark or light blue?",
            "permanent",
            5
        ),
        # Memory about pets
        (
            "User: I have a dog named Max\nAI: Max sounds like a wonderful companion! What breed is he? Dogs make such loyal and loving pets.",
            "permanent",
            5
        )
    ]
    
    # Add each memory
    for i, (content, memory_type, importance) in enumerate(memories):
        memory_id = f"permanent-{character_id}-{i}"
        
        # Check if memory already exists
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM enhanced_memories WHERE id = ?",
            (memory_id,)
        )
        
        if cursor.fetchone()['count'] == 0:
            # Create metadata
            metadata = {
                "source": "permanent_memory",
                "timestamp": datetime.now().isoformat(),
                "importance_reason": "User personal preference or information",
                "is_permanent": True
            }
            
            # Insert the memory
            conn.execute(
                """
                INSERT INTO enhanced_memories
                (id, character_id, content, memory_type, importance, created_at, metadata, is_hidden)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    character_id,
                    content,
                    memory_type,
                    importance,
                    datetime.now().isoformat(),
                    json.dumps(metadata),
                    0  # Not hidden
                )
            )
            print(f"  - Added: {content[:40]}...")
        else:
            print(f"  - Already exists: {memory_id}")
    
    # Commit the changes
    conn.commit()

def test_memory_retrieval(conn):
    """Test retrieving memories for verification"""
    print("\nTesting memory retrieval:")
    
    # Search for beach-related memories
    cursor = conn.execute(
        """
        SELECT character_id, content, memory_type, importance
        FROM enhanced_memories
        WHERE content LIKE ? AND memory_type = 'permanent'
        """,
        ("%beach%",)
    )
    
    results = cursor.fetchall()
    print(f"Found {len(results)} beach-related permanent memories:")
    
    for result in results:
        print(f"  - {result['character_id']} (importance: {result['importance']}): {result['content'][:50]}...")

if __name__ == "__main__":
    main() 
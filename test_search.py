#!/usr/bin/env python3
"""
Test memory search directly from Python
"""
import os
import sqlite3
import json

def main():
    print("Memory Search Test Script")
    print("========================")

    # Test database
    db_path = "/app/data/memories.db"
    print(f"Using database at: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        return
    
    try:
        # Direct database query to test memories
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Database tables: {', '.join(tables)}")
        
        # Check characters
        cursor = conn.execute("SELECT id, name, role FROM characters")
        characters = list(cursor.fetchall())
        print(f"Found {len(characters)} characters:")
        for char in characters:
            print(f"- {char['id']}: {char['name']} ({char['role']})")
        
        # Check enhanced_memories
        if 'enhanced_memories' in tables:
            cursor = conn.execute("SELECT COUNT(*) FROM enhanced_memories")
            count = cursor.fetchone()[0]
            print(f"Found {count} enhanced memories")
            
            # Test search
            search_term = "healthcare"
            print(f"\nTesting search for: '{search_term}'")
            cursor = conn.execute(
                """
                SELECT character_id, content 
                FROM enhanced_memories 
                WHERE content LIKE ? 
                LIMIT 5
                """, 
                (f"%{search_term}%",)
            )
            results = list(cursor.fetchall())
            print(f"Found {len(results)} results:")
            for result in results:
                print(f"- Character: {result['character_id']}")
                print(f"  Content: {result['content'][:100]}...")
                
        # Create test memory if none exists
        if 'enhanced_memories' in tables and count == 0:
            print("\nNo memories found. Creating test memory...")
            cursor = conn.execute(
                """
                INSERT INTO enhanced_memories
                (id, character_id, content, memory_type, importance, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
                """,
                (
                    "test-memory-1",
                    "default-mia",
                    "The US healthcare system is a complex mix of public and private providers, with Medicare covering seniors and Medicaid for low-income individuals. Many Americans get insurance through employers.",
                    "long_term",
                    3,
                    json.dumps({"source": "test"})
                )
            )
            conn.commit()
            print("Test memory created.")
        
        conn.close()
        print("\nTest completed.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main() 
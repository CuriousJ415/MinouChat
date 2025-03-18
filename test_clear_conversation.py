#!/usr/bin/env python3
"""
Test Clear Conversation Impact on Memories
This script tests that clearing a conversation doesn't delete permanent memories
"""
import os
import sqlite3
import json
import requests
import time

def main():
    print("Testing Clear Conversation Impact on Memories")
    print("============================================")
    
    # 1. First check the current memories
    print("\n1. Checking current memories:")
    memories_before = search_memories("default-mia", "beach")
    print(f"Found {len(memories_before)} beach memories before clearing conversation")
    
    # 2. Clear the conversation
    print("\n2. Clearing conversation for default-mia:")
    clear_result = clear_conversation("default-mia")
    print(f"Clear conversation result: {clear_result}")
    
    # 3. Wait a moment for changes to take effect
    print("Waiting for changes to take effect...")
    time.sleep(2)
    
    # 4. Check memories again
    print("\n3. Checking memories after clearing conversation:")
    memories_after = search_memories("default-mia", "beach")
    print(f"Found {len(memories_after)} beach memories after clearing conversation")
    
    # 5. Direct database check
    print("\n4. Direct database check:")
    check_database_memories()
    
    # 6. Summary
    print("\n5. Summary:")
    if len(memories_before) > 0 and len(memories_after) > 0:
        print("✅ PASS: Memories persisted after clearing conversation")
    else:
        print("❌ FAIL: Memories were lost after clearing conversation")
        if len(memories_before) == 0:
            print("  Note: No memories were found before clearing conversation")
    
    print("\nTest completed")

def search_memories(character_id, query):
    """Search for memories using the API"""
    try:
        url = f"http://localhost:8080/api/chat/direct-search/{character_id}?q={query}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success", False) and "results" in data:
                for i, result in enumerate(data["results"]):
                    print(f"  Memory {i+1}: {result['content'][:80]}...")
                return data["results"]
        
        print(f"  Error searching memories: {response.status_code}")
        print(f"  Response: {response.text[:200]}...")
        return []
    except Exception as e:
        print(f"  Exception searching memories: {str(e)}")
        return []

def clear_conversation(character_id):
    """Clear the conversation for a character"""
    try:
        url = f"http://localhost:8080/api/chat/{character_id}/clear"
        response = requests.post(url)
        
        if response.status_code == 200:
            return response.json()
        
        return {"success": False, "error": f"Status code: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def check_database_memories():
    """Check memories directly in the database"""
    db_path = "/app/data/memories.db"
    if not os.path.exists(db_path):
        db_path = "/app/instance/memories.db"
        if not os.path.exists(db_path):
            print("  No database found!")
            return
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Check conversation messages
        cursor = conn.execute("SELECT COUNT(*) as count FROM conversations")
        conv_count = cursor.fetchone()['count']
        print(f"  Conversation messages in database: {conv_count}")
        
        # Check enhanced memories
        cursor = conn.execute(
            """
            SELECT memory_type, COUNT(*) as count FROM enhanced_memories
            GROUP BY memory_type
            """
        )
        memory_counts = cursor.fetchall()
        print(f"  Enhanced memories by type:")
        for row in memory_counts:
            print(f"    - {row['memory_type']}: {row['count']}")
        
        # Check beach memories specifically
        cursor = conn.execute(
            """
            SELECT character_id, memory_type, importance FROM enhanced_memories
            WHERE content LIKE '%beach%'
            """
        )
        beach_memories = cursor.fetchall()
        print(f"  Beach memories: {len(beach_memories)}")
        for memory in beach_memories:
            print(f"    - {memory['character_id']} ({memory['memory_type']}, importance: {memory['importance']})")
        
        conn.close()
    except Exception as e:
        print(f"  Error checking database: {str(e)}")

if __name__ == "__main__":
    main() 
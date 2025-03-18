#!/usr/bin/env python3
"""
Direct search fix for Flask application
"""
import os
import sys
import sqlite3
import json
import datetime

def main():
    print("Direct Search Fix")
    print("=================")
    
    # Insert the direct search route at the end of the file
    target_file = "/app/app/api/chat.py"
    
    if not os.path.exists(target_file):
        print(f"ERROR: Target file not found at {target_file}")
        return
    
    # Read the current file content
    with open(target_file, 'r') as f:
        content = f.read()
    
    # Check if the direct search route is already there
    if "def direct_search_memories" in content:
        print("Direct search route already exists")
        return
    
    # Add the direct search route
    new_route = """
@chat_bp.route('/direct-search/<character_id>', methods=['GET'])
def direct_search_memories(character_id):
    \"\"\"
    Direct search for memories - bypasses Flask context issues
    \"\"\"
    query = request.args.get('q', '')
    if not query:
        return jsonify({
            "success": False,
            "error": "Search query is required"
        }), 400
        
    try:
        # Get the limit parameter
        limit = int(request.args.get('limit', 5))
        
        # Direct database access
        db_path = '/app/data/memories.db'
        if not os.path.exists(db_path):
            # Try alternate location
            db_path = '/app/instance/memories.db'
            if not os.path.exists(db_path):
                return jsonify({
                    "success": False,
                    "error": f"Database not found at {db_path}"
                }), 500
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Get character
        cursor = conn.execute("SELECT * FROM characters WHERE id = ?", (character_id,))
        character = cursor.fetchone()
        if not character:
            return jsonify({
                "success": False,
                "error": f"Character not found: {character_id}"
            }), 404
        
        # Search for memories
        cursor = conn.execute(
            \"\"\"
            SELECT id, content, memory_type, importance, created_at, metadata
            FROM enhanced_memories
            WHERE character_id = ? AND is_hidden = 0
            AND content LIKE ?
            ORDER BY importance DESC, created_at DESC
            LIMIT ?
            \"\"\",
            (character_id, f"%{query}%", limit)
        )
        
        results = []
        for row in cursor:
            # Get metadata
            metadata = row['metadata']
            if metadata:
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            else:
                metadata = {}
            
            # Format timestamp
            timestamp = None
            if 'timestamp' in metadata:
                try:
                    dt = datetime.datetime.fromisoformat(metadata['timestamp'])
                    timestamp = dt.strftime("%B %d, %Y %I:%M %p")
                except:
                    timestamp = metadata.get('timestamp')
            
            results.append({
                'content': row['content'],
                'timestamp': timestamp,
                'score': 0.8  # Default score for text search
            })
        
        # Close connection
        conn.close()
        
        return jsonify({
            'success': True,
            'character': {
                'id': character['id'],
                'name': character['name'],
                'role': character['role']
            },
            'results': results
        })
        
    except Exception as e:
        import traceback
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
"""
    
    # Add the imports if needed
    if "import os" not in content:
        content = "import os\n" + content
    if "import sqlite3" not in content:
        content = "import sqlite3\n" + content
    if "import json" not in content:
        content = "import json\n" + content
    if "import datetime" not in content:
        content = "import datetime\n" + content
    
    # Append the new route
    with open(target_file, 'w') as f:
        f.write(content + new_route)
    
    print("Direct search route added successfully")

    # Also update the frontend to use the new route
    js_file = "/app/app/static/js/app.js"
    if os.path.exists(js_file):
        with open(js_file, 'r') as f:
            js_content = f.read()
        
        # Update the searchMemories function
        if "searchMemories" in js_content:
            print("Updating frontend to use direct search route")
            
            # Replace the API endpoint
            js_content = js_content.replace(
                "fetch(`/api/chat/search/${this.selectedCharacter.id}?q=${encodeURIComponent(query)}`)",
                "fetch(`/api/chat/direct-search/${this.selectedCharacter.id}?q=${encodeURIComponent(query)}`)"
            )
            
            with open(js_file, 'w') as f:
                f.write(js_content)
            
            print("Frontend updated to use direct search route")

if __name__ == "__main__":
    main() 
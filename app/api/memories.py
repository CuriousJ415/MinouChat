"""
Memory API
Handles memory management operations
"""
from flask import Blueprint, jsonify, request
from app.memory.sql import get_db

memories_bp = Blueprint('memories', __name__)

def init_app(app):
    """Initialize memory functions with app context"""
    app.logger.info("Memory system initialized successfully")
    return app

@memories_bp.route('/settings/<character_id>', methods=['GET'])
def get_character_memory_settings(character_id):
    """Get memory settings for a character"""
    try:
        settings = get_memory_settings(character_id)
        return jsonify({
            "success": True,
            "settings": settings
        })
    except Exception as e:
        app.logger.error(f"Error getting memory settings: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to get memory settings: {str(e)}"
        }), 500

@memories_bp.route('/settings/<character_id>', methods=['PUT'])
def update_character_memory_settings(character_id):
    """Update memory settings for a character"""
    data = request.json
    if not data:
        return jsonify({
            "success": False,
            "error": "No settings provided"
        }), 400
        
    try:
        success = update_memory_settings(character_id, data)
        if success:
            return jsonify({
                "success": True,
                "message": "Settings updated successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to update settings"
            }), 500
    except Exception as e:
        app.logger.error(f"Error updating memory settings: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to update memory settings: {str(e)}"
        }), 500

@memories_bp.route('/stats/<character_id>', methods=['GET'])
def get_character_memory_stats(character_id):
    """Get memory statistics for a character"""
    try:
        stats = get_memory_stats(character_id)
        return jsonify({
            "success": True,
            "stats": stats
        })
    except Exception as e:
        app.logger.error(f"Error getting memory stats: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to get memory stats: {str(e)}"
        }), 500

@memories_bp.route('/<character_id>/memories', methods=['GET'])
def get_character_memories(character_id):
    """Get memories for a character"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM memories WHERE character_id = ? ORDER BY timestamp DESC', (character_id,))
    rows = cursor.fetchall()
    memories = []
    for row in rows:
        memories.append({
            'id': row['id'],
            'content': row['content'],
            'timestamp': row['timestamp']
        })
    return jsonify(memories)

@memories_bp.route('/<character_id>/memories', methods=['POST'])
def add_character_memory(character_id):
    """Add a memory for a character"""
    data = request.json
    if not data or 'content' not in data:
        return jsonify({"error": "No content provided"}), 400
    db = get_db()
    cursor = db.cursor()
    cursor.execute('INSERT INTO memories (character_id, content) VALUES (?, ?)', (character_id, data['content']))
    db.commit()
    return jsonify({"success": True}), 201

@memories_bp.route('/memories/<int:character_id>', methods=['DELETE'])
def clear_memories(character_id):
    """Clear all memories for a character"""
    try:
        db = get_db()
        db.execute('DELETE FROM memories WHERE character_id = ?', (character_id,))
        db.commit()
        return jsonify({"message": "Memories cleared successfully"})
    except Exception as e:
        app.logger.error(f"Error clearing memories: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Add the reset_all_memories endpoint
@memories_bp.route('/reset/<character_id>', methods=['POST'])
def reset_all_memories(character_id):
    """
    Reset (completely delete) all memories for a character
    This differs from clear_character_memory by removing ALL types of memories,
    including enhanced memories, while keeping the character profile intact
    """
    try:
        # Connect to database
        db_path = app.config.get('DATABASE_PATH', '/app/data/memories.db')
        
        # Use enhanced memory system if available
        if HAS_ENHANCED_MEMORY:
            # Use the reset_character_memories function from enhanced_memory
            result = reset_character_memories(character_id)
            return jsonify({
                "success": True,
                "message": f"All memories have been completely reset for this character"
            })
        else:
            # Fallback to basic memory reset (using SQL directly)
            db = get_db()
            cursor = db.cursor()
            
            # Delete from conversations table
            cursor.execute('DELETE FROM conversations WHERE character_id = ?', (character_id,))
            deleted_conversations = cursor.rowcount
            
            # Delete from memories table
            cursor.execute('DELETE FROM memories WHERE character_id = ?', (character_id,))
            deleted_memories = cursor.rowcount
            
            # Try to delete from enhanced_memories table if it exists
            try:
                cursor.execute('DELETE FROM enhanced_memories WHERE character_id = ?', (character_id,))
                deleted_enhanced = cursor.rowcount
            except:
                deleted_enhanced = 0
                
            # Try to delete from vector_memories table if it exists
            try:
                cursor.execute('DELETE FROM vector_memories WHERE character_id = ?', (character_id,))
                deleted_vector = cursor.rowcount
            except:
                deleted_vector = 0
                
            db.commit()
            
            return jsonify({
                "success": True,
                "message": f"All memories have been completely reset for this character",
                "stats": {
                    "conversations_deleted": deleted_conversations,
                    "memories_deleted": deleted_memories,
                    "enhanced_memories_deleted": deleted_enhanced,
                    "vector_memories_deleted": deleted_vector
                }
            })
            
    except Exception as e:
        app.logger.error(f"Error resetting all memories: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

__all__ = ['init_app'] 
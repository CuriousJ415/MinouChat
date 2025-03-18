import datetime
import sqlite3
import os
"""
Chat API
Handles sending and receiving messages with characters
"""
from flask import jsonify, request, current_app
from app.api import chat_bp
from app.memory.sql import clear_character_memory
import json
import logging
import traceback
from app.core.character import get_character, get_characters, update_character, delete_character, create_character
from app.memory.enhanced_memory import (
    add_memory, retrieve_relevant_memories as retrieve_memories, 
    search_memories_by_text as search_memories, 
    forget_memories_by_search as forget_memories,
    reset_character_memories
)

# Try to import enhanced memory
try:
    from app.memory.enhanced_memory import HAVE_TIKTOKEN
    HAS_ENHANCED_MEMORY = True
except ImportError:
    HAS_ENHANCED_MEMORY = False

# Import chat functions
try:
    from app.core.chat import send_message, get_conversation_history
    HAS_FORGET = True
except ImportError:
    # For backward compatibility
    from app.core.chat import send_message, get_conversation_history
    HAS_FORGET = False

@chat_bp.route('/send', methods=['POST'])
def send_chat_message():
    """Send a message to a character and get a response"""
    data = request.json
    
    # Log the incoming request
    current_app.logger.info(f"Received chat request: {data}")
    
    # Validate required fields
    if not data.get('character_id'):
        current_app.logger.error("Missing character_id in request")
        return jsonify({"success": False, "error": "character_id is required"}), 400
    if not data.get('message'):
        current_app.logger.error("Missing message in request")
        return jsonify({"success": False, "error": "message is required"}), 400
    
    character_id = data.get('character_id')
    message = data.get('message')
    use_documents = data.get('use_documents', False)
    context_type = data.get('context_type', 'default')
    
    current_app.logger.info(f"Processing message for character {character_id}: {message[:50]}...")
    
    try:
        result = send_message(
            character_id, 
            message, 
            use_documents=use_documents,
            context_type=context_type
        )
        # Format the response in the way the frontend expects
        response_data = {
            "success": True,
            "response": result["message"],
            "character": result["character"]
        }
        current_app.logger.info(f"Successfully generated response: {result['message'][:50]}...")
        return jsonify(response_data)
    except ValueError as e:
        current_app.logger.error(f"Value error in chat: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error in chat: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": f"Failed to generate response: {str(e)}"}), 500

@chat_bp.route('/<character_id>/history', methods=['GET'])
def get_history(character_id):
    """Get conversation history with a character"""
    try:
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
        
        result = get_conversation_history(character_id, limit, offset)
        
        if 'error' in result:
            return jsonify({"success": False, "error": result['error']}), 404
            
        return jsonify({
            "success": True,
            "character": result["character"],
            "conversations": result["conversations"]
        })
    except Exception as e:
        current_app.logger.error(f"Error getting history: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@chat_bp.route('/<character_id>/clear', methods=['POST'])
def clear_history(character_id):
    """Clear conversation history with a character"""
    try:
        success = clear_character_memory(character_id)
        
        if not success:
            return jsonify({
                "success": False,
                "error": "Failed to clear conversation history"
            }), 500
            
        return jsonify({
            "success": True,
            "message": "Conversation history cleared"
        })
    except Exception as e:
        current_app.logger.error(f"Error clearing history: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@chat_bp.route('/search/<character_id>', methods=['GET'])
def search_character_memories(character_id):
    """Search character memories"""
    # Get query parameter
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({
            "success": False,
            "error": "Search query is required"
        }), 400
        
    try:
        from flask import g
        current_app.logger.info(f"Searching memories for character {character_id} with query: {query}")
        
        # Check if we're in an application context
        if not hasattr(g, 'app_context_set'):
            current_app.logger.warning("Creating explicit app context for search")
            g.app_context_set = True
        
        # Check if character exists
        character = get_character(character_id)
        
        if not character:
            current_app.logger.warning(f"Character not found: {character_id}")
        
        limit = int(request.args.get('limit', 5))
        
        # Set DATABASE_PATH config if not set
        if 'DATABASE_PATH' not in current_app.config:
            current_app.logger.warning("DATABASE_PATH not set, using default")
            current_app.config['DATABASE_PATH'] = '/app/data/memories.db'
            
        result = search_memories(character_id, query, limit)
        
        current_app.logger.info(f"Search completed with status: {result.get('success', False)}")
        
        if not result.get('success', False):
            current_app.logger.error(f"Search failed: {result.get('error', 'Unknown error')}")
            
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Error searching memories: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@chat_bp.route('/forget/<character_id>', methods=['POST'])
def forget_character_memories(character_id):
    """Forget (hide) memories containing specific text"""
    # Check if forget functionality is available
    if not HAS_FORGET:
        return jsonify({
            "success": False,
            "error": "Forget memories functionality not available"
        }), 501
    
    data = request.json
    if not data or 'query' not in data:
        return jsonify({
            "success": False,
            "error": "Forget query is required"
        }), 400
    
    query = data['query']
    
    try:
        result = forget_memories(character_id, query)
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Error forgetting memories: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to forget memories: {str(e)}"
        }), 500 
@chat_bp.route('/direct-search/<character_id>', methods=['GET'])
def direct_search_memories(character_id):
    """
    Direct search for memories - bypasses Flask context issues
    """
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

@chat_bp.route('/characters/<character_id>/reset_memories', methods=['POST'])
def reset_all_character_memories(character_id):
    """Reset all memories for a character while preserving the character profile."""
    try:
        # Check if character exists
        character = get_character(character_id)
        if not character:
            logging.warning(f"Character not found: {character_id}")
            return jsonify({"success": False, "error": "Character not found"}), 404
            
        # Reset all memories
        success = reset_character_memories(character_id)
        
        if success:
            logging.info(f"All memories reset for character: {character_id}")
            return jsonify({"success": True}), 200
        else:
            logging.error(f"Failed to reset memories for character: {character_id}")
            return jsonify({"success": False, "error": "Memory reset failed"}), 500
            
    except Exception as e:
        logging.error(f"Error resetting character memories: {str(e)}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

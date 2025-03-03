"""
Chat API
Handles sending and receiving messages with characters
"""
from flask import jsonify, request, current_app
from app.api import chat_bp
from app.core.chat import send_message, get_conversation_history, search_memories
from app.memory.sql import clear_character_memory

@chat_bp.route('/send', methods=['POST'])
def send_chat_message():
    """Send a message to a character and get a response"""
    data = request.json
    
    # Validate required fields
    if not data.get('character_id'):
        return jsonify({"success": False, "error": "character_id is required"}), 400
    if not data.get('message'):
        return jsonify({"success": False, "error": "message is required"}), 400
    
    character_id = data.get('character_id')
    message = data.get('message')
    
    try:
        result = send_message(character_id, message)
        # Format the response in the way the frontend expects
        return jsonify({
            "success": True,
            "response": result["message"],
            "character": result["character"]
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error in chat: {str(e)}")
        return jsonify({"success": False, "error": "Failed to generate response"}), 500

@chat_bp.route('/<character_id>/history', methods=['GET'])
def get_history(character_id):
    """Get conversation history with a character"""
    limit = request.args.get('limit', default=20, type=int)
    offset = request.args.get('offset', default=0, type=int)
    
    try:
        history = get_conversation_history(character_id, limit, offset)
        return jsonify(history)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@chat_bp.route('/<character_id>/clear', methods=['POST'])
def clear_history(character_id):
    """Clear chat history for a character"""
    try:
        # Call the function to clear history
        success = clear_character_memory(character_id)
        if success:
            return jsonify({"success": True, "message": "Chat history cleared successfully"})
        else:
            return jsonify({"success": False, "error": "Character not found"}), 404
    except Exception as e:
        current_app.logger.error(f"Error clearing chat history: {str(e)}")
        return jsonify({"success": False, "error": "Failed to clear chat history"}), 500

@chat_bp.route('/search/<character_id>', methods=['GET'])
def search_character_memories(character_id):
    """Search a character's memories for relevant information"""
    query = request.args.get('query', '')
    if not query:
        return jsonify({"error": "Search query is required"}), 400
    
    try:
        results = search_memories(character_id, query)
        return jsonify(results)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400 
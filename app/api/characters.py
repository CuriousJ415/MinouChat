"""
Character Management API
Handles CRUD operations for characters
"""
from flask import jsonify, request, current_app
from app.api import characters_bp
from app.core.character import get_characters, get_character, create_character, update_character, delete_character, reset_character_memory, restore_default_characters

# Import personalization functions
try:
    from app.core.personalization import get_user_preferences, set_user_preferences
except ImportError:
    # Fallback if module not available
    def get_user_preferences(character_id):
        return None
    def set_user_preferences(character_id, preferences):
        return False

# Import memory settings functions
try:
    from app.memory.enhanced_memory import get_memory_settings, update_memory_settings, get_memory_stats
except ImportError:
    # Fallback if module not available
    def get_memory_settings(character_id):
        return {}
    def update_memory_settings(character_id, settings):
        return False
    def get_memory_stats(character_id):
        return {}

@characters_bp.route('/', methods=['GET'])
def list_characters():
    """Get all available characters"""
    characters = get_characters()
    return jsonify(characters)

@characters_bp.route('/<character_id>', methods=['GET'])
def get_character_details(character_id):
    """Get details for a specific character"""
    character = get_character(character_id)
    if not character:
        return jsonify({"error": "Character not found"}), 404
    return jsonify(character)

@characters_bp.route('/', methods=['POST'])
def add_character():
    """Create a new character"""
    data = request.json
    current_app.logger.info(f"Creating new character with data: {data}")
    
    # Validate required fields
    required_fields = ['name', 'role', 'personality']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        current_app.logger.error(f"Missing required fields: {missing_fields}")
        return jsonify({
            "error": f"Missing required fields: {', '.join(missing_fields)}"
        }), 400
    
    try:
        character = create_character(data)
        current_app.logger.info(f"Character created successfully: {character}")
        # Return in the same format as update_character for consistency
        return jsonify({"success": True, "character": character}), 201
    except ValueError as e:
        current_app.logger.error(f"Error creating character: {str(e)}")
        return jsonify({"error": str(e)}), 400

@characters_bp.route('/<character_id>', methods=['PUT'])
def modify_character(character_id):
    """Update an existing character"""
    data = request.json
    current_app.logger.info(f"Updating character {character_id} with data: {data}")
    try:
        character = update_character(character_id, data)
        if not character:
            return jsonify({"error": "Character not found"}), 404
        current_app.logger.info(f"Character updated successfully: {character}")
        return jsonify({"success": True, "character": character})
    except ValueError as e:
        current_app.logger.error(f"Error updating character: {str(e)}")
        return jsonify({"error": str(e)}), 400

@characters_bp.route('/<character_id>', methods=['DELETE'])
def remove_character(character_id):
    """Delete a character"""
    success = delete_character(character_id)
    if not success:
        return jsonify({"error": "Character not found"}), 404
    return jsonify({"success": True})

@characters_bp.route('/<character_id>/reset', methods=['POST'])
def reset_memory(character_id):
    """Reset a character's memory"""
    success = reset_character_memory(character_id)
    if not success:
        return jsonify({"error": "Character not found"}), 404
    return jsonify({"success": True})

@characters_bp.route('/restore-defaults', methods=['POST'])
def handle_restore_defaults():
    """Restore all default characters"""
    try:
        restore_default_characters()
        characters = get_characters()
        return jsonify(characters)
    except Exception as e:
        current_app.logger.error(f"Error restoring default characters: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Add new routes for personalization

@characters_bp.route('/<character_id>/personalization', methods=['GET'])
def get_character_personalization(character_id):
    """Get personalization preferences for a character"""
    # Check if character exists
    character = get_character(character_id)
    if not character:
        return jsonify({
            "success": False,
            "message": "Character not found"
        }), 404
    
    # Get personalization preferences
    preferences = get_user_preferences(character_id)
    
    # Return empty object if no preferences set
    if not preferences:
        preferences = {
            "character_id": character_id,
            "user_name": None,
            "user_pronouns": None,
            "relationship_context": None,
            "background": None
        }
    
    return jsonify({
        "success": True,
        "preferences": preferences
    })

@characters_bp.route('/<character_id>/personalization', methods=['PUT'])
def update_character_personalization(character_id):
    """Update personalization preferences for a character"""
    data = request.json
    if not data:
        return jsonify({
            "success": False,
            "message": "No data provided"
        }), 400
    
    # Check if character exists
    character = get_character(character_id)
    if not character:
        return jsonify({
            "success": False,
            "message": "Character not found"
        }), 404
    
    # Update preferences
    success = set_user_preferences(character_id, data)
    
    return jsonify({
        "success": success,
        "message": "Personalization preferences updated" if success else "Failed to update preferences"
    })

@characters_bp.route('/<character_id>/memory-settings', methods=['GET'])
def get_character_memory_settings(character_id):
    """Get memory settings for a character"""
    # Check if character exists
    character = get_character(character_id)
    if not character:
        return jsonify({
            "success": False,
            "message": "Character not found"
        }), 404
    
    # Get memory settings
    settings = get_memory_settings(character_id)
    
    return jsonify({
        "success": True,
        "settings": settings
    })

@characters_bp.route('/<character_id>/memory-settings', methods=['PUT'])
def update_character_memory_settings(character_id):
    """Update memory settings for a character"""
    data = request.json
    if not data:
        return jsonify({
            "success": False,
            "message": "No data provided"
        }), 400
    
    # Check if character exists
    character = get_character(character_id)
    if not character:
        return jsonify({
            "success": False,
            "message": "Character not found"
        }), 404
    
    # Update settings
    success = update_memory_settings(character_id, data)
    
    return jsonify({
        "success": success,
        "message": "Memory settings updated" if success else "Failed to update settings"
    })

@characters_bp.route('/<character_id>/memory-stats', methods=['GET'])
def get_character_memory_statistics(character_id):
    """Get memory statistics for a character"""
    # Check if character exists
    character = get_character(character_id)
    if not character:
        return jsonify({
            "success": False,
            "message": "Character not found"
        }), 404
    
    # Get memory stats
    stats = get_memory_stats(character_id)
    
    return jsonify({
        "success": True,
        "stats": stats
    })

@characters_bp.route('/<character_id>/reset_memories', methods=['POST'])
def reset_memories_complete(character_id):
    """Reset all memories for a character completely, including long-term memories"""
    try:
        # Check if character exists
        character = get_character(character_id)
        if not character:
            current_app.logger.warning(f"Character not found: {character_id}")
            return jsonify({"success": False, "error": "Character not found"}), 404
            
        # Use the enhanced memory function to reset all memories
        from app.memory.enhanced_memory import reset_character_memories
        success = reset_character_memories(character_id)
        
        if success:
            current_app.logger.info(f"All memories reset for character: {character_id}")
            return jsonify({"success": True}), 200
        else:
            current_app.logger.error(f"Failed to reset memories for character: {character_id}")
            return jsonify({"success": False, "error": "Memory reset failed"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error resetting character memories: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500 
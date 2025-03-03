"""
Character Management API
Handles CRUD operations for characters
"""
from flask import jsonify, request, current_app
from app.api import characters_bp
from app.core.character import get_characters, get_character, create_character, update_character, delete_character, reset_character_memory, restore_default_characters

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
    
    # Validate required fields
    required_fields = ['name', 'role', 'personality']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return jsonify({
            "error": f"Missing required fields: {', '.join(missing_fields)}"
        }), 400
    
    try:
        character = create_character(data)
        return jsonify(character), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@characters_bp.route('/<character_id>', methods=['PUT'])
def modify_character(character_id):
    """Update an existing character"""
    data = request.json
    try:
        character = update_character(character_id, data)
        if not character:
            return jsonify({"error": "Character not found"}), 404
        return jsonify(character)
    except ValueError as e:
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
        result = restore_default_characters()
        return jsonify({"success": True, "restored": result})
    except Exception as e:
        current_app.logger.error(f"Error restoring default characters: {str(e)}")
        return jsonify({"error": str(e)}), 500 
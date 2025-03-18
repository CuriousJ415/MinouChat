"""
Settings API
Handles application and LLM configuration
"""
from flask import jsonify, request, current_app, Blueprint
from app.api import settings_bp
from app.llm.adapter import update_llm_config, get_llm_config, test_llm_connection, fetch_available_models
from app.core.character import create_character, get_characters, DEFAULT_CHARACTERS
from app.core.settings import get_llm_models, save_llm_settings
from app.llm.adapter import get_llm_adapter

@settings_bp.route('/llm', methods=['GET'])
def get_configuration():
    """Get current LLM configuration"""
    config = get_llm_config()
    
    # Create a secure copy without sensitive data for return
    secure_config = config.copy()
    if 'api_key' in secure_config:
        # Just indicate if the API key exists
        secure_config['api_key'] = secure_config['api_key'] is not None
        
    return jsonify(secure_config)

@settings_bp.route('/llm/models', methods=['GET'])
def get_models():
    try:
        provider = request.args.get('provider', current_app.config.get('LLM_PROVIDER', 'ollama'))
        models = get_llm_models(provider)
        return jsonify(models)
    except Exception as e:
        current_app.logger.error(f"Error getting LLM models: {str(e)}")
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/llm', methods=['POST'])
def update_configuration():
    """Update LLM configuration"""
    data = request.json
    
    # Validate required fields
    required_fields = ['provider']
    if data.get('provider') not in ['ollama']:
        required_fields.append('api_key')
        
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({
            "success": False,
            "error": f"Missing required fields: {', '.join(missing_fields)}"
        }), 400
    
    try:
        success = update_llm_config(data)
        return jsonify({"success": success})
    except Exception as e:
        current_app.logger.error(f"Error updating LLM config: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to save configuration: {str(e)}"
        }), 500

@settings_bp.route('/llm/test', methods=['POST'])
def test_connection():
    """Test connection to LLM provider"""
    data = request.json
    provider = data.get('provider')
    config = data.get('config', {})
    
    if not provider:
        return jsonify({
            "success": False,
            "error": "Provider is required"
        }), 400
    
    try:
        result = test_llm_connection(provider, config)
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Error testing LLM connection: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Test connection failed: {str(e)}"
        }), 500

@settings_bp.route('/setup', methods=['POST'])
def save_setup():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Required fields
        provider = data.get('provider')
        api_key = data.get('api_key')
        character_models = data.get('character_models', {})
        
        if not provider:
            return jsonify({'error': 'LLM provider is required'}), 400
            
        # Save LLM settings
        save_llm_settings(provider, api_key)
        
        # Create default characters with specified models
        characters = []
        for char in DEFAULT_CHARACTERS:
            model = character_models.get(char['id'], 'mistral')  # Default to mistral if not specified
            char_copy = char.copy()
            char_copy['model'] = model
            character = create_character(**char_copy)
            characters.append(character)
        
        return jsonify({
            'success': True,
            'message': 'Setup completed successfully',
            'characters': characters
        })
        
    except Exception as e:
        current_app.logger.error(f"Error saving setup: {str(e)}")
        return jsonify({'error': str(e)}), 500 
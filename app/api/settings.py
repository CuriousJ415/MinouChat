"""
Settings API
Handles application and LLM configuration
"""
from flask import jsonify, request, current_app
from app.api import settings_bp
from app.llm.adapter import update_llm_config, get_llm_config, test_llm_connection

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
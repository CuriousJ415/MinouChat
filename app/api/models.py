"""
Model Management API Endpoints
"""
from flask import Blueprint, jsonify, request
from app.llm.model_adapter import ModelAdapter
import logging

# Create blueprint
models_bp = Blueprint('models', __name__)

# Initialize model adapter
model_adapter = ModelAdapter()

@models_bp.route('/list', methods=['GET'])
def list_models():
    """Get list of available models"""
    try:
        models = model_adapter.get_available_models()
        return jsonify({
            'success': True,
            'models': models
        })
    except Exception as e:
        logging.error(f"Error listing models: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@models_bp.route('/current', methods=['GET'])
def get_current_model():
    """Get current model configuration"""
    try:
        config = model_adapter.get_config()
        return jsonify({
            'success': True,
            'model': config.get('model'),
            'provider': config.get('provider'),
            'api_url': config.get('api_url')
        })
    except Exception as e:
        logging.error(f"Error getting current model: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@models_bp.route('/switch', methods=['POST'])
def switch_model():
    """Switch to a different model"""
    try:
        data = request.get_json()
        model_name = data.get('model')
        
        if not model_name:
            return jsonify({
                'success': False,
                'error': 'Model name is required'
            }), 400
            
        success = model_adapter.switch_model(model_name)
        if success:
            return jsonify({
                'success': True,
                'message': f'Switched to model: {model_name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to switch to model: {model_name}'
            }), 400
    except Exception as e:
        logging.error(f"Error switching model: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@models_bp.route('/test', methods=['POST'])
def test_connection():
    """Test connection to current model"""
    try:
        result = model_adapter.test_connection()
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error testing connection: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 
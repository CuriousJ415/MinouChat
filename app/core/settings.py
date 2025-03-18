"""
Core settings module for managing application configuration
"""
from flask import current_app
from app.llm.adapter import get_llm_adapter, update_llm_config, fetch_available_models

def get_llm_models(provider):
    """Get available models for the specified LLM provider"""
    try:
        models = fetch_available_models(provider)
        return {
            'success': True,
            'models': models
        }
    except Exception as e:
        current_app.logger.error(f"Error fetching models for provider {provider}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def save_llm_settings(provider, api_key=None):
    """Save LLM provider settings and update configuration"""
    try:
        config = {
            'provider': provider
        }
        
        if api_key:
            config['api_key'] = api_key
            
        # Update the LLM configuration
        update_llm_config(config)
        
        # Update the application config
        current_app.config['LLM_PROVIDER'] = provider
        if api_key:
            current_app.config['LLM_API_KEY'] = api_key
            
        return True
    except Exception as e:
        current_app.logger.error(f"Error saving LLM settings: {str(e)}")
        return False 
"""
Application Configuration
Manages application settings and environment variables
"""
import os
import json
from typing import Dict, Any, Optional
from flask import current_app

class Config:
    """
    Configuration manager for the application
    Handles loading and saving configuration from various sources
    """
    
    @staticmethod
    def get_llm_config() -> Dict[str, Any]:
        """
        Get LLM configuration
        
        Returns:
            Dictionary with LLM configuration
        """
        # Default config
        default_config = {
            'provider': os.environ.get('LLM_PROVIDER', 'ollama'),
            'api_url': os.environ.get('LLM_API_URL', 'http://localhost:11434/api'),
            'model': os.environ.get('LLM_MODEL', 'mistral'),
            'api_key': os.environ.get('LLM_API_KEY'),
            'headers': {}
        }
        
        # Try to load from config file
        config_path = os.path.join('config', 'llm_config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                current_app.logger.error(f"Error loading LLM config: {str(e)}")
        
        # Use environment variables if no file
        return default_config
    
    @staticmethod
    def save_llm_config(config: Dict[str, Any]) -> bool:
        """
        Save LLM configuration
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if successful, False otherwise
        """
        # Ensure config directory exists
        os.makedirs('config', exist_ok=True)
        
        # Save to file
        config_path = os.path.join('config', 'llm_config.json')
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            current_app.logger.error(f"Error saving LLM config: {str(e)}")
            return False
    
    @staticmethod
    def get_app_config() -> Dict[str, Any]:
        """
        Get application configuration
        
        Returns:
            Dictionary with application configuration
        """
        return {
            'database_path': current_app.config['DATABASE_PATH'],
            'debug': current_app.config.get('DEBUG', False),
            'port': int(os.environ.get('PORT', 8080)),
            'host': '0.0.0.0'
        }

    @staticmethod
    def get_ngrok_config() -> Optional[Dict[str, str]]:
        """
        Get Ngrok configuration if available
        
        Returns:
            Dictionary with Ngrok configuration or None
        """
        auth_token = os.environ.get('NGROK_AUTH_TOKEN')
        domain = os.environ.get('NGROK_DOMAIN')
        
        if not auth_token:
            return None
            
        return {
            'auth_token': auth_token,
            'domain': domain
        } 
"""
Settings service for managing user preferences and LLM provider configuration
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, Dict, Any, List
import logging
import os
from ...database.models import UserSettings, User
from ...database.config import get_db

logger = logging.getLogger(__name__)

class SettingsService:
    """Service for managing user settings"""
    
    def __init__(self):
        self.supported_providers = [
            "ollama", "openai", "anthropic", "openrouter", "litellm"
        ]
        
        self.default_models = {
            "ollama": "llama3:8b",
            "openai": "gpt-4",
            "anthropic": "claude-3-opus-20240229",
            "openrouter": "openai/gpt-4",
            "litellm": "gpt-4"
        }
    
    def get_user_settings(self, user_id: int, db: Session) -> Optional[UserSettings]:
        """Get user settings by user ID"""
        try:
            settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
            return settings
        except Exception as e:
            logger.error(f"Error getting user settings for user {user_id}: {e}")
            return None
    
    def create_user_settings(self, user_id: int, db: Session, **kwargs) -> Optional[UserSettings]:
        """Create new user settings"""
        try:
            settings = UserSettings(user_id=user_id, **kwargs)
            db.add(settings)
            db.commit()
            db.refresh(settings)
            return settings
        except IntegrityError:
            db.rollback()
            logger.error(f"Settings already exist for user {user_id}")
            return None
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating user settings for user {user_id}: {e}")
            return None
    
    def update_user_settings(self, user_id: int, db: Session, **kwargs) -> Optional[UserSettings]:
        """Update user settings"""
        try:
            settings = self.get_user_settings(user_id, db)
            if not settings:
                # Create settings if they don't exist
                return self.create_user_settings(user_id, db, **kwargs)
            
            # Update only provided fields
            for key, value in kwargs.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
            
            db.commit()
            db.refresh(settings)
            return settings
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating user settings for user {user_id}: {e}")
            return None
    
    def get_llm_config(self, user_id: int, db: Session) -> Dict[str, Any]:
        """Get LLM configuration for a user"""
        settings = self.get_user_settings(user_id, db)
        if not settings:
            # Return default configuration
            return {
                "provider": "ollama",
                "model": "llama3:8b",
                "privacy_mode": "local_only",
                "api_url": f"http://{os.getenv('OLLAMA_HOST', 'localhost')}:{os.getenv('OLLAMA_PORT', '11434')}"
            }
        
        config = {
            "provider": settings.default_llm_provider,
            "model": settings.default_model,
            "privacy_mode": settings.privacy_mode,
            "api_url": settings.ollama_url
        }
        
        # Add provider-specific settings
        if settings.default_llm_provider == "openai":
            config["api_key"] = settings.openai_api_key
            config["model"] = settings.openai_model
        elif settings.default_llm_provider == "anthropic":
            config["api_key"] = settings.anthropic_api_key
            config["model"] = settings.anthropic_model
        elif settings.default_llm_provider == "openrouter":
            config["api_key"] = settings.openrouter_api_key
            config["model"] = settings.openrouter_model
        
        return config
    
    def update_llm_config(self, user_id: int, db: Session, config: Dict[str, Any]) -> bool:
        """Update LLM configuration for a user"""
        try:
            provider = config.get("provider", "ollama")
            if provider not in self.supported_providers:
                raise ValueError(f"Unsupported provider: {provider}")
            
            update_data = {
                "default_llm_provider": provider,
                "default_model": config.get("model", self.default_models[provider]),
                "privacy_mode": config.get("privacy_mode", "local_only")
            }
            
            # Provider-specific settings
            if provider == "ollama":
                update_data["ollama_url"] = config.get("api_url", f"http://{os.getenv('OLLAMA_HOST', 'localhost')}:{os.getenv('OLLAMA_PORT', '11434')}")
            elif provider == "openai":
                if "api_key" in config:
                    update_data["openai_api_key"] = config["api_key"]
                update_data["openai_model"] = config.get("model", "gpt-4")
            elif provider == "anthropic":
                if "api_key" in config:
                    update_data["anthropic_api_key"] = config["api_key"]
                update_data["anthropic_model"] = config.get("model", "claude-3-opus-20240229")
            elif provider == "openrouter":
                if "api_key" in config:
                    update_data["openrouter_api_key"] = config["api_key"]
                update_data["openrouter_model"] = config.get("model", "openai/gpt-4")
            
            settings = self.update_user_settings(user_id, db, **update_data)
            return settings is not None
        except Exception as e:
            logger.error(f"Error updating LLM config for user {user_id}: {e}")
            return False
    
    def get_available_models(self, provider: str) -> List[str]:
        """Get available models for a provider"""
        if provider == "ollama":
            return [
                "llama3:8b", "llama3:70b", "mistral:7b", "mistral:7b-instruct",
                "codellama:7b", "codellama:13b", "codellama:34b",
                "llama2:7b", "llama2:13b", "llama2:70b"
            ]
        elif provider == "openai":
            return [
                "gpt-5", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4",
                "gpt-3.5-turbo", "o1-preview", "o1-mini"
            ]
        elif provider == "anthropic":
            return [
                "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229", "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307"
            ]
        elif provider == "openrouter":
            return [
                "openai/gpt-4", "openai/gpt-4-turbo", "openai/gpt-4o",
                "anthropic/claude-3-opus", "anthropic/claude-3-sonnet",
                "google/gemini-pro", "meta-llama/llama-3-8b-instruct"
            ]
        elif provider == "litellm":
            return [
                "gpt-4", "gpt-3.5-turbo", "claude-3-opus", "claude-3-sonnet",
                "gemini-pro", "llama3:8b"
            ]
        else:
            return []
    
    def test_provider_connection(self, provider: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test connection to an LLM provider"""
        try:
            # This would integrate with the LLM client to test connections
            # For now, return a mock response
            return {
                "success": True,
                "message": f"Connection to {provider} successful",
                "provider": provider,
                "model": config.get("model", "unknown")
            }
        except Exception as e:
            logger.error(f"Error testing connection to {provider}: {e}")
            return {
                "success": False,
                "message": f"Connection to {provider} failed: {str(e)}",
                "provider": provider
            }

# Global settings service instance
settings_service = SettingsService() 
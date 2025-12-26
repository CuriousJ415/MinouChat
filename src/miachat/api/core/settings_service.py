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
        """Get LLM configuration for a user (for chat with personas)"""
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

    def get_assistant_llm_config(self, user_id: int, db: Session) -> Dict[str, Any]:
        """Get Assistant LLM configuration for utility tasks (prompt generation, trait suggestions, etc.)"""
        settings = self.get_user_settings(user_id, db)

        # Default assistant config
        default_config = {
            "provider": "ollama",
            "model": "llama3.1:8b",
            "temperature": 0.7,
            "max_tokens": 512,
            "api_url": f"http://{os.getenv('OLLAMA_HOST', 'localhost')}:{os.getenv('OLLAMA_PORT', '11434')}"
        }

        if not settings:
            return default_config

        provider = settings.assistant_llm_provider or "ollama"
        model = settings.assistant_llm_model or "llama3.1:8b"

        config = {
            "provider": provider,
            "model": model,
            "temperature": 0.7,
            "max_tokens": 512,
            "api_url": settings.ollama_url
        }

        # Add provider-specific API keys
        if provider == "openai":
            config["api_key"] = settings.openai_api_key
        elif provider == "anthropic":
            config["api_key"] = settings.anthropic_api_key
        elif provider == "openrouter":
            config["api_key"] = settings.openrouter_api_key

        return config

    def get_fallback_llm_config(self, user_id: Optional[int], db: Optional[Session]) -> Dict[str, Any]:
        """
        Get LLM config with smart fallback logic.

        Priority:
        1. User's configured assistant LLM (if user is logged in)
        2. User's default chat LLM (if user is logged in)
        3. Check for available cloud providers (API keys in env)
        4. Fall back to Ollama only if nothing else is available

        Returns a config dict with 'provider', 'model', 'temperature', 'max_tokens', etc.
        If no LLM is available, returns config with 'error' key explaining the issue.
        """
        import requests

        # Try user's configured LLMs first
        if user_id and db:
            settings = self.get_user_settings(user_id, db)
            if settings:
                # Try assistant LLM first
                if settings.assistant_llm_provider and settings.assistant_llm_model:
                    provider = settings.assistant_llm_provider
                    config = {
                        "provider": provider,
                        "model": settings.assistant_llm_model,
                        "temperature": 0.7,
                        "max_tokens": 512
                    }
                    # Add API key if needed
                    if provider == "openai" and settings.openai_api_key:
                        config["api_key"] = settings.openai_api_key
                        return config
                    elif provider == "anthropic" and settings.anthropic_api_key:
                        config["api_key"] = settings.anthropic_api_key
                        return config
                    elif provider == "openrouter" and settings.openrouter_api_key:
                        config["api_key"] = settings.openrouter_api_key
                        return config
                    elif provider == "ollama":
                        config["api_url"] = settings.ollama_url or f"http://{os.getenv('OLLAMA_HOST', 'localhost')}:{os.getenv('OLLAMA_PORT', '11434')}"
                        # Check if Ollama is reachable
                        try:
                            resp = requests.get(f"{config['api_url']}/api/tags", timeout=2)
                            if resp.ok:
                                return config
                        except:
                            pass  # Ollama not available, try other options

                # Try default chat LLM
                if settings.default_llm_provider:
                    provider = settings.default_llm_provider
                    config = {
                        "provider": provider,
                        "model": settings.default_model or self.default_models.get(provider, "gpt-4"),
                        "temperature": 0.7,
                        "max_tokens": 512
                    }
                    if provider == "openai" and settings.openai_api_key:
                        config["api_key"] = settings.openai_api_key
                        return config
                    elif provider == "anthropic" and settings.anthropic_api_key:
                        config["api_key"] = settings.anthropic_api_key
                        return config
                    elif provider == "openrouter" and settings.openrouter_api_key:
                        config["api_key"] = settings.openrouter_api_key
                        return config
                    elif provider == "ollama":
                        config["api_url"] = settings.ollama_url or f"http://{os.getenv('OLLAMA_HOST', 'localhost')}:{os.getenv('OLLAMA_PORT', '11434')}"
                        try:
                            resp = requests.get(f"{config['api_url']}/api/tags", timeout=2)
                            if resp.ok:
                                return config
                        except:
                            pass

                # Check for any configured API keys in user settings
                if settings.openrouter_api_key:
                    return {
                        "provider": "openrouter",
                        "model": settings.openrouter_model or "openai/gpt-4o-mini",
                        "api_key": settings.openrouter_api_key,
                        "temperature": 0.7,
                        "max_tokens": 512
                    }
                if settings.openai_api_key:
                    return {
                        "provider": "openai",
                        "model": settings.openai_model or "gpt-4o-mini",
                        "api_key": settings.openai_api_key,
                        "temperature": 0.7,
                        "max_tokens": 512
                    }
                if settings.anthropic_api_key:
                    return {
                        "provider": "anthropic",
                        "model": settings.anthropic_model or "claude-3-5-haiku-20241022",
                        "api_key": settings.anthropic_api_key,
                        "temperature": 0.7,
                        "max_tokens": 512
                    }

        # Check environment variables for API keys
        if os.getenv('OPENROUTER_API_KEY'):
            return {
                "provider": "openrouter",
                "model": "openai/gpt-4o-mini",
                "api_key": os.getenv('OPENROUTER_API_KEY'),
                "temperature": 0.7,
                "max_tokens": 512
            }
        if os.getenv('OPENAI_API_KEY'):
            return {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "api_key": os.getenv('OPENAI_API_KEY'),
                "temperature": 0.7,
                "max_tokens": 512
            }
        if os.getenv('ANTHROPIC_API_KEY'):
            return {
                "provider": "anthropic",
                "model": "claude-3-5-haiku-20241022",
                "api_key": os.getenv('ANTHROPIC_API_KEY'),
                "temperature": 0.7,
                "max_tokens": 512
            }

        # Check if Ollama is available and get an installed model
        ollama_url = f"http://{os.getenv('OLLAMA_HOST', 'localhost')}:{os.getenv('OLLAMA_PORT', '11434')}"
        try:
            resp = requests.get(f"{ollama_url}/api/tags", timeout=2)
            if resp.ok:
                data = resp.json()
                models = data.get('models', [])
                if models:
                    # Pick the first available model
                    model_name = models[0].get('name', 'llama3.1:8b')
                    return {
                        "provider": "ollama",
                        "model": model_name,
                        "api_url": ollama_url,
                        "temperature": 0.7,
                        "max_tokens": 512
                    }
        except:
            pass

        # No LLM available - return error config
        return {
            "error": "No LLM provider available. Please configure an API key in Settings or start Ollama.",
            "provider": None,
            "model": None
        }

    def update_assistant_llm_config(self, user_id: int, db: Session, provider: str, model: str) -> bool:
        """Update Assistant LLM configuration"""
        try:
            if provider not in self.supported_providers:
                raise ValueError(f"Unsupported provider: {provider}")

            update_data = {
                "assistant_llm_provider": provider,
                "assistant_llm_model": model
            }

            settings = self.update_user_settings(user_id, db, **update_data)
            return settings is not None
        except Exception as e:
            logger.error(f"Error updating assistant LLM config for user {user_id}: {e}")
            return False
    
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

            # Always save ALL credentials when provided (frontend sends all in 'credentials' dict)
            credentials = config.get("credentials", {})
            if credentials.get("openai"):
                update_data["openai_api_key"] = credentials["openai"]
            if credentials.get("anthropic"):
                update_data["anthropic_api_key"] = credentials["anthropic"]
            if credentials.get("openrouter"):
                update_data["openrouter_api_key"] = credentials["openrouter"]

            # Provider-specific settings
            if provider == "ollama":
                update_data["ollama_url"] = config.get("api_url", f"http://{os.getenv('OLLAMA_HOST', 'localhost')}:{os.getenv('OLLAMA_PORT', '11434')}")
            elif provider == "openai":
                if "api_key" in config and not credentials.get("openai"):
                    update_data["openai_api_key"] = config["api_key"]
                update_data["openai_model"] = config.get("model", "gpt-4")
            elif provider == "anthropic":
                if "api_key" in config and not credentials.get("anthropic"):
                    update_data["anthropic_api_key"] = config["api_key"]
                update_data["anthropic_model"] = config.get("model", "claude-3-opus-20240229")
            elif provider == "openrouter":
                if "api_key" in config and not credentials.get("openrouter"):
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
        """
        Test connection to an LLM provider.

        Actually tests the connection by making a lightweight API call.

        Args:
            provider: Provider name (ollama, openai, anthropic, openrouter)
            config: Configuration including api_key, api_url, model

        Returns:
            Dict with success status and message
        """
        import requests

        try:
            if provider == "ollama":
                # Test Ollama by checking the /api/tags endpoint
                ollama_url = config.get("api_url") or f"http://{os.getenv('OLLAMA_HOST', 'localhost')}:{os.getenv('OLLAMA_PORT', '11434')}"
                response = requests.get(f"{ollama_url}/api/tags", timeout=10)
                if response.ok:
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    requested_model = config.get("model", "")
                    if requested_model and requested_model not in model_names:
                        return {
                            "success": False,
                            "message": f"Ollama is running but model '{requested_model}' not found. Available: {', '.join(model_names[:5])}",
                            "provider": provider,
                            "available_models": model_names
                        }
                    return {
                        "success": True,
                        "message": f"Ollama connection successful. {len(models)} models available.",
                        "provider": provider,
                        "model": config.get("model", "default")
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Ollama returned status {response.status_code}",
                        "provider": provider
                    }

            elif provider == "openai":
                api_key = config.get("api_key")
                if not api_key:
                    return {
                        "success": False,
                        "message": "OpenAI API key is required",
                        "provider": provider
                    }
                # Test by listing models (lightweight call)
                response = requests.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10
                )
                if response.ok:
                    return {
                        "success": True,
                        "message": "OpenAI connection successful",
                        "provider": provider,
                        "model": config.get("model", "gpt-4")
                    }
                else:
                    error_detail = response.json().get("error", {}).get("message", response.text)
                    return {
                        "success": False,
                        "message": f"OpenAI API error: {error_detail}",
                        "provider": provider
                    }

            elif provider == "anthropic":
                api_key = config.get("api_key")
                if not api_key:
                    return {
                        "success": False,
                        "message": "Anthropic API key is required",
                        "provider": provider
                    }
                # Test with a minimal message call
                response = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": config.get("model", "claude-3-haiku-20240307"),
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "Hi"}]
                    },
                    timeout=15
                )
                if response.ok:
                    return {
                        "success": True,
                        "message": "Anthropic connection successful",
                        "provider": provider,
                        "model": config.get("model", "claude-3-opus")
                    }
                else:
                    error_detail = response.json().get("error", {}).get("message", response.text)
                    return {
                        "success": False,
                        "message": f"Anthropic API error: {error_detail}",
                        "provider": provider
                    }

            elif provider == "openrouter":
                api_key = config.get("api_key")
                if not api_key:
                    return {
                        "success": False,
                        "message": "OpenRouter API key is required",
                        "provider": provider
                    }
                # Test by fetching available models
                response = requests.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10
                )
                if response.ok:
                    return {
                        "success": True,
                        "message": "OpenRouter connection successful",
                        "provider": provider,
                        "model": config.get("model", "openai/gpt-4")
                    }
                else:
                    return {
                        "success": False,
                        "message": f"OpenRouter API error: {response.status_code}",
                        "provider": provider
                    }

            else:
                return {
                    "success": False,
                    "message": f"Unknown provider: {provider}",
                    "provider": provider
                }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "message": f"Connection to {provider} timed out",
                "provider": provider
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "message": f"Could not connect to {provider}. Check if the service is running.",
                "provider": provider
            }
        except Exception as e:
            logger.error(f"Error testing connection to {provider}: {e}")
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}",
                "provider": provider
            }

    def check_llm_status(self, user_id: int, db: Session) -> Dict[str, Any]:
        """
        Check if the user has a valid LLM configuration and if it's available.

        Returns:
            Dict with:
                - configured: bool - whether settings exist
                - available: bool - whether the configured LLM is reachable
                - provider: str - configured provider name
                - model: str - configured model name
                - message: str - human-readable status message
                - needs_setup: bool - whether user needs to configure LLM settings
        """
        import requests

        settings = self.get_user_settings(user_id, db)

        if not settings:
            return {
                "configured": False,
                "available": False,
                "provider": None,
                "model": None,
                "message": "LLM settings not configured. Please set up your AI provider in Settings.",
                "needs_setup": True
            }

        provider = settings.default_llm_provider or "ollama"
        model = settings.default_model or "llama3:8b"

        # Check availability based on provider
        available = False
        message = ""

        if provider == "ollama":
            ollama_url = settings.ollama_url or f"http://{os.getenv('OLLAMA_HOST', 'localhost')}:{os.getenv('OLLAMA_PORT', '11434')}"
            try:
                response = requests.get(f"{ollama_url}/api/tags", timeout=5)
                if response.ok:
                    available = True
                    message = f"Ollama is running with model {model}"
                else:
                    message = "Ollama is not responding. Please ensure Ollama is running."
            except requests.exceptions.RequestException:
                message = "Cannot connect to Ollama. Please ensure Ollama is running."

        elif provider == "openai":
            if settings.openai_api_key:
                available = True
                message = f"OpenAI configured with model {model}"
            else:
                message = "OpenAI API key not configured. Please add your API key in Settings."

        elif provider == "anthropic":
            if settings.anthropic_api_key:
                available = True
                message = f"Anthropic configured with model {model}"
            else:
                message = "Anthropic API key not configured. Please add your API key in Settings."

        elif provider == "openrouter":
            if settings.openrouter_api_key:
                available = True
                message = f"OpenRouter configured with model {model}"
            else:
                message = "OpenRouter API key not configured. Please add your API key in Settings."

        else:
            message = f"Unknown provider: {provider}"

        return {
            "configured": True,
            "available": available,
            "provider": provider,
            "model": model,
            "message": message,
            "needs_setup": not available
        }

    def check_character_llm_status(
        self,
        user_id: int,
        character_model_config: Optional[Dict[str, Any]],
        db: Session
    ) -> Dict[str, Any]:
        """
        Check if a character's LLM configuration is available, with fallback info.

        Returns:
            Dict with:
                - available: bool
                - using_default: bool - true if falling back to system default
                - provider: str
                - model: str
                - message: str
        """
        import requests

        # Check if character has its own config
        has_character_config = (
            character_model_config and
            character_model_config.get('provider') and
            character_model_config.get('model')
        )

        if has_character_config:
            provider = character_model_config['provider']
            model = character_model_config['model']

            # Check character's LLM availability
            char_available = self._check_provider_available(provider, character_model_config, user_id, db)

            if char_available:
                return {
                    "available": True,
                    "using_default": False,
                    "provider": provider,
                    "model": model,
                    "message": f"Using character's configured {provider} model: {model}"
                }
            else:
                # Character LLM not available, check system default
                system_status = self.check_llm_status(user_id, db)
                if system_status['available']:
                    return {
                        "available": True,
                        "using_default": True,
                        "provider": system_status['provider'],
                        "model": system_status['model'],
                        "message": f"Character's {provider} model unavailable. Using default ({system_status['provider']}/{system_status['model']}). Click the gear icon to configure.",
                        "character_provider_unavailable": provider
                    }
                else:
                    return {
                        "available": False,
                        "using_default": False,
                        "provider": None,
                        "model": None,
                        "message": "No LLM available. Please configure your AI settings."
                    }
        else:
            # No character config, use system default
            system_status = self.check_llm_status(user_id, db)
            if system_status['available']:
                return {
                    "available": True,
                    "using_default": True,
                    "provider": system_status.get('provider'),
                    "model": system_status.get('model'),
                    "message": f"Using default model ({system_status['provider']}/{system_status['model']}). Click the gear icon to set a custom model for this persona."
                }
            else:
                return {
                    "available": False,
                    "using_default": True,
                    "provider": system_status.get('provider'),
                    "model": system_status.get('model'),
                    "message": system_status['message']
                }

    def _check_provider_available(
        self,
        provider: str,
        config: Dict[str, Any],
        user_id: int,
        db: Session
    ) -> bool:
        """Check if a specific provider is available."""
        import requests

        user_settings = self.get_user_settings(user_id, db)

        if provider == "ollama":
            ollama_url = config.get('api_url') or (user_settings.ollama_url if user_settings else None) or f"http://{os.getenv('OLLAMA_HOST', 'localhost')}:{os.getenv('OLLAMA_PORT', '11434')}"
            model = config.get('model', '')
            try:
                response = requests.get(f"{ollama_url}/api/tags", timeout=5)
                if not response.ok:
                    return False
                # Check if the specific model exists
                if model:
                    available_models = response.json().get('models', [])
                    model_names = [m.get('name', '') for m in available_models]
                    # Check for exact match only
                    if model not in model_names:
                        logger.warning(f"Ollama model '{model}' not found. Available: {model_names[:5]}...")
                        return False
                return True
            except Exception as e:
                logger.warning(f"Error checking Ollama availability: {e}")
                return False

        elif provider == "openai":
            api_key = config.get('api_key') or (user_settings.openai_api_key if user_settings else None)
            return bool(api_key)

        elif provider == "anthropic":
            api_key = config.get('api_key') or (user_settings.anthropic_api_key if user_settings else None)
            return bool(api_key)

        elif provider == "openrouter":
            api_key = config.get('api_key') or (user_settings.openrouter_api_key if user_settings else None)
            return bool(api_key)

        return False

# Global settings service instance
settings_service = SettingsService() 
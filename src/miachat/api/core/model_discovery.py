"""
Privacy-First Model Discovery System

Core Principles:
1. Local discovery first (Ollama)
2. Configuration-driven external models (no automatic API calls)
3. User-controlled privacy levels
4. Graceful fallbacks for offline usage
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ModelDiscoveryService:
    """Privacy-respecting model discovery service."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.models_config_file = self.config_dir / "models.json"
        self.cache_file = self.config_dir / "model_cache.json"
        self.cache_ttl_hours = 24
        
    def get_available_models(self, privacy_mode: str = "local_only") -> Dict[str, List[str]]:
        """
        Get available models respecting privacy preferences.
        
        Args:
            privacy_mode: "local_only", "cloud_allowed", or "hybrid"
        """
        models = {}
        
        # Always discover local Ollama models (privacy-safe)
        models['ollama'] = self._discover_ollama_models()
        
        if privacy_mode == "local_only":
            # Only return local models, use static lists for cloud providers
            models.update(self._get_static_cloud_models())
        else:
            # Load from configuration file (user-controlled)
            models.update(self._get_configured_models())
            
        return models
    
    def _discover_ollama_models(self) -> List[str]:
        """Discover locally installed Ollama models."""
        try:
            import requests
            
            ollama_host = os.getenv('OLLAMA_HOST', 'localhost')
            ollama_port = os.getenv('OLLAMA_PORT', '11434')
            
            # Try Docker internal network first
            if ollama_host == 'localhost':
                ollama_host = 'host.docker.internal'
                
            url = f"http://{ollama_host}:{ollama_port}/api/tags"
            
            response = requests.get(url, timeout=5)
            if response.ok:
                data = response.json()
                models = [model['name'] for model in data.get('models', [])]
                logger.info(f"Discovered {len(models)} local Ollama models")
                return sorted(models)
                
        except Exception as e:
            logger.warning(f"Could not discover Ollama models: {e}")
        
        # Fallback to common models
        return [
            'llama3.1:8b', 'llama3.1:latest', 'llama3:8b',
            'mistral:latest', 'mistral:7b', 'codellama:7b'
        ]
    
    def _get_static_cloud_models(self) -> Dict[str, List[str]]:
        """Return static cloud model lists for privacy mode."""
        return {
            'openai': [
                'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4',
                'gpt-3.5-turbo', 'o1-preview', 'o1-mini'
            ],
            'anthropic': [
                'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022',
                'claude-3-opus-20240229', 'claude-3-sonnet-20240229',
                'claude-3-haiku-20240307'
            ],
            'openrouter': [
                'openai/gpt-4o', 'openai/gpt-4o-mini',
                'anthropic/claude-3.5-sonnet', 'google/gemini-pro-1.5',
                'meta-llama/llama-3.1-70b-instruct'
            ]
        }
    
    def _get_configured_models(self) -> Dict[str, List[str]]:
        """Load models from configuration file."""
        try:
            if self.models_config_file.exists():
                with open(self.models_config_file, 'r') as f:
                    config = json.load(f)
                return config.get('models', self._get_static_cloud_models())
        except Exception as e:
            logger.error(f"Error loading models config: {e}")
        
        return self._get_static_cloud_models()
    
    def update_models_config(self, models: Dict[str, List[str]]) -> bool:
        """Update the models configuration file."""
        try:
            config = {
                'models': models,
                'updated_at': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            with open(self.models_config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
            logger.info("Models configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating models config: {e}")
            return False
    
    def get_model_recommendations(self) -> Dict[str, Any]:
        """Get privacy-aware model recommendations."""
        return {
            "privacy_first": {
                "provider": "ollama",
                "models": ["llama3.1:8b", "mistral:latest"],
                "description": "100% local processing, no data leaves your device",
                "privacy_level": "maximum"
            },
            "balanced_performance": {
                "providers": ["ollama", "openai"],
                "models": {
                    "ollama": ["llama3.1:8b"],
                    "openai": ["gpt-4o-mini"]  # Cost-effective cloud option
                },
                "description": "Local for private conversations, cloud for complex tasks",
                "privacy_level": "selective"
            },
            "maximum_capability": {
                "providers": ["openai", "anthropic"],
                "models": {
                    "openai": ["gpt-4o", "o1-preview"],
                    "anthropic": ["claude-3-5-sonnet-20241022"]
                },
                "description": "Cutting-edge models for complex reasoning",
                "privacy_level": "cloud",
                "privacy_note": "All conversations processed by external providers"
            }
        }
    
    def get_privacy_info(self) -> Dict[str, Any]:
        """Get detailed privacy information for each provider."""
        return {
            'ollama': {
                'privacy_level': 'maximum',
                'data_location': 'local_only',
                'description': 'All processing happens on your device. No data transmitted.',
                'external_calls': False,
                'recommended': True
            },
            'openai': {
                'privacy_level': 'cloud',
                'data_location': 'openai_servers',
                'description': 'Messages sent to OpenAI servers for processing.',
                'external_calls': True,
                'data_retention': 'See OpenAI privacy policy',
                'encryption': 'In transit and at rest'
            },
            'anthropic': {
                'privacy_level': 'cloud',
                'data_location': 'anthropic_servers',
                'description': 'Messages sent to Anthropic servers for processing.',
                'external_calls': True,
                'data_retention': 'See Anthropic privacy policy',
                'encryption': 'In transit and at rest'
            },
            'openrouter': {
                'privacy_level': 'cloud_proxy',
                'data_location': 'multiple_providers',
                'description': 'Messages routed through OpenRouter to various providers.',
                'external_calls': True,
                'data_retention': 'Varies by underlying provider',
                'note': 'Additional privacy considerations for proxy service'
            }
        }

# Global instance
model_discovery = ModelDiscoveryService()
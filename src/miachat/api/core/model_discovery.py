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
        
    def get_available_models(self, privacy_mode: str = "local_only", api_keys: Dict[str, str] = None) -> Dict[str, List[str]]:
        """
        Get available models respecting privacy preferences.

        Args:
            privacy_mode: "local_only", "cloud_allowed", or "hybrid"
            api_keys: Optional dict with keys 'openrouter', 'openai', 'anthropic' for dynamic discovery
        """
        if api_keys is None:
            api_keys = {}

        models = {}

        # Always discover local Ollama models (privacy-safe)
        models['ollama'] = self._discover_ollama_models()

        if privacy_mode == "local_only":
            # Only return local models, use static lists for cloud providers
            models.update(self._get_static_cloud_models(api_keys))
        else:
            # Load from configuration file (user-controlled)
            models.update(self._get_configured_models(api_keys))

        return models
    
    def _discover_ollama_models(self) -> List[str]:
        """Discover locally installed Ollama models."""
        try:
            import requests
            
            ollama_host = os.getenv('OLLAMA_HOST', 'localhost')
            ollama_port = os.getenv('OLLAMA_PORT', '11434')

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
    
    def _discover_openai_models(self, api_key: str = None) -> List[str]:
        """Fetch available models from OpenAI API."""
        try:
            import requests

            if not api_key:
                api_key = os.getenv('OPENAI_API_KEY', '')
            if not api_key:
                logger.warning("No OpenAI API key found, using static model list")
                return self._get_static_openai_models()

            response = requests.get(
                'https://api.openai.com/v1/models',
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=10
            )

            if response.ok:
                data = response.json()
                # Filter to only include chat models (gpt-* and o1-*)
                all_models = [model['id'] for model in data.get('data', [])]
                chat_models = [m for m in all_models if m.startswith(('gpt-', 'o1-')) and 'instruct' not in m]
                logger.info(f"Discovered {len(chat_models)} OpenAI chat models")
                return sorted(chat_models)
            else:
                logger.warning(f"OpenAI API returned {response.status_code}")

        except Exception as e:
            logger.warning(f"Could not discover OpenAI models: {e}")

        return self._get_static_openai_models()

    def _get_static_openai_models(self) -> List[str]:
        """Fallback static list of OpenAI models."""
        return [
            # Top tier - recommended for complex tasks
            'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo',
            # Reasoning models
            'o1-preview', 'o1-mini', 'o1',
            # Legacy but still useful
            'gpt-4', 'gpt-3.5-turbo'
        ]

    def _discover_anthropic_models(self, api_key: str = None) -> List[str]:
        """Fetch available models from Anthropic API."""
        try:
            import requests

            if not api_key:
                api_key = os.getenv('ANTHROPIC_API_KEY', '')
            if not api_key:
                logger.warning("No Anthropic API key found, using static model list")
                return self._get_static_anthropic_models()

            response = requests.get(
                'https://api.anthropic.com/v1/models',
                headers={
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01'
                },
                timeout=10
            )

            if response.ok:
                data = response.json()
                models = [model['id'] for model in data.get('data', [])]
                logger.info(f"Discovered {len(models)} Anthropic models")
                return sorted(models)
            else:
                logger.warning(f"Anthropic API returned {response.status_code}")

        except Exception as e:
            logger.warning(f"Could not discover Anthropic models: {e}")

        return self._get_static_anthropic_models()

    def _get_static_anthropic_models(self) -> List[str]:
        """Fallback static list of Anthropic models."""
        return [
            # Claude 4.5 - Power user favorite, best instruction-following (200K context)
            'claude-sonnet-4-5-20250514',
            # Claude 3.5 series - Current production models
            'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022',
            # Claude 3 series - Established models
            'claude-3-opus-20240229', 'claude-3-sonnet-20240229',
            'claude-3-haiku-20240307'
        ]

    def _discover_openrouter_models(self, api_key: str = None) -> List[str]:
        """Fetch available models from OpenRouter API."""
        try:
            import requests

            if not api_key:
                api_key = os.getenv('OPENROUTER_API_KEY', '')
            if not api_key:
                logger.warning("No OpenRouter API key found, using static model list")
                return self._get_static_openrouter_models()

            response = requests.get(
                'https://openrouter.ai/api/v1/models',
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=10
            )

            if response.ok:
                data = response.json()
                models = [model['id'] for model in data.get('data', [])]
                logger.info(f"Discovered {len(models)} OpenRouter models")
                return sorted(models)
            else:
                logger.warning(f"OpenRouter API returned {response.status_code}")

        except Exception as e:
            logger.warning(f"Could not discover OpenRouter models: {e}")

        return self._get_static_openrouter_models()

    def _get_static_openrouter_models(self) -> List[str]:
        """Fallback static list of popular OpenRouter models - curated from market analysis."""
        return [
            # === CHARACTER ROLEPLAY (Top performers from market analysis) ===
            # DeepSeek R1T2 Chimera - #1 market leader (30.5%), best reasoning + character consistency
            'tngtech/deepseek-r1t2-chimera',
            'tngtech/deepseek-r1t2-chimera:free',
            # DeepSeek R1T Chimera - Advanced reasoning for sophisticated characters
            'tngtech/deepseek-r1t-chimera',
            # DeepSeek R1 0528 - Deep reasoning without alignment constraints
            'deepseek/deepseek-r1-0528',

            # === BALANCED / COST-EFFECTIVE ===
            # DeepSeek V3 0324 - #2 market usage, excellent instruction-following, 50+ turn consistency
            'deepseek/deepseek-chat-v3-0324',
            # DeepSeek V3.1 - Best cost-to-quality ratio for streaming chat
            'deepseek/deepseek-chat',

            # === POWER USER / PROFESSIONAL ===
            # Claude Sonnet 4.5 - Power user favorite, best instruction-following (200K context)
            'anthropic/claude-sonnet-4.5',
            'anthropic/claude-3.5-sonnet',
            'anthropic/claude-3-opus',
            'anthropic/claude-3-haiku',

            # === OPENAI MODELS ===
            'openai/gpt-4o',
            'openai/gpt-4o-mini',
            'openai/gpt-4-turbo',
            'openai/o1-preview',
            'openai/o1-mini',

            # === GOOGLE MODELS ===
            'google/gemini-pro-1.5',
            'google/gemini-flash-1.5',
            'google/gemini-2.0-flash-exp',

            # === META LLAMA ===
            'meta-llama/llama-3.1-405b-instruct',
            'meta-llama/llama-3.1-70b-instruct',
            'meta-llama/llama-3.1-8b-instruct',

            # === UNFILTERED OPTIONS (from market analysis) ===
            # Grok - Intentionally unfiltered, minimal safety training
            'x-ai/grok-2-1212',
            'x-ai/grok-beta',

            # === OTHER POPULAR ===
            'mistralai/mistral-large',
            'mistralai/mistral-medium',
            'mistralai/mixtral-8x22b-instruct',
            'cohere/command-r-plus',
            'qwen/qwen-2.5-72b-instruct'
        ]

    def _get_static_cloud_models(self, api_keys: Dict[str, str] = None) -> Dict[str, List[str]]:
        """Return cloud model lists, fetching dynamically if API keys are available."""
        if api_keys is None:
            api_keys = {}

        return {
            'openai': self._discover_openai_models(api_keys.get('openai')),
            'anthropic': self._discover_anthropic_models(api_keys.get('anthropic')),
            'openrouter': self._discover_openrouter_models(api_keys.get('openrouter'))
        }
    
    def _get_configured_models(self, api_keys: Dict[str, str] = None) -> Dict[str, List[str]]:
        """Load models from configuration file."""
        try:
            if self.models_config_file.exists():
                with open(self.models_config_file, 'r') as f:
                    config = json.load(f)
                return config.get('models', self._get_static_cloud_models(api_keys))
        except Exception as e:
            logger.error(f"Error loading models config: {e}")

        return self._get_static_cloud_models(api_keys)
    
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
        """Get privacy-aware model recommendations based on market analysis."""
        return {
            "privacy_first": {
                "provider": "ollama",
                "models": ["llama3.1:8b", "deepseek-r1:latest", "mistral:latest"],
                "description": "100% local processing, no data leaves your device",
                "privacy_level": "maximum",
                "best_for": "Users who prioritize privacy above all"
            },
            "character_roleplay": {
                "provider": "openrouter",
                "models": [
                    "tngtech/deepseek-r1t2-chimera",  # #1 market leader (30.5%)
                    "tngtech/deepseek-r1t-chimera",
                    "deepseek/deepseek-chat-v3-0324"
                ],
                "description": "Best reasoning + character consistency, minimal safety constraints",
                "privacy_level": "cloud",
                "best_for": "Creative writing, character roleplay, narrative consistency",
                "market_insight": "DeepSeek R1T2 Chimera dominates with 301.75B tokens (30.5% market share)"
            },
            "power_user": {
                "provider": "openrouter",
                "models": [
                    "anthropic/claude-sonnet-4.5",  # Power user favorite
                    "anthropic/claude-3.5-sonnet",
                    "anthropic/claude-3-opus"
                ],
                "description": "Best instruction-following, 200K context window, Constitutional AI",
                "privacy_level": "cloud",
                "best_for": "Complex prompts, knowledge work, professional applications",
                "market_insight": "Claude Sonnet 4.5 leads SillyTavern with 37.7B tokens"
            },
            "cost_effective": {
                "provider": "openrouter",
                "models": [
                    "deepseek/deepseek-chat",  # V3.1 - best cost-to-quality
                    "openai/gpt-4o-mini",
                    "google/gemini-flash-1.5"
                ],
                "description": "Best cost-to-quality ratio for streaming chat",
                "privacy_level": "cloud",
                "best_for": "High-volume usage, budget-conscious deployment"
            },
            "balanced": {
                "providers": ["ollama", "openrouter"],
                "models": {
                    "ollama": ["llama3.1:8b"],
                    "openrouter": ["deepseek/deepseek-chat-v3-0324"]
                },
                "description": "Local for private conversations, cloud for complex tasks",
                "privacy_level": "selective",
                "best_for": "General use with privacy when needed",
                "market_insight": "DeepSeek V3 0324 maintains character 50+ turns"
            },
            "unfiltered": {
                "provider": "openrouter",
                "models": [
                    "tngtech/deepseek-r1t2-chimera",
                    "x-ai/grok-2-1212",
                    "deepseek/deepseek-r1-0528"
                ],
                "description": "Models with minimal safety training for creative freedom",
                "privacy_level": "cloud",
                "best_for": "Adult content, dark themes, unrestricted character expression",
                "market_insight": "90.8% of unrestricted model usage clusters on character services"
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
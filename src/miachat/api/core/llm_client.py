"""
Multi-provider LLM client supporting Ollama, OpenAI, Anthropic, and OpenRouter.
Privacy-first design: Ollama (local) is the default provider.
"""

import os
import requests
import json
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class LLMClient:
    """Multi-provider LLM client with privacy-first design."""

    def __init__(self):
        # Ollama configuration (local, private)
        ollama_host = os.getenv('OLLAMA_HOST', 'localhost')
        ollama_port = os.getenv('OLLAMA_PORT', '11434')
        self.ollama_url = f"http://{ollama_host}:{ollama_port}"
        self.default_model = "llama3.1:8b"

        # Cloud provider API keys (optional)
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.openrouter_key = os.getenv('OPENROUTER_API_KEY')

    def generate_response_with_config(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        model_config: Dict[str, Any]
    ) -> str:
        """
        Generate a response using the specified model configuration.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system_prompt: System prompt for the character
            model_config: Model configuration dictionary with 'provider' and 'model'

        Returns:
            Generated response text
        """
        provider = model_config.get('provider', 'ollama')

        # Route to appropriate provider
        if provider == 'ollama':
            return self._generate_ollama(messages, system_prompt, model_config)
        elif provider == 'openai':
            return self._generate_openai(messages, system_prompt, model_config)
        elif provider == 'anthropic':
            return self._generate_anthropic(messages, system_prompt, model_config)
        elif provider == 'openrouter':
            return self._generate_openrouter(messages, system_prompt, model_config)
        else:
            logger.warning(f"Unknown provider {provider}, falling back to Ollama")
            return self._generate_ollama(messages, system_prompt, model_config)

    def _generate_ollama(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        model_config: Dict[str, Any]
    ) -> str:
        """Generate response using local Ollama (fully private)."""
        model = model_config.get('model', self.default_model)

        # Prepare messages with system prompt
        all_messages = messages.copy()
        if system_prompt and system_prompt.strip():
            all_messages = [{"role": "system", "content": system_prompt}] + all_messages

        payload = {
            "model": model,
            "messages": all_messages,
            "stream": False,
            "options": {
                "temperature": model_config.get('temperature', 0.7),
                "top_p": model_config.get('top_p', 0.9),
                "num_predict": model_config.get('max_tokens', 2048)
            }
        }

        logger.info(f"[Ollama/LOCAL] Using model {model}")

        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            return result.get('message', {}).get('content', '')

        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return f"Error connecting to Ollama: {str(e)}"

    def _generate_openai(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        model_config: Dict[str, Any]
    ) -> str:
        """Generate response using OpenAI API (cloud)."""
        if not self.openai_key:
            return "OpenAI API key not configured. Set OPENAI_API_KEY environment variable."

        model = model_config.get('model', 'gpt-4o-mini')

        # Prepare messages with system prompt
        all_messages = messages.copy()
        if system_prompt and system_prompt.strip():
            all_messages = [{"role": "system", "content": system_prompt}] + all_messages

        payload = {
            "model": model,
            "messages": all_messages,
            "temperature": model_config.get('temperature', 0.7),
            "max_tokens": model_config.get('max_tokens', 2048)
        }

        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }

        logger.info(f"[OpenAI/CLOUD] Using model {model}")

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']

        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return f"Error connecting to OpenAI: {str(e)}"

    def _generate_anthropic(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        model_config: Dict[str, Any]
    ) -> str:
        """Generate response using Anthropic API (cloud)."""
        if not self.anthropic_key:
            return "Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable."

        model = model_config.get('model', 'claude-3-5-sonnet-20241022')

        # Anthropic uses a different message format
        # System prompt goes in a separate field, not in messages
        anthropic_messages = []
        for msg in messages:
            if msg['role'] != 'system':
                anthropic_messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })

        payload = {
            "model": model,
            "max_tokens": model_config.get('max_tokens', 2048),
            "messages": anthropic_messages
        }

        if system_prompt and system_prompt.strip():
            payload["system"] = system_prompt

        headers = {
            "x-api-key": self.anthropic_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        logger.info(f"[Anthropic/CLOUD] Using model {model}")

        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            return result['content'][0]['text']

        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            return f"Error connecting to Anthropic: {str(e)}"

    def _generate_openrouter(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        model_config: Dict[str, Any]
    ) -> str:
        """Generate response using OpenRouter API (cloud, multi-provider)."""
        if not self.openrouter_key:
            return "OpenRouter API key not configured. Set OPENROUTER_API_KEY environment variable."

        model = model_config.get('model', 'openai/gpt-4o-mini')

        # Prepare messages with system prompt
        all_messages = messages.copy()
        if system_prompt and system_prompt.strip():
            all_messages = [{"role": "system", "content": system_prompt}] + all_messages

        payload = {
            "model": model,
            "messages": all_messages,
            "temperature": model_config.get('temperature', 0.7),
            "max_tokens": model_config.get('max_tokens', 2048)
        }

        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://miachat.local",
            "X-Title": "MiaChat"
        }

        logger.info(f"[OpenRouter/CLOUD] Using model {model}")

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']

        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            return f"Error connecting to OpenRouter: {str(e)}"

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        **kwargs
    ) -> str:
        """Simple response generation using default Ollama."""
        model_config = {
            'provider': 'ollama',
            'model': model or self.default_model,
            **kwargs
        }
        return self.generate_response_with_config(messages, None, model_config)

    def test_connection(self, provider: str = 'ollama') -> bool:
        """Test if a provider is accessible."""
        try:
            if provider == 'ollama':
                response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                return response.ok
            elif provider == 'openai':
                return bool(self.openai_key)
            elif provider == 'anthropic':
                return bool(self.anthropic_key)
            elif provider == 'openrouter':
                return bool(self.openrouter_key)
            return False
        except:
            return False

    def get_available_providers(self) -> List[Dict[str, Any]]:
        """Get list of available providers with their status."""
        providers = [
            {
                "id": "ollama",
                "name": "Ollama (Local)",
                "privacy": "full",
                "available": self.test_connection('ollama'),
                "description": "Fully private, runs locally"
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "privacy": "cloud",
                "available": bool(self.openai_key),
                "description": "GPT-4, GPT-4o, etc."
            },
            {
                "id": "anthropic",
                "name": "Anthropic",
                "privacy": "cloud",
                "available": bool(self.anthropic_key),
                "description": "Claude 3.5, Claude 3, etc."
            },
            {
                "id": "openrouter",
                "name": "OpenRouter",
                "privacy": "cloud",
                "available": bool(self.openrouter_key),
                "description": "Access to 100+ models"
            }
        ]
        return providers


# Global client instance
llm_client = LLMClient()

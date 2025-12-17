"""
Multi-provider LLM Client for MinouChat

Supports Ollama, OpenAI, Anthropic, and OpenRouter with a privacy-first design.
Ollama (local) is the default provider ensuring data never leaves your machine
unless you explicitly configure cloud providers.

Configuration:
    All settings can be configured via environment variables:
    - OLLAMA_HOST, OLLAMA_PORT: Local Ollama server
    - OPENAI_API_KEY, OPENAI_API_ENDPOINT: OpenAI configuration
    - ANTHROPIC_API_KEY, ANTHROPIC_API_ENDPOINT: Anthropic configuration
    - OPENROUTER_API_KEY, OPENROUTER_API_ENDPOINT: OpenRouter configuration
    - LLM_DEFAULT_MODEL: Default model for Ollama
    - LLM_REQUEST_TIMEOUT: Request timeout in seconds

Security:
    - API keys are never logged
    - Error messages are sanitized to avoid exposing internal details
    - Configurable endpoints allow proxy usage for added security
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

logger = logging.getLogger(__name__)


# =============================================================================
# Constants and Configuration
# =============================================================================

class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"


@dataclass(frozen=True)
class ProviderDefaults:
    """Default configuration values for providers."""
    # Ollama defaults
    OLLAMA_HOST: str = "localhost"
    OLLAMA_PORT: str = "11434"
    OLLAMA_MODEL: str = "llama3.1:8b"

    # OpenAI defaults
    OPENAI_ENDPOINT: str = "https://api.openai.com/v1/chat/completions"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Anthropic defaults
    ANTHROPIC_ENDPOINT: str = "https://api.anthropic.com/v1/messages"
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    ANTHROPIC_VERSION: str = "2023-06-01"

    # OpenRouter defaults
    OPENROUTER_ENDPOINT: str = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"

    # General defaults
    REQUEST_TIMEOUT: int = 120
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_MAX_TOKENS: int = 2048
    DEFAULT_TOP_P: float = 0.9
    DEFAULT_TOP_K: int = 40
    DEFAULT_REPEAT_PENALTY: float = 1.1


DEFAULTS = ProviderDefaults()


class LLMError(Exception):
    """Base exception for LLM client errors."""
    pass


class ProviderConnectionError(LLMError):
    """Raised when unable to connect to an LLM provider."""
    pass


class ProviderConfigurationError(LLMError):
    """Raised when a provider is not properly configured."""
    pass


# =============================================================================
# LLM Client Implementation
# =============================================================================

class LLMClient:
    """
    Multi-provider LLM client with privacy-first design.

    Supports routing requests to different LLM providers based on configuration.
    Ollama (local) is the default, ensuring privacy by default.

    Attributes:
        ollama_url: URL for the local Ollama server
        default_model: Default model to use for Ollama
        request_timeout: Timeout for API requests in seconds

    Example:
        >>> client = LLMClient()
        >>> response = client.generate_response_with_config(
        ...     messages=[{"role": "user", "content": "Hello!"}],
        ...     system_prompt="You are a helpful assistant.",
        ...     model_config={"provider": "ollama", "model": "llama3.1:8b"}
        ... )
    """

    def __init__(self) -> None:
        """Initialize the LLM client with configuration from environment."""
        # Ollama configuration (local, private)
        ollama_host = os.getenv('OLLAMA_HOST', DEFAULTS.OLLAMA_HOST)
        ollama_port = os.getenv('OLLAMA_PORT', DEFAULTS.OLLAMA_PORT)
        self.ollama_url: str = f"http://{ollama_host}:{ollama_port}"
        self.default_model: str = os.getenv('LLM_DEFAULT_MODEL', DEFAULTS.OLLAMA_MODEL)

        # Cloud provider API keys (optional)
        self.openai_key: Optional[str] = os.getenv('OPENAI_API_KEY') or None
        self.anthropic_key: Optional[str] = os.getenv('ANTHROPIC_API_KEY') or None
        self.openrouter_key: Optional[str] = os.getenv('OPENROUTER_API_KEY') or None

        # Configurable endpoints (for proxy support)
        self.openai_endpoint: str = os.getenv('OPENAI_API_ENDPOINT', DEFAULTS.OPENAI_ENDPOINT)
        self.anthropic_endpoint: str = os.getenv('ANTHROPIC_API_ENDPOINT', DEFAULTS.ANTHROPIC_ENDPOINT)
        self.openrouter_endpoint: str = os.getenv('OPENROUTER_API_ENDPOINT', DEFAULTS.OPENROUTER_ENDPOINT)

        # Request timeout
        self.request_timeout: int = int(os.getenv('LLM_REQUEST_TIMEOUT', str(DEFAULTS.REQUEST_TIMEOUT)))

    def generate_response_with_config(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        model_config: Dict[str, Any]
    ) -> str:
        """
        Generate a response using the specified model configuration.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            system_prompt: System prompt for the character/context
            model_config: Configuration dict with 'provider', 'model', and optional parameters

        Returns:
            Generated response text

        Raises:
            No exceptions raised - errors are returned as error message strings
            to maintain backward compatibility with existing code.
        """
        provider = model_config.get('provider', LLMProvider.OLLAMA.value)

        # Route to appropriate provider
        provider_handlers = {
            LLMProvider.OLLAMA.value: self._generate_ollama,
            LLMProvider.OPENAI.value: self._generate_openai,
            LLMProvider.ANTHROPIC.value: self._generate_anthropic,
            LLMProvider.OPENROUTER.value: self._generate_openrouter,
        }

        handler = provider_handlers.get(provider)
        if handler:
            return handler(messages, system_prompt, model_config)

        logger.warning(f"Unknown provider '{provider}', falling back to Ollama")
        return self._generate_ollama(messages, system_prompt, model_config)

    def _generate_ollama(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        model_config: Dict[str, Any]
    ) -> str:
        """
        Generate response using local Ollama (fully private).

        Args:
            messages: Conversation messages
            system_prompt: System prompt to prepend
            model_config: Model configuration parameters

        Returns:
            Generated response or error message
        """
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
                "temperature": model_config.get('temperature', DEFAULTS.DEFAULT_TEMPERATURE),
                "top_p": model_config.get('top_p', DEFAULTS.DEFAULT_TOP_P),
                "top_k": model_config.get('top_k', DEFAULTS.DEFAULT_TOP_K),
                "repeat_penalty": model_config.get('repeat_penalty', DEFAULTS.DEFAULT_REPEAT_PENALTY),
                "num_predict": model_config.get('max_tokens', DEFAULTS.DEFAULT_MAX_TOKENS)
            }
        }

        logger.info(f"[Ollama/LOCAL] Using model {model}")

        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=self.request_timeout
            )
            response.raise_for_status()
            result = response.json()
            return result.get('message', {}).get('content', '')

        except Timeout:
            logger.error(f"Ollama request timed out after {self.request_timeout}s")
            return "Request timed out. The model may be loading or the server is busy."
        except ConnectionError:
            logger.error(f"Cannot connect to Ollama at {self.ollama_url}")
            return "Cannot connect to Ollama. Is the server running?"
        except RequestException as e:
            logger.error(f"Ollama request error: {e}")
            return "Failed to generate response. Please try again."
        except (KeyError, ValueError) as e:
            logger.error(f"Ollama response parsing error: {e}")
            return "Received invalid response from Ollama."

    def _generate_openai(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        model_config: Dict[str, Any]
    ) -> str:
        """
        Generate response using OpenAI API (cloud).

        Args:
            messages: Conversation messages
            system_prompt: System prompt to prepend
            model_config: Model configuration parameters

        Returns:
            Generated response or error message
        """
        if not self.openai_key:
            return "OpenAI API key not configured. Set OPENAI_API_KEY environment variable."

        model = model_config.get('model', DEFAULTS.OPENAI_MODEL)

        # Prepare messages with system prompt
        all_messages = messages.copy()
        if system_prompt and system_prompt.strip():
            all_messages = [{"role": "system", "content": system_prompt}] + all_messages

        payload = {
            "model": model,
            "messages": all_messages,
            "temperature": model_config.get('temperature', DEFAULTS.DEFAULT_TEMPERATURE),
            "max_tokens": model_config.get('max_tokens', DEFAULTS.DEFAULT_MAX_TOKENS)
        }

        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }

        logger.info(f"[OpenAI/CLOUD] Using model {model}")

        try:
            response = requests.post(
                self.openai_endpoint,
                headers=headers,
                json=payload,
                timeout=self.request_timeout
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']

        except Timeout:
            logger.error(f"OpenAI request timed out after {self.request_timeout}s")
            return "Request timed out. Please try again."
        except ConnectionError:
            logger.error("Cannot connect to OpenAI API")
            return "Cannot connect to OpenAI. Check your internet connection."
        except RequestException as e:
            logger.error(f"OpenAI request error: {e}")
            return "Failed to generate response. Please try again."
        except (KeyError, ValueError) as e:
            logger.error(f"OpenAI response parsing error: {e}")
            return "Received invalid response from OpenAI."

    def _generate_anthropic(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        model_config: Dict[str, Any]
    ) -> str:
        """
        Generate response using Anthropic API (cloud).

        Args:
            messages: Conversation messages
            system_prompt: System prompt (sent as separate field for Anthropic)
            model_config: Model configuration parameters

        Returns:
            Generated response or error message
        """
        if not self.anthropic_key:
            return "Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable."

        model = model_config.get('model', DEFAULTS.ANTHROPIC_MODEL)

        # Anthropic uses a different message format
        # System prompt goes in a separate field, not in messages
        anthropic_messages = []
        for msg in messages:
            if msg['role'] != 'system':
                anthropic_messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })

        payload: Dict[str, Any] = {
            "model": model,
            "max_tokens": model_config.get('max_tokens', DEFAULTS.DEFAULT_MAX_TOKENS),
            "messages": anthropic_messages
        }

        if system_prompt and system_prompt.strip():
            payload["system"] = system_prompt

        headers = {
            "x-api-key": self.anthropic_key,
            "Content-Type": "application/json",
            "anthropic-version": DEFAULTS.ANTHROPIC_VERSION
        }

        logger.info(f"[Anthropic/CLOUD] Using model {model}")

        try:
            response = requests.post(
                self.anthropic_endpoint,
                headers=headers,
                json=payload,
                timeout=self.request_timeout
            )
            response.raise_for_status()
            result = response.json()
            return result['content'][0]['text']

        except Timeout:
            logger.error(f"Anthropic request timed out after {self.request_timeout}s")
            return "Request timed out. Please try again."
        except ConnectionError:
            logger.error("Cannot connect to Anthropic API")
            return "Cannot connect to Anthropic. Check your internet connection."
        except RequestException as e:
            logger.error(f"Anthropic request error: {e}")
            return "Failed to generate response. Please try again."
        except (KeyError, ValueError) as e:
            logger.error(f"Anthropic response parsing error: {e}")
            return "Received invalid response from Anthropic."

    def _generate_openrouter(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        model_config: Dict[str, Any]
    ) -> str:
        """
        Generate response using OpenRouter API (cloud, multi-provider).

        OpenRouter provides access to 100+ models through a single API.

        Args:
            messages: Conversation messages
            system_prompt: System prompt to prepend
            model_config: Model configuration (can include 'api_key' override)

        Returns:
            Generated response or error message
        """
        # Check for API key in model_config first, then fall back to instance variable
        api_key = model_config.get('api_key') or self.openrouter_key
        if not api_key:
            return "OpenRouter API key not configured. Set OPENROUTER_API_KEY or configure in Settings."

        model = model_config.get('model', DEFAULTS.OPENROUTER_MODEL)

        # Prepare messages with system prompt
        all_messages = messages.copy()
        if system_prompt and system_prompt.strip():
            all_messages = [{"role": "system", "content": system_prompt}] + all_messages

        payload = {
            "model": model,
            "messages": all_messages,
            "temperature": model_config.get('temperature', DEFAULTS.DEFAULT_TEMPERATURE),
            "max_tokens": model_config.get('max_tokens', DEFAULTS.DEFAULT_MAX_TOKENS)
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv('APP_URL', 'https://minouchat.local'),
            "X-Title": "MinouChat"
        }

        logger.info(f"[OpenRouter/CLOUD] Using model {model}")

        try:
            response = requests.post(
                self.openrouter_endpoint,
                headers=headers,
                json=payload,
                timeout=self.request_timeout
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']

        except Timeout:
            logger.error(f"OpenRouter request timed out after {self.request_timeout}s")
            return "Request timed out. Please try again."
        except ConnectionError:
            logger.error("Cannot connect to OpenRouter API")
            return "Cannot connect to OpenRouter. Check your internet connection."
        except RequestException as e:
            logger.error(f"OpenRouter request error: {e}")
            return "Failed to generate response. Please try again."
        except (KeyError, ValueError) as e:
            logger.error(f"OpenRouter response parsing error: {e}")
            return "Received invalid response from OpenRouter."

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """
        Simple response generation using default Ollama provider.

        This is a convenience method for quick generation without
        specifying full configuration.

        Args:
            messages: Conversation messages
            model: Optional model override
            **kwargs: Additional parameters passed to model config

        Returns:
            Generated response text
        """
        model_config = {
            'provider': LLMProvider.OLLAMA.value,
            'model': model or self.default_model,
            **kwargs
        }
        return self.generate_response_with_config(messages, None, model_config)

    def test_connection(self, provider: str = 'ollama') -> bool:
        """
        Test if a provider is accessible.

        Args:
            provider: Provider name to test ('ollama', 'openai', 'anthropic', 'openrouter')

        Returns:
            True if provider is available, False otherwise
        """
        try:
            if provider == LLMProvider.OLLAMA.value:
                response = requests.get(
                    f"{self.ollama_url}/api/tags",
                    timeout=5
                )
                return response.ok
            elif provider == LLMProvider.OPENAI.value:
                return bool(self.openai_key)
            elif provider == LLMProvider.ANTHROPIC.value:
                return bool(self.anthropic_key)
            elif provider == LLMProvider.OPENROUTER.value:
                return bool(self.openrouter_key)
            return False
        except RequestException:
            return False

    def get_available_providers(self) -> List[Dict[str, Any]]:
        """
        Get list of available providers with their status.

        Returns:
            List of provider info dictionaries with keys:
            - id: Provider identifier
            - name: Display name
            - privacy: Privacy level ('full' for local, 'cloud' for remote)
            - available: Whether the provider is currently accessible
            - description: Brief description of the provider
        """
        providers = [
            {
                "id": LLMProvider.OLLAMA.value,
                "name": "Ollama (Local)",
                "privacy": "full",
                "available": self.test_connection(LLMProvider.OLLAMA.value),
                "description": "Fully private, runs locally"
            },
            {
                "id": LLMProvider.OPENAI.value,
                "name": "OpenAI",
                "privacy": "cloud",
                "available": bool(self.openai_key),
                "description": "GPT-4, GPT-4o, etc."
            },
            {
                "id": LLMProvider.ANTHROPIC.value,
                "name": "Anthropic",
                "privacy": "cloud",
                "available": bool(self.anthropic_key),
                "description": "Claude 3.5, Claude 3, etc."
            },
            {
                "id": LLMProvider.OPENROUTER.value,
                "name": "OpenRouter",
                "privacy": "cloud",
                "available": bool(self.openrouter_key),
                "description": "Access to 100+ models"
            }
        ]
        return providers


# Global client instance (singleton pattern)
llm_client = LLMClient()

"""
Token counting and context budget management service.
Provides multi-provider token counting and intelligent budget allocation.
"""

import os
import logging
from typing import Dict, Any, Optional, List
import tiktoken

logger = logging.getLogger(__name__)


class TokenService:
    """Service for token counting and context budget management across LLM providers."""

    # Model context window sizes (in tokens)
    MODEL_CONTEXT_LIMITS = {
        # Ollama models
        'llama3.1:8b': 8192,
        'llama3.1:latest': 8192,
        'llama3.1:70b': 8192,
        'llama3:8b': 8192,
        'llama3:latest': 8192,
        'llama2:7b': 4096,
        'llama2:13b': 4096,
        'mistral:latest': 32768,
        'mistral:7b': 32768,
        'mixtral:8x7b': 32768,
        'codellama:7b': 16384,
        'codellama:13b': 16384,
        'deepseek-coder:6.7b': 16384,
        'phi3:mini': 4096,
        'gemma:7b': 8192,
        'qwen2:7b': 32768,

        # OpenAI models
        'gpt-4o': 128000,
        'gpt-4o-mini': 128000,
        'gpt-4-turbo': 128000,
        'gpt-4-turbo-preview': 128000,
        'gpt-4': 8192,
        'gpt-4-32k': 32768,
        'gpt-3.5-turbo': 16385,
        'gpt-3.5-turbo-16k': 16385,

        # Anthropic models
        'claude-3-5-sonnet-20241022': 200000,
        'claude-3-5-sonnet-latest': 200000,
        'claude-3-opus-20240229': 200000,
        'claude-3-sonnet-20240229': 200000,
        'claude-3-haiku-20240307': 200000,

        # OpenRouter models (common ones)
        'openai/gpt-4o': 128000,
        'openai/gpt-4o-mini': 128000,
        'anthropic/claude-3.5-sonnet': 200000,
        'anthropic/claude-3-opus': 200000,
        'meta-llama/llama-3.1-405b-instruct': 32768,
        'meta-llama/llama-3.1-70b-instruct': 32768,
        'mistralai/mistral-large': 32768,
        'google/gemini-pro-1.5': 1000000,
    }

    # Default token allocations (percentages of available context)
    DEFAULT_ALLOCATIONS = {
        'system_prompt': 0.15,      # 15% for character system prompt
        'persistent_memory': 0.10,  # 10% for always-injected memory
        'world_info': 0.20,         # 20% for keyword-triggered entries
        'conversation': 0.35,       # 35% for recent conversation history
        'rag_context': 0.15,        # 15% for document RAG
        'response_reserve': 0.05,   # 5% reserved for response generation
    }

    # Alternative allocations for different use cases
    ALLOCATION_PRESETS = {
        'default': DEFAULT_ALLOCATIONS,
        'rag_heavy': {
            'system_prompt': 0.10,
            'persistent_memory': 0.05,
            'world_info': 0.15,
            'conversation': 0.25,
            'rag_context': 0.40,
            'response_reserve': 0.05,
        },
        'conversation_heavy': {
            'system_prompt': 0.10,
            'persistent_memory': 0.05,
            'world_info': 0.10,
            'conversation': 0.55,
            'rag_context': 0.15,
            'response_reserve': 0.05,
        },
        'world_info_heavy': {
            'system_prompt': 0.10,
            'persistent_memory': 0.10,
            'world_info': 0.40,
            'conversation': 0.25,
            'rag_context': 0.10,
            'response_reserve': 0.05,
        },
    }

    def __init__(self, default_context_limit: int = 8192):
        """Initialize the token service.

        Args:
            default_context_limit: Default context limit for unknown models
        """
        self.default_context_limit = default_context_limit

        # Initialize tiktoken encoder (cl100k_base works for most modern models)
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
            logger.info("TokenService initialized with cl100k_base encoding")
        except Exception as e:
            logger.warning(f"Failed to load tiktoken encoder: {e}, using approximate counting")
            self.encoder = None

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception as e:
                logger.warning(f"Token counting failed: {e}, using approximate")

        # Fallback: approximate 4 characters per token
        return len(text) // 4

    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in a list of chat messages.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Total token count including message overhead
        """
        total = 0
        for msg in messages:
            # Add overhead for message structure (~4 tokens per message)
            total += 4
            total += self.count_tokens(msg.get('role', ''))
            total += self.count_tokens(msg.get('content', ''))

        # Add overhead for conversation structure
        total += 3

        return total

    def get_model_context_limit(self, model: str, provider: str = 'ollama') -> int:
        """Get context window size for a model.

        Args:
            model: Model name/identifier
            provider: Provider name (ollama, openai, anthropic, openrouter)

        Returns:
            Context window size in tokens
        """
        # Try exact match first
        if model in self.MODEL_CONTEXT_LIMITS:
            return self.MODEL_CONTEXT_LIMITS[model]

        # Try with provider prefix for OpenRouter
        if provider == 'openrouter':
            prefixed = model if '/' in model else f"openai/{model}"
            if prefixed in self.MODEL_CONTEXT_LIMITS:
                return self.MODEL_CONTEXT_LIMITS[prefixed]

        # Try to match by model family
        model_lower = model.lower()

        if 'gpt-4o' in model_lower:
            return 128000
        elif 'gpt-4' in model_lower:
            return 8192 if '32k' not in model_lower else 32768
        elif 'gpt-3.5' in model_lower:
            return 16385
        elif 'claude-3' in model_lower:
            return 200000
        elif 'claude-2' in model_lower:
            return 100000
        elif 'llama-3' in model_lower or 'llama3' in model_lower:
            return 8192
        elif 'mistral' in model_lower or 'mixtral' in model_lower:
            return 32768
        elif 'gemini' in model_lower:
            return 1000000

        logger.warning(f"Unknown model {model}, using default context limit {self.default_context_limit}")
        return self.default_context_limit

    def calculate_budget(
        self,
        model: str,
        provider: str = 'ollama',
        preset: str = 'default',
        custom_allocations: Optional[Dict[str, float]] = None
    ) -> Dict[str, int]:
        """Calculate token budgets for each context component.

        Args:
            model: Model name
            provider: Provider name
            preset: Allocation preset name
            custom_allocations: Custom allocation percentages (overrides preset)

        Returns:
            Dictionary mapping component names to token budgets
        """
        context_limit = self.get_model_context_limit(model, provider)

        # Get allocations
        if custom_allocations:
            allocations = custom_allocations
        elif preset in self.ALLOCATION_PRESETS:
            allocations = self.ALLOCATION_PRESETS[preset]
        else:
            allocations = self.DEFAULT_ALLOCATIONS

        # Calculate budgets
        budgets = {}
        for component, percentage in allocations.items():
            budgets[component] = int(context_limit * percentage)

        # Add metadata
        budgets['total_context'] = context_limit
        budgets['model'] = model
        budgets['provider'] = provider

        return budgets

    def truncate_to_budget(
        self,
        text: str,
        max_tokens: int,
        preserve_end: bool = True,
        ellipsis: str = "..."
    ) -> str:
        """Truncate text to fit within token budget.

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed
            preserve_end: If True, keep end of text; if False, keep start
            ellipsis: String to add indicating truncation

        Returns:
            Truncated text
        """
        if not text:
            return text

        current_tokens = self.count_tokens(text)
        if current_tokens <= max_tokens:
            return text

        ellipsis_tokens = self.count_tokens(ellipsis)
        target_tokens = max_tokens - ellipsis_tokens

        if target_tokens <= 0:
            return ellipsis

        if self.encoder:
            try:
                tokens = self.encoder.encode(text)
                if preserve_end:
                    # Keep the end
                    truncated_tokens = tokens[-target_tokens:]
                    return ellipsis + self.encoder.decode(truncated_tokens)
                else:
                    # Keep the start
                    truncated_tokens = tokens[:target_tokens]
                    return self.encoder.decode(truncated_tokens) + ellipsis
            except Exception as e:
                logger.warning(f"Token-based truncation failed: {e}")

        # Fallback: character-based truncation (4 chars per token estimate)
        target_chars = target_tokens * 4
        if preserve_end:
            return ellipsis + text[-target_chars:]
        else:
            return text[:target_chars] + ellipsis

    def allocate_context(
        self,
        contents: Dict[str, str],
        model: str,
        provider: str = 'ollama',
        preset: str = 'default'
    ) -> Dict[str, str]:
        """Allocate context content within budgets, truncating as needed.

        Args:
            contents: Dictionary mapping component names to their text content
            model: Model name
            provider: Provider name
            preset: Allocation preset

        Returns:
            Dictionary with truncated content for each component
        """
        budgets = self.calculate_budget(model, provider, preset)

        allocated = {}
        for component, content in contents.items():
            if component in budgets and content:
                budget = budgets[component]
                # Determine truncation direction
                preserve_end = component in ['conversation', 'rag_context']
                allocated[component] = self.truncate_to_budget(
                    content, budget, preserve_end=preserve_end
                )
            else:
                allocated[component] = content

        return allocated

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics.

        Returns:
            Dictionary with service stats
        """
        return {
            'known_models': len(self.MODEL_CONTEXT_LIMITS),
            'allocation_presets': list(self.ALLOCATION_PRESETS.keys()),
            'default_context_limit': self.default_context_limit,
            'encoder_available': self.encoder is not None,
        }


# Global token service instance
token_service = TokenService()

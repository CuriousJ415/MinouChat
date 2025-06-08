"""
LLM Adapter Interface
Manages integration with different LLM providers
"""
import json
import os
import requests
from typing import Dict, List, Optional, Any
from flask import current_app

from app.core.config import Config

# Cache the LLM providers
LLM_PROVIDERS = {}

def get_llm_config() -> Dict[str, Any]:
    """
    Get current LLM configuration
    
    Returns:
        Dictionary with LLM configuration
    """
    return Config.get_llm_config()

def update_llm_config(config: Dict[str, Any]) -> bool:
    """
    Update LLM configuration
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if successful, False otherwise
    """
    # Update configuration
    result = Config.save_llm_config(config)
    
    # Update app configuration if in app context
    try:
        if current_app and result:
            current_app.config['LLM_CONFIG'] = config
    except RuntimeError:
        # Not in app context
        pass
        
    return result

def test_llm_connection(provider: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Test connection to LLM provider
    
    Args:
        provider: LLM provider name
        config: Optional configuration override
        
    Returns:
        Dictionary with test results
    """
    if config is None:
        config = get_llm_config()
        
    # Merge provided config with existing
    test_config = config.copy()
    test_config['provider'] = provider
    
    try:
        # Simple test prompt
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, can you hear me?"}
        ]
        
        # Try to generate a response
        response = generate_llm_response(messages, test_config.get('model', 'mistral'), test_config)
        
        return {
            "success": True,
            "message": "Connection successful",
            "response": response[:100] + "..." if len(response) > 100 else response
        }
    except Exception as e:
        current_app.logger.error(f"LLM connection test failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def generate_llm_response(
    messages: List[Dict[str, str]] = None,
    system_prompt: str = None,
    message_history: List[Dict] = None,
    user_message: str = None,
    model: str = None, 
    config: Dict[str, Any] = None, 
    provider: str = None,
    temperature: float = 0.7,
    top_p: float = 0.9,
    repeat_penalty: float = 1.1,
    top_k: int = 40
) -> str:
    """
    Generate a response from an LLM provider
    
    Supports two modes:
    1. Messages mode: Pass a list of messages in OpenAI format
    2. System + history mode: Pass system_prompt, message_history, and user_message
    
    Args:
        messages: List of message dictionaries (OpenAI format)
        system_prompt: System prompt for the LLM
        message_history: List of previous message dictionaries
        user_message: Current user message
        model: Model name to use
        config: Custom LLM configuration
        provider: Provider name (e.g., 'ollama', 'openai')
        temperature: Sampling temperature (0.0 to 1.0)
        top_p: Nucleus sampling probability (0.0 to 1.0)
        repeat_penalty: Penalty for repeating tokens (1.0 to 2.0)
        top_k: Top-k sampling parameter (1 to 100)
        
    Returns:
        Generated response text
    """
    # If using the system + history mode, convert to messages format
    if messages is None and system_prompt and user_message:
        messages = []
        
        # Add system message
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # Add message history
        if message_history:
            for msg in message_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Add user message
        messages.append({
            "role": "user",
            "content": user_message
        })
    
    # Get LLM configuration
    if not config:
        config = get_llm_config()
    
    # Use default provider if not specified
    if not provider:
        provider = config.get('default_provider', 'ollama')
    
    # Use default model if not specified
    if not model:
        # Get default model for provider
        provider_config = config.get(provider, {})
        model = provider_config.get('default_model', 'mistral')
    
    # Prepare model parameters
    model_params = {
        "temperature": temperature,
        "top_p": top_p,
        "repeat_penalty": repeat_penalty,
        "top_k": top_k
    }
    
    # Select provider-specific implementation
    if provider == 'ollama':
        return _generate_ollama_response(messages, model, config, model_params)
    elif provider == 'openai':
        return _generate_openai_response(messages, model, config, model_params)
    elif provider == 'anthropic':
        return _generate_anthropic_response(messages, model, config, model_params)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

def _generate_ollama_response(
    messages: List[Dict[str, str]], 
    model: str, 
    config: Dict[str, Any],
    model_params: Dict[str, Any]
) -> str:
    """
    Generate a response using Ollama
    
    Args:
        messages: List of message dictionaries
        model: Model name
        config: Configuration dictionary
        model_params: Model parameters (temperature, top_p, etc.)
        
    Returns:
        Generated text response
        
    Raises:
        ValueError: If connection fails
    """
    # Add explicit timeout for requests
    REQUEST_TIMEOUT = 15  # seconds
    
    try:
        # Try multiple possible hostnames for Ollama
        hosts_to_try = [
            os.environ.get('OLLAMA_HOST', 'localhost'),  # From env or default
            'localhost',  # Direct localhost
            '127.0.0.1',  # Explicit localhost IP
            'host.docker.internal',  # Docker Desktop standard for host machine
            'ollama',     # Service name if using docker-compose
            'host-gateway'  # Linux Docker
        ]
        
        port = os.environ.get('OLLAMA_PORT', '11434')
        
        # Log for debugging
        current_app.logger.info(f"Attempting to connect to Ollama with hosts: {hosts_to_try}, on port {port}")
        
        last_error = None
        for host in hosts_to_try:
            try:
                current_app.logger.info(f"Trying Ollama connection at {host}:{port}")
                api_url = f"http://{host}:{port}/api"
                generate_url = f"{api_url}/chat"
                
                # First try a simple GET request to check if Ollama is running
                try:
                    health_check = requests.get(f"{api_url}/tags", timeout=5)
                    if not health_check.ok:
                        current_app.logger.warning(f"Ollama health check failed at {host}: {health_check.status_code}")
                        continue
                except requests.RequestException as e:
                    current_app.logger.warning(f"Ollama health check failed at {host}: {str(e)}")
                    continue
                
                # Format request
                data = {
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": model_params.get('temperature', 0.7),
                        "top_p": model_params.get('top_p', 0.9),
                        "top_k": model_params.get('top_k', 40),
                        "repeat_penalty": model_params.get('repeat_penalty', 1.1)
                    }
                }
                
                # Make request with a short timeout for quick failure
                response = requests.post(generate_url, json=data, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                
                # If we get here, the request was successful
                current_app.logger.info(f"Successfully connected to Ollama at {host}")
                
                # Parse response
                result = response.json()
                return result.get('message', {}).get('content', '')
                
            except requests.RequestException as e:
                current_app.logger.warning(f"Ollama request to {host} failed: {str(e)}")
                last_error = e
                continue
                
        # If we get here, all hosts failed
        error_msg = "Failed to connect to Ollama. Please ensure Ollama is running and accessible."
        if last_error:
            error_msg += f" Last error: {str(last_error)}"
        raise ValueError(error_msg)
        
    except Exception as e:
        current_app.logger.error(f"Ollama request failed: {str(e)}")
        raise ValueError(f"Failed to connect to Ollama: {str(e)}")

def _generate_openai_response(
    messages: List[Dict[str, str]], 
    model: str, 
    config: Dict[str, Any],
    model_params: Dict[str, Any]
) -> str:
    """
    Generate a response using OpenAI
    
    Args:
        messages: List of message dictionaries
        model: Model name
        config: Configuration dictionary
        model_params: Model parameters (temperature, top_p, etc.)
        
    Returns:
        Generated text response
        
    Raises:
        ValueError: If API key missing or connection fails
    """
    api_key = config.get('api_key')
    if not api_key:
        raise ValueError("OpenAI API key is required")
    
    api_url = config.get('api_url', 'https://api.openai.com/v1/chat/completions')
    
    try:
        # Format request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": messages,
            "options": model_params
        }
        
        # Make request
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        return result['choices'][0]['message']['content']
        
    except requests.RequestException as e:
        current_app.logger.error(f"OpenAI request failed: {str(e)}")
        raise ValueError(f"Failed to connect to OpenAI: {str(e)}")

def _generate_anthropic_response(
    messages: List[Dict[str, str]], 
    model: str, 
    config: Dict[str, Any],
    model_params: Dict[str, Any]
) -> str:
    """
    Generate a response using Anthropic
    
    Args:
        messages: List of message dictionaries
        model: Model name
        config: Configuration dictionary
        model_params: Model parameters (temperature, top_p, etc.)
        
    Returns:
        Generated text response
        
    Raises:
        ValueError: If API key missing or connection fails
    """
    api_key = config.get('api_key')
    if not api_key:
        raise ValueError("Anthropic API key is required")
    
    api_url = config.get('api_url', 'https://api.anthropic.com/v1/messages')
    
    # Convert messages to Anthropic format
    anthropic_messages = []
    system_content = ""
    
    for msg in messages:
        if msg['role'] == 'system':
            system_content += msg['content'] + "\n\n"
        else:
            anthropic_messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
    
    try:
        # Format request
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        data = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": 1024,
            "options": model_params
        }
        
        # Add system content if exists
        if system_content:
            data["system"] = system_content.strip()
        
        # Make request
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        return result['content'][0]['text']
        
    except requests.RequestException as e:
        current_app.logger.error(f"Anthropic request failed: {str(e)}")
        raise ValueError(f"Failed to connect to Anthropic: {str(e)}")

def get_ollama_base_url():
    """Get the base URL for Ollama API"""
    host = os.environ.get('OLLAMA_HOST', 'localhost')
    port = os.environ.get('OLLAMA_PORT', '11434')
    return f"http://{host}:{port}/api"

def fetch_available_models(provider):
    """Fetch available models from the provider"""
    try:
        if provider == 'ollama':
            base_url = get_ollama_base_url()
            try:
                response = requests.get(f"{base_url}/tags", timeout=5)
                if response.ok:
                    data = response.json()
                    return [model['name'].split(':')[0] for model in data['models']]
                else:
                    current_app.logger.error(f"Failed to fetch Ollama models: {response.text}")
                    return []
            except requests.RequestException as e:
                current_app.logger.error(f"Failed to connect to Ollama: {str(e)}")
                return []
        elif provider == 'openai':
            # Add OpenAI model fetching if needed
            return ['gpt-3.5-turbo', 'gpt-4']
        elif provider == 'anthropic':
            # Add Anthropic model fetching if needed
            return ['claude-2', 'claude-instant-1']
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    except Exception as e:
        current_app.logger.error(f"Error fetching models: {str(e)}")
        return []

def get_llm_adapter():
    """Get the appropriate LLM adapter based on configuration"""
    provider = current_app.config.get('LLM_PROVIDER', 'ollama')
    
    if provider == 'ollama':
        base_url = get_ollama_base_url()
        return OllamaAdapter(base_url)
    elif provider == 'openai':
        api_key = current_app.config.get('OPENAI_API_KEY')
        return OpenAIAdapter(api_key)
    elif provider == 'anthropic':
        api_key = current_app.config.get('ANTHROPIC_API_KEY')
        return AnthropicAdapter(api_key)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

class OllamaAdapter:
    def __init__(self, base_url):
        self.base_url = base_url
        
    def generate_response(self, messages, model="mistral", **kwargs):
        """Generate a response using Ollama"""
        try:
            # Format messages for Ollama
            prompt = self._format_messages(messages)
            
            # Make request to Ollama
            response = requests.post(
                f"{self.base_url}/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    **kwargs
                }
            )
            
            if not response.ok:
                raise Exception(f"Ollama request failed: {response.text}")
                
            data = response.json()
            return data['message']['content']
            
        except Exception as e:
            current_app.logger.error(f"Ollama request failed: {str(e)}")
            raise Exception(f"Failed to connect to Ollama: {str(e)}")
            
    def _format_messages(self, messages):
        """Format messages for Ollama API"""
        formatted = []
        for msg in messages:
            formatted.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        return formatted

def _fetch_openai_models(config: Dict[str, Any]) -> List[str]:
    """
    Return common OpenAI models (API doesn't easily support model listing)
    """
    return [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo"
    ]

def _fetch_anthropic_models(config: Dict[str, Any]) -> List[str]:
    """
    Return common Anthropic models (API doesn't easily support model listing)
    """
    return [
        "claude-3-5-sonnet",
        "claude-3-opus",
        "claude-3-sonnet",
        "claude-3-haiku",
        "claude-2.1",
        "claude-2.0"
    ] 
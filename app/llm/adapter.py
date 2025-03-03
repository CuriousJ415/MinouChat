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
        config: Updated configuration dictionary
        
    Returns:
        True if successful, False otherwise
    """
    return Config.save_llm_config(config)

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

def generate_llm_response(messages: List[Dict[str, str]], model: str = None, config: Dict[str, Any] = None, provider: str = None) -> str:
    """
    Generate a response from the LLM
    
    Args:
        messages: List of message dictionaries (role, content)
        model: Optional model override
        config: Optional configuration override
        provider: Optional provider override
        
    Returns:
        Generated text response
        
    Raises:
        ValueError: If provider not supported or connection fails
    """
    if config is None:
        config = get_llm_config()
        
    # Use specified model or fallback
    model = model or config.get('model', 'mistral')
    
    # Use specified provider or fallback to config
    provider = provider or config.get('provider', 'ollama')
    
    # Route to appropriate provider implementation
    if provider == 'ollama':
        return _generate_ollama_response(messages, model, config)
    elif provider == 'openai':
        return _generate_openai_response(messages, model, config)
    elif provider == 'anthropic':
        return _generate_anthropic_response(messages, model, config)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

def _generate_ollama_response(messages: List[Dict[str, str]], model: str, config: Dict[str, Any]) -> str:
    """
    Generate a response using Ollama
    
    Args:
        messages: List of message dictionaries
        model: Model name
        config: Configuration dictionary
        
    Returns:
        Generated text response
        
    Raises:
        ValueError: If connection fails
    """
    api_url = config.get('api_url', 'http://localhost:11434/api')
    
    # Fix API URL if needed
    if not api_url.endswith('/api'):
        api_url = f"{api_url.rstrip('/')}/api"
        
    generate_url = f"{api_url}/chat"
    
    try:
        # Format request
        data = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        
        # Make request
        response = requests.post(generate_url, json=data)
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        return result.get('message', {}).get('content', '')
        
    except requests.RequestException as e:
        current_app.logger.error(f"Ollama request failed: {str(e)}")
        raise ValueError(f"Failed to connect to Ollama: {str(e)}")

def _generate_openai_response(messages: List[Dict[str, str]], model: str, config: Dict[str, Any]) -> str:
    """
    Generate a response using OpenAI
    
    Args:
        messages: List of message dictionaries
        model: Model name
        config: Configuration dictionary
        
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
            "messages": messages
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

def _generate_anthropic_response(messages: List[Dict[str, str]], model: str, config: Dict[str, Any]) -> str:
    """
    Generate a response using Anthropic
    
    Args:
        messages: List of message dictionaries
        model: Model name
        config: Configuration dictionary
        
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
            "max_tokens": 1024
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
from __future__ import annotations
import os
import json
import requests
from typing import Dict, List, Optional, Any
import logging
from urllib.parse import urlparse

class ModelAdapter:
    """Adapter for different LLM providers"""
    
    def __init__(self, config_path: str = 'config/llm_config.json'):
        self.config_path = config_path
        self.config = self._load_config()
        self._ensure_config_dir()
        self._validate_config()
        
    def _validate_config(self) -> None:
        """Validate and normalize configuration"""
        if 'api_url' in self.config:
            # Ensure API URL has no trailing slash
            self.config['api_url'] = self.config['api_url'].rstrip('/')
            
            # If using Ollama, ensure proper URL format
            if self.config.get('provider') == 'ollama':
                parsed = urlparse(self.config['api_url'])
                if not parsed.scheme:
                    self.config['api_url'] = f"http://{self.config['api_url']}"
                if not parsed.path or parsed.path == '/':
                    self.config['api_url'] = f"{self.config['api_url']}/api"
    
    def _ensure_config_dir(self) -> None:
        """Ensure config directory exists"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
    
    def _load_config(self) -> Dict:
        """Load configuration from file or environment"""
        # Default configuration
        default_config = {
            'provider': 'ollama',
            'api_url': 'http://localhost:11434/api',
            'model': 'mistral',
            'api_key': None,
            'headers': {},
            'available_models': []
        }
        
        # Try to load from file
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    # Ensure all default keys exist
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                logging.error(f"Error loading config: {str(e)}")
        
        # If no file, try environment variables
        env_provider = os.environ.get('LLM_PROVIDER')
        if env_provider:
            config = {
                'provider': env_provider,
                'api_url': os.environ.get('LLM_API_URL', 'http://localhost:11434/api'),
                'model': os.environ.get('LLM_MODEL', 'mistral'),
                'api_key': os.environ.get('LLM_API_KEY'),
                'headers': {},
                'available_models': []
            }
            try:
                headers_str = os.environ.get('LLM_HEADERS', '{}')
                config['headers'] = json.loads(headers_str)
            except:
                pass
            return config
            
        # Return default if nothing else works
        return default_config
    
    def save_config(self, config: Dict) -> bool:
        """Save configuration to file"""
        try:
            # Don't overwrite all settings, just update what's provided
            current_config = self._load_config()
            current_config.update(config)
            
            self._ensure_config_dir()
            with open(self.config_path, 'w') as f:
                json.dump(current_config, f, indent=2)
                
            # Update current config
            self.config = current_config
            return True
        except Exception as e:
            logging.error(f"Error saving config: {str(e)}")
            return False
    
    def get_config(self) -> Dict:
        """Get current configuration"""
        return self.config
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to configured provider"""
        provider = self.config.get('provider', 'ollama')
        
        test_handlers = {
            'ollama': self._test_ollama_connection,
            'openai': self._test_openai_connection,
            'anthropic': self._test_anthropic_connection,
            'custom': self._test_custom_connection
        }
        
        handler = test_handlers.get(provider)
        if not handler:
            return {
                'success': False,
                'error': f"Unknown provider: {provider}"
            }
            
        return handler()
    
    def generate_response(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Generate response using configured provider"""
        provider = self.config.get('provider', 'ollama')
        
        handlers = {
            'ollama': self._generate_ollama,
            'openai': self._generate_openai,
            'anthropic': self._generate_anthropic,
            'custom': self._generate_custom
        }
        
        handler = handlers.get(provider)
        if not handler:
            logging.error(f"Unknown provider: {provider}")
            return None
            
        return handler(messages)
    
    def get_config(self) -> Dict:
        """Get current configuration"""
        # Create a safe copy of the config to return
        safe_config = self.config.copy()
        if 'api_key' in safe_config:
            # Instead of returning None, return True if key exists
            safe_config['api_key'] = safe_config['api_key'] is not None
        return safe_config

    def save_config(self, config: Dict) -> bool:
        """Save configuration to file"""
        try:
            # Update current config with new values
            self.config.update(config)
            
            # Ensure config directory exists
            self._ensure_config_dir()
            
            # Save to file
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            return True
        except Exception as e:
            logging.error(f"Failed to save configuration: {str(e)}")
            return False

    def _test_ollama_connection(self) -> Dict[str, Any]:
        """Test connection to Ollama"""
        try:
            api_url = self.config.get('api_url', 'http://ollama:11434/api').rstrip('/')
            response = requests.get(f"{api_url}/tags", timeout=5)
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model.get("name") for model in models if model.get("name")]
                return {
                    'success': True,
                    'message': f"Connected successfully. Available models: {', '.join(model_names[:5])}{'...' if len(model_names) > 5 else ''}"
                }
            else:
                return {
                    'success': False,
                    'error': f"Connection failed with status code: {response.status_code}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Connection failed: {str(e)}"
            }
    
    def _generate_ollama(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Generate response using Ollama"""
        try:
            api_url = self.config.get('api_url', 'http://ollama:11434/api').rstrip('/')
            model = self.config.get('model', 'mistral')
            
            response = requests.post(
                f"{api_url}/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code != 200:
                logging.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None
                
            return response.json()["message"]["content"].strip()
            
        except Exception as e:
            logging.error(f"Error generating response with Ollama: {str(e)}")
            return None
    
    def _test_openai_connection(self) -> Dict[str, Any]:
        """Test connection to OpenAI API"""
        try:
            api_key = self.config.get('api_key')
            model = self.config.get('model', 'gpt-4o')
            
            if not api_key:
                return {
                    'success': False,
                    'error': "API key not configured"
                }
                
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Simple test request
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Hello, this is a test message. Please respond with 'OK'."}],
                    "max_tokens": 10,
                    "temperature": 0.1
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': f"Connected successfully to OpenAI API with model {model}"
                }
            else:
                error_message = response.json().get('error', {}).get('message', f"Status code: {response.status_code}")
                return {
                    'success': False,
                    'error': f"Connection failed: {error_message}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Connection failed: {str(e)}"
            }
    
    def _generate_openai(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Generate response using OpenAI API"""
        try:
            api_key = self.config.get('api_key')
            model = self.config.get('model', 'gpt-4o')
            
            if not api_key:
                logging.error("OpenAI API key not configured")
                return None
                
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7
                },
                timeout=60
            )
            
            if response.status_code != 200:
                logging.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return None
                
            return response.json()["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logging.error(f"Error generating response with OpenAI: {str(e)}")
            return None
    
    def _test_anthropic_connection(self) -> Dict[str, Any]:
        """Test connection to Anthropic Claude API"""
        try:
            api_key = self.config.get('api_key')
            model = self.config.get('model', 'claude-3-5-sonnet')
            
            if not api_key:
                return {
                    'success': False,
                    'error': "API key not configured"
                }
                
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            # Simple test request
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Hello, this is a test message. Please respond with 'OK'."}],
                    "max_tokens": 10
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': f"Connected successfully to Anthropic API with model {model}"
                }
            else:
                error_message = response.json().get('error', {}).get('message', f"Status code: {response.status_code}")
                return {
                    'success': False,
                    'error': f"Connection failed: {error_message}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Connection failed: {str(e)}"
            }
    
    def _generate_anthropic(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Generate response using Anthropic Claude API"""
        try:
            api_key = self.config.get('api_key')
            model = self.config.get('model', 'claude-3-5-sonnet')
            
            if not api_key:
                logging.error("Anthropic API key not configured")
                return None
            
            # Convert messages to Anthropic format
            anthropic_messages = []
            system_message = None
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": anthropic_messages,
                "max_tokens": 1024
            }
            
            if system_message:
                payload["system"] = system_message
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                logging.error(f"Anthropic API error: {response.status_code} - {response.text}")
                return None
                
            return response.json()["content"][0]["text"].strip()
            
        except Exception as e:
            logging.error(f"Error generating response with Anthropic: {str(e)}")
            return None
    
    def _test_custom_connection(self) -> Dict[str, Any]:
        """Test connection to custom API endpoint"""
        try:
            api_url = self.config.get('api_url')
            api_key = self.config.get('api_key')
            model = self.config.get('model')
            custom_headers = self.config.get('headers', {})
            
            if not api_url:
                return {
                    'success': False,
                    'error': "API URL not configured"
                }
                
            headers = {
                "Content-Type": "application/json"
            }
            
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                
            # Add custom headers
            headers.update(custom_headers)
            
            # Simple test request with minimal payload
            payload = {
                "messages": [{"role": "user", "content": "This is a connection test."}]
            }
            
            if model:
                payload["model"] = model
                
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': f"Connected successfully to custom API at {api_url}"
                }
            else:
                return {
                    'success': False,
                    'error': f"Connection failed with status code: {response.status_code}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Connection failed: {str(e)}"
            }
    
    def _generate_custom(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Generate response using custom API endpoint"""
        try:
            api_url = self.config.get('api_url')
            api_key = self.config.get('api_key')
            model = self.config.get('model')
            custom_headers = self.config.get('headers', {})
            
            if not api_url:
                logging.error("Custom API URL not configured")
                return None
                
            headers = {
                "Content-Type": "application/json"
            }
            
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                
            # Add custom headers
            headers.update(custom_headers)
            
            payload = {
                "messages": messages
            }
            
            if model:
                payload["model"] = model
                
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                logging.error(f"Custom API error: {response.status_code} - {response.text}")
                return None
            
            # Try to parse response based on common API patterns
            response_json = response.json()
            
            # Try OpenAI format
            if "choices" in response_json and len(response_json["choices"]) > 0:
                if "message" in response_json["choices"][0]:
                    return response_json["choices"][0]["message"]["content"].strip()
                elif "text" in response_json["choices"][0]:
                    return response_json["choices"][0]["text"].strip()
            
            # Try Anthropic format
            if "content" in response_json and isinstance(response_json["content"], list):
                if len(response_json["content"]) > 0 and "text" in response_json["content"][0]:
                    return response_json["content"][0]["text"].strip()
            
            # Try direct message format
            if "message" in response_json:
                if isinstance(response_json["message"], dict) and "content" in response_json["message"]:
                    return response_json["message"]["content"].strip()
                elif isinstance(response_json["message"], str):
                    return response_json["message"].strip()
            
            # Try direct content format
            if "content" in response_json and isinstance(response_json["content"], str):
                return response_json["content"].strip()
                
            # Try direct text format
            if "text" in response_json and isinstance(response_json["text"], str):
                return response_json["text"].strip()
                
            logging.error(f"Could not parse response format: {response_json}")
            return None
            
        except Exception as e:
            logging.error(f"Error generating response with custom API: {str(e)}")
            return None

    def get_available_models(self) -> List[str]:
        """Get list of available models for current provider"""
        provider = self.config.get('provider', 'ollama')
        
        if provider == 'ollama':
            try:
                api_url = self.config.get('api_url', 'http://localhost:11434/api').rstrip('/')
                response = requests.get(f"{api_url}/tags", timeout=5)
                
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [model.get("name") for model in models if model.get("name")]
                    # Update available models in config
                    self.config['available_models'] = model_names
                    self.save_config(self.config)
                    return model_names
                else:
                    logging.error(f"Failed to fetch models: {response.status_code} - {response.text}")
                    return []
            except requests.exceptions.ConnectionError:
                logging.error("Could not connect to Ollama. Is it running?")
                return []
            except Exception as e:
                logging.error(f"Error fetching available models: {str(e)}")
                return []
        
        # For other providers, return empty list as we don't have a way to fetch models
        return []

    def switch_model(self, model_name: str) -> bool:
        """Switch to a different model"""
        if not model_name:
            return False
            
        # For Ollama, verify model exists
        if self.config.get('provider') == 'ollama':
            available_models = self.get_available_models()
            if not available_models:
                logging.error("Could not fetch available models. Is Ollama running?")
                return False
            if model_name not in available_models:
                logging.error(f"Model {model_name} not available")
                return False
        
        # Update model in config
        self.config['model'] = model_name
        return self.save_config(self.config)
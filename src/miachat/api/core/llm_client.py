import requests
import json
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.default_model = "llama3:8b"
    
    def generate_response(self, messages: List[Dict[str, str]], model: str = None, **kwargs) -> str:
        """
        Generate a response using Ollama.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model name to use (defaults to llama3:8b)
            **kwargs: Additional parameters for the API call
            
        Returns:
            Generated response text
        """
        model = model or self.default_model
        
        try:
            # Format the request for Ollama
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                **kwargs
            }
            
            logger.info(f"Sending request to Ollama with model {model}")
            logger.info(f"Messages being sent: {json.dumps(messages, indent=2)}")
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=30
            )
            
            if not response.ok:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                raise Exception(f"Ollama API request failed: {response.status_code}")
            
            data = response.json()
            response_content = data.get('message', {}).get('content', '')
            logger.info(f"Received response: {response_content[:200]}...")
            
            return response_content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise Exception(f"Failed to connect to Ollama: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise Exception(f"Error generating response: {str(e)}")
    
    def generate_personality_response(self, personality: Dict[str, Any], user_message: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """
        Generate a response based on personality configuration.
        
        Args:
            personality: Personality configuration dictionary
            user_message: User's message
            conversation_history: Previous conversation messages
            
        Returns:
            Generated response text
        """
        # Build the conversation context
        messages = []
        
        # Add system prompt based on personality
        system_prompt = personality.get("system_prompt", "")
        logger.info(f"Using system prompt: {system_prompt}")
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        logger.info(f"Final message count: {len(messages)}")
        
        # Generate response
        return self.generate_response(messages)
    
    def test_connection(self) -> bool:
        """Test if Ollama is accessible."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.ok
        except:
            return False

# Global client instance
llm_client = OllamaClient() 
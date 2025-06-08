"""
MiaAI Configuration
"""
import os

# Secret key for sessions
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_please_change_in_production')

# Debug mode
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# Database settings
DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data/memories.db'))

# LLM settings
LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'openai')

# Provider-specific settings
if LLM_PROVIDER == 'openai':
    LLM_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo')
    LLM_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    LLM_API_URL = None
elif LLM_PROVIDER == 'ollama':
    LLM_MODEL = os.environ.get('OLLAMA_MODEL', 'mistral')
    LLM_API_KEY = None
    LLM_API_URL = os.environ.get('OLLAMA_API_URL', 'http://localhost:11434/api')

# Path configuration
UPLOADS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'documents')
DOCUMENTS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'documents')
OUTPUT_DOCUMENTS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output_documents')

# Ensure required directories exist
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
os.makedirs(UPLOADS_PATH, exist_ok=True)
os.makedirs(DOCUMENTS_PATH, exist_ok=True)
os.makedirs(OUTPUT_DOCUMENTS_PATH, exist_ok=True) 
"""
API Routes Package
"""
from flask import Blueprint

# Create blueprints for different API areas
characters_bp = Blueprint('characters', __name__, url_prefix='/api/characters')
chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')
settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')

# Import views to register routes with blueprints
from . import characters, chat, settings

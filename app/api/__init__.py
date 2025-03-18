"""
API endpoints for MiaAI
"""
from flask import Blueprint, send_from_directory, current_app
import os

# Create blueprints
api_bp = Blueprint('api', __name__)
chat_bp = Blueprint('chat', __name__)
characters_bp = Blueprint('characters', __name__)
memories_bp = Blueprint('memories', __name__)
documents_bp = Blueprint('documents', __name__)
settings_bp = Blueprint('settings', __name__)

@api_bp.route('/')
def index():
    """Serve the main application page"""
    return send_from_directory(current_app.static_folder, 'index.html')

@api_bp.route('/js/<path:filename>')
def serve_js(filename):
    """Serve JavaScript files"""
    return send_from_directory(os.path.join(current_app.static_folder, 'js'), filename)

@api_bp.route('/css/<path:filename>')
def serve_css(filename):
    """Serve CSS files"""
    return send_from_directory(os.path.join(current_app.static_folder, 'css'), filename)

@api_bp.route('/img/<path:filename>')
def serve_img(filename):
    """Serve image files"""
    return send_from_directory(os.path.join(current_app.static_folder, 'img'), filename)

@api_bp.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return send_from_directory(current_app.static_folder, 'favicon.ico')

# Import core routes
from app.api import chat
from app.api import characters
from app.api import settings
from app.api import documents  # Explicitly import documents module

# Import optional features
def init_app(app):
    """Initialize API features"""
    with app.app_context():
        # Initialize memory system
        try:
            from app.api.memories import init_app as init_memory
            init_memory(app)
        except Exception as e:
            app.logger.warning(f"Memory system not available: {str(e)}")

        # Initialize document system
        try:
            from app.api.documents import init_app as init_documents
            init_documents(app)
        except Exception as e:
            app.logger.warning(f"Document system not available: {str(e)}")

    return app

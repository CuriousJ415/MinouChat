"""
API Blueprint Initialization
"""
# Only import blueprints, no routes or registration here
from flask import Blueprint, current_app
from .chat import chat_bp
from .characters import characters_bp
from .memories import memories_bp, init_app as init_memories
from .settings import settings_bp
from .documents import documents_bp, init_app as init_documents
from .models import models_bp
from .root import root_bp

def init_app(app):
    """Centralized blueprint registration and initialization"""
    # Register blueprints first
    app.register_blueprint(root_bp)
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(characters_bp, url_prefix='/api/characters')
    app.register_blueprint(memories_bp, url_prefix='/api/memories')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')
    app.register_blueprint(documents_bp, url_prefix='/api/documents')
    app.register_blueprint(models_bp, url_prefix='/api/models')

    # Initialize features within app context
    with app.app_context():
        # Initialize memory system
        try:
            init_memories(app)
            app.logger.info("Memory system initialized successfully")
        except Exception as e:
            app.logger.warning(f"Enhanced memory functions not available: {e}")

        # Initialize document system
        try:
            init_documents(app)
            app.logger.info("Document system initialized successfully")
        except Exception as e:
            app.logger.warning(f"Document system not available: {e}")

    return app

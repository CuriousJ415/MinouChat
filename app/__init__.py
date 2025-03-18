"""
MiaAI Application Factory
"""
import os
from flask import Flask
from flask_cors import CORS
from app.memory.sql import init_db

def create_app(test_config=None):
    """Create and configure the app"""
    app = Flask(__name__, instance_relative_config=True)
    CORS(app)

    # Default configuration
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'memories.db'),
        DATABASE_PATH=os.environ.get('DATABASE_PATH', '/app/data/memories.db'),
        LLM_PROVIDER=os.getenv('LLM_PROVIDER', 'ollama'),
        OLLAMA_HOST=os.getenv('OLLAMA_HOST', 'host.docker.internal'),
        OLLAMA_PORT=os.getenv('OLLAMA_PORT', '11434')
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.update(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize database
    with app.app_context():
        init_db()

    # Initialize API features
    from app.api import init_app as init_api
    try:
        init_api(app)
    except Exception as e:
        app.logger.error(f"Error initializing API features: {e}")

    # Register blueprints
    from app.api import api_bp, chat_bp, characters_bp, memories_bp, settings_bp
    
    # Main API blueprint serves static files and index
    app.register_blueprint(api_bp, url_prefix='/')
    
    # Feature-specific blueprints
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(characters_bp, url_prefix='/api/characters')
    app.register_blueprint(memories_bp, url_prefix='/api/memories')
    # Documents blueprint is registered in its init_app function
    app.register_blueprint(settings_bp, url_prefix='/api/settings')

    # Initialize enhanced components
    initialize_enhanced_components(app)

    # Register CLI commands
    register_commands(app)

    return app

def initialize_enhanced_components(app):
    """Initialize optional enhanced features"""
    # Initialize memory system
    try:
        from app.api.memories import init_app as init_memory
        init_memory(app)
        app.logger.info("Memory system initialized successfully")
    except Exception as e:
        app.logger.warning(f"Enhanced memory functions not available: {e}")

    # Initialize document processor
    try:
        from app.api.documents import init_app as init_documents
        init_documents(app)
        app.logger.info("Document system initialized successfully")
    except Exception as e:
        app.logger.warning(f"Document system not available: {e}")

def register_commands(app):
    """Register CLI commands"""
    @app.cli.command("init-db")
    def init_db_command():
        """Clear existing data and create new tables."""
        init_db()
        app.logger.info("Initialized the database.")

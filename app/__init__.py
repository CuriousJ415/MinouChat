"""
MiaAI Application Package
"""
import os
from flask import Flask, render_template
from dotenv import load_dotenv

def create_app(test_config=None):
    """
    Application factory function.
    Creates and configures the Flask application.
    
    Args:
        test_config: Configuration dictionary for testing
        
    Returns:
        The configured Flask application
    """
    # Load environment variables
    load_dotenv()
    
    # Create and configure the app
    app = Flask(__name__, 
                static_folder='static',
                template_folder='templates')
    
    # Set default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_secret_key'),
        DATABASE_PATH=os.environ.get('DATABASE_PATH', 'memories.db'),
        LLM_PROVIDER=os.environ.get('LLM_PROVIDER', 'ollama'),
        LLM_API_URL=os.environ.get('LLM_API_URL', 'http://localhost:11434/api'),
        LLM_MODEL=os.environ.get('LLM_MODEL', 'mistral'),
        LLM_API_KEY=os.environ.get('LLM_API_KEY', '')
    )
    
    # Override with test config if provided
    if test_config:
        app.config.update(test_config)
    
    # Ensure instance path exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass
    
    # Register blueprints
    from app.api import characters_bp, chat_bp, settings_bp
    app.register_blueprint(characters_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(settings_bp)
    
    # Register CLI commands
    register_commands(app)
    
    # Setup database
    from app.memory import init_db
    init_db(app)
    
    # Root route for application
    @app.route('/')
    def index():
        return render_template('index.html')
    
    # Settings page
    @app.route('/settings')
    def settings():
        return render_template('settings.html')
    
    return app

def register_commands(app):
    """Register CLI commands with the application"""
    @app.cli.command("init-db")
    def init_db_command():
        """Initialize the database."""
        from app.memory import init_db
        init_db(app)
        print("Initialized the database.")

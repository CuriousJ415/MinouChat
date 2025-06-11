"""
Flask web application for MiaChat.
"""

from flask import Flask
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from ..database.config import db_config
from .auth import User
import os

# Initialize Flask extensions
socketio = SocketIO()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates")
    
    # Load configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        SQLALCHEMY_DATABASE_URI=db_config.database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    
    if config:
        app.config.update(config)
    
    # Initialize extensions
    socketio.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Register blueprints
    from .routes import main, auth, personality
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(personality.bp)
    
    # Register user loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.get(user_id)
    
    return app 
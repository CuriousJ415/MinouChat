from flask import Blueprint, send_from_directory, current_app

root_bp = Blueprint('root', __name__)

@root_bp.route('/')
def index():
    """Serve the main application page"""
    return send_from_directory(current_app.static_folder, 'index.html') 
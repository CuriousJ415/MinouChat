from flask import Blueprint, render_template

root_bp = Blueprint('root', __name__)

@root_bp.route('/')
def index():
    """Serve the main application page"""
    return render_template('index.html', characters={}) 
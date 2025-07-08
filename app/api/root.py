from flask import Blueprint, render_template, redirect, url_for
from app.core.auth import get_current_user, require_auth

root_bp = Blueprint('root', __name__)

@root_bp.route('/')
def index():
    """Serve the main application page"""
    user = get_current_user()
    if user:
        # If user is logged in, redirect to dashboard
        return redirect(url_for('root.dashboard'))
    else:
        # If not logged in, show landing page
        return render_template('index.html', characters={})

@root_bp.route('/dashboard')
@require_auth
def dashboard():
    """Dashboard for authenticated users"""
    user = get_current_user()
    return render_template('dashboard.html', user=user) 
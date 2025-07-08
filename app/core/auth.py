"""
Authentication System
Handles user authentication, registration, and session management
"""
import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict
from flask import current_app, request, session
from werkzeug.security import generate_password_hash, check_password_hash

from app.memory.sql import (
    create_user, get_user_by_username, get_user_by_email, get_user_by_id,
    update_user_last_login, create_user_session, get_user_session,
    delete_user_session, cleanup_expired_sessions
)

def generate_session_token() -> str:
    """Generate a secure random session token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))

def hash_password(password: str) -> str:
    """Hash a password using werkzeug's security functions"""
    return generate_password_hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash"""
    return check_password_hash(password_hash, password)

def register_user(username: str, email: str, password: str) -> Optional[Dict]:
    """
    Register a new user
    
    Args:
        username: Username for the new user
        email: Email address for the new user
        password: Plain text password
        
    Returns:
        User dictionary if successful, None if failed
    """
    # Validate input
    if not username or not email or not password:
        return None
    
    if len(password) < 6:
        return None
    
    # Check if username or email already exists
    if get_user_by_username(username):
        return None
    
    if get_user_by_email(email):
        return None
    
    # Hash the password
    password_hash = hash_password(password)
    
    # Create the user
    user = create_user(username, email, password_hash)
    
    if user:
        # Remove password hash from returned data
        user.pop('password_hash', None)
        return user
    
    return None

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """
    Authenticate a user with username and password
    
    Args:
        username: Username or email
        password: Plain text password
        
    Returns:
        User dictionary if successful, None if failed
    """
    # Try to find user by username or email
    user = get_user_by_username(username)
    if not user:
        user = get_user_by_email(username)
    
    if not user:
        return None
    
    # Check if user is active
    if not user.get('is_active', True):
        return None
    
    # Verify password
    if not verify_password(password, user['password_hash']):
        return None
    
    # Update last login
    update_user_last_login(user['id'])
    
    # Remove password hash from returned data
    user.pop('password_hash', None)
    return user

def create_session(user_id: int, remember_me: bool = False) -> Optional[str]:
    """
    Create a new session for a user
    
    Args:
        user_id: User's ID
        remember_me: Whether to create a longer session
        
    Returns:
        Session token if successful, None if failed
    """
    # Generate session token
    session_token = generate_session_token()
    
    # Set expiration time
    if remember_me:
        expires_at = datetime.now() + timedelta(days=30)
    else:
        expires_at = datetime.now() + timedelta(hours=24)
    
    # Create session in database
    if create_user_session(user_id, session_token, expires_at.isoformat()):
        return session_token
    
    return None

def get_current_user() -> Optional[Dict]:
    """
    Get the current authenticated user
    
    Returns:
        User dictionary if authenticated, None if not
    """
    # Check Flask session first
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        if user:
            user.pop('password_hash', None)
            return user
    
    # Check for session token in cookies
    session_token = request.cookies.get('session_token')
    if session_token:
        session_data = get_user_session(session_token)
        if session_data:
            user = get_user_by_id(session_data['user_id'])
            if user:
                user.pop('password_hash', None)
                return user
    
    return None

def login_user(user: Dict, remember_me: bool = False) -> bool:
    """
    Log in a user and create a session
    
    Args:
        user: User dictionary
        remember_me: Whether to create a longer session
        
    Returns:
        True if successful, False if failed
    """
    # Create session token
    session_token = create_session(user['id'], remember_me)
    if not session_token:
        return False
    
    # Set Flask session
    session['user_id'] = user['id']
    session['username'] = user['username']
    
    # Set session token in response cookie
    response = current_app.make_response('')
    if remember_me:
        response.set_cookie('session_token', session_token, max_age=30*24*60*60)  # 30 days
    else:
        response.set_cookie('session_token', session_token, max_age=24*60*60)  # 24 hours
    
    return True

def logout_user() -> bool:
    """
    Log out the current user
    
    Returns:
        True if successful, False if failed
    """
    # Get session token from cookies
    session_token = request.cookies.get('session_token')
    
    # Delete session from database
    if session_token:
        delete_user_session(session_token)
    
    # Clear Flask session
    session.clear()
    
    # Clear session cookie
    response = current_app.make_response('')
    response.delete_cookie('session_token')
    
    return True

def require_auth(f):
    """
    Decorator to require authentication for routes
    
    Usage:
        @app.route('/protected')
        @require_auth
        def protected_route():
            return 'This is protected'
    """
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return {'error': 'Authentication required'}, 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def cleanup_sessions():
    """Clean up expired sessions (call this periodically)"""
    return cleanup_expired_sessions() 
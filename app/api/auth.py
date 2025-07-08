from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from app.core.auth import register_user, authenticate_user, login_user, logout_user, get_current_user, require_auth

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        remember_me = data.get('remember_me', False)
        
        if not username or not password:
            if request.is_json:
                return jsonify({"success": False, "error": "Username and password are required"}), 400
            else:
                flash('Username and password are required', 'error')
                return render_template('auth/login.html')
        
        # Authenticate user
        user = authenticate_user(username, password)
        
        if user:
            # Log in the user
            if login_user(user, remember_me):
                if request.is_json:
                    return jsonify({
                        "success": True, 
                        "message": "Login successful",
                        "user": {
                            "id": user['id'],
                            "username": user['username'],
                            "email": user['email']
                        }
                    })
                else:
                    flash('Login successful!', 'success')
                    return redirect(url_for('root.index'))
            else:
                if request.is_json:
                    return jsonify({"success": False, "error": "Failed to create session"}), 500
                else:
                    flash('Failed to create session', 'error')
                    return render_template('auth/login.html')
        else:
            if request.is_json:
                return jsonify({"success": False, "error": "Invalid username or password"}), 401
            else:
                flash('Invalid username or password', 'error')
                return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        
        # Validate input
        if not username or not email or not password:
            if request.is_json:
                return jsonify({"success": False, "error": "All fields are required"}), 400
            else:
                flash('All fields are required', 'error')
                return render_template('auth/register.html')
        
        if password != confirm_password:
            if request.is_json:
                return jsonify({"success": False, "error": "Passwords do not match"}), 400
            else:
                flash('Passwords do not match', 'error')
                return render_template('auth/register.html')
        
        if len(password) < 6:
            if request.is_json:
                return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400
            else:
                flash('Password must be at least 6 characters', 'error')
                return render_template('auth/register.html')
        
        # Register user
        user = register_user(username, email, password)
        
        if user:
            # Automatically log in the user
            if login_user(user):
                if request.is_json:
                    return jsonify({
                        "success": True, 
                        "message": "Registration successful",
                        "user": {
                            "id": user['id'],
                            "username": user['username'],
                            "email": user['email']
                        }
                    })
                else:
                    flash('Registration successful!', 'success')
                    return redirect(url_for('root.index'))
            else:
                if request.is_json:
                    return jsonify({"success": False, "error": "Registration successful but failed to log in"}), 500
                else:
                    flash('Registration successful but failed to log in', 'warning')
                    return redirect(url_for('auth.login'))
        else:
            if request.is_json:
                return jsonify({"success": False, "error": "Username or email already exists"}), 409
            else:
                flash('Username or email already exists', 'error')
                return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    """Handle user logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('root.index'))

@auth_bp.route('/api/logout', methods=['POST'])
def api_logout():
    """API endpoint for logout"""
    logout_user()
    return jsonify({"success": True, "message": "Logout successful"})

@auth_bp.route('/api/me')
@require_auth
def get_current_user_info():
    """Get current user information"""
    user = get_current_user()
    if user:
        return jsonify({
            "success": True,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "created_at": user['created_at'],
                "last_login": user['last_login']
            }
        })
    else:
        return jsonify({"success": False, "error": "User not found"}), 404

@auth_bp.route('/api/check-auth')
def check_auth():
    """Check if user is authenticated"""
    user = get_current_user()
    if user:
        return jsonify({
            "success": True,
            "authenticated": True,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email']
            }
        })
    else:
        return jsonify({
            "success": True,
            "authenticated": False
        }) 
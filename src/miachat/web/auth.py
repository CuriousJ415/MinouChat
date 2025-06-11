"""
Authentication module for MiaChat web interface.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import UserMixin, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import Session
from ..database.config import get_db
from ..database.models import User as UserModel
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email

bp = Blueprint('auth', __name__)

class User(UserMixin):
    """User class for authentication."""
    
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email
    
    @staticmethod
    def get(user_id):
        """Get user by ID."""
        with next(get_db()) as db:
            user = db.query(UserModel).get(user_id)
            if user:
                return User(user.id, user.username, user.email)
        return None
    
    @staticmethod
    def authenticate(username, password):
        """Authenticate user with username and password."""
        with next(get_db()) as db:
            user = db.query(UserModel).filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                return User(user.id, user.username, user.email)
        return None
    
    @staticmethod
    def create(username, email, password):
        """Create a new user."""
        with next(get_db()) as db:
            if db.query(UserModel).filter_by(username=username).first():
                return None
            
            user = UserModel(
                username=username,
                email=email,
                password_hash=generate_password_hash(password)
            )
            db.add(user)
            db.commit()
            return User(user.id, user.username, user.email)

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page."""
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        user = User.create(username, email, password)
        if user:
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Username already exists')
    return render_template('auth/register.html', form=form) 
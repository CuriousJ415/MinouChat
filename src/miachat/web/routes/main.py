from flask import Blueprint, render_template

bp = Blueprint('root', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@bp.route('/chat')
def chat():
    return render_template('chat.html') 
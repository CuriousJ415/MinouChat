from flask import Blueprint, render_template

bp = Blueprint('personality', __name__, url_prefix='/personalities')

@bp.route('/')
def list_personalities():
    return render_template('personality/list.html')

@bp.route('/create', methods=['GET', 'POST'])
def create_personality():
    return render_template('personality/create.html')

@bp.route('/<int:personality_id>/edit', methods=['GET', 'POST'])
def edit_personality(personality_id):
    return render_template('personality/edit.html', personality_id=personality_id) 
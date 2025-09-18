from flask import Blueprint, render_template

bp = Blueprint('persona', __name__, url_prefix='/personas')

@bp.route('/')
def list_personas():
    return render_template('persona/list.html')

@bp.route('/create', methods=['GET', 'POST'])
def create_persona():
    return render_template('persona/create.html')

@bp.route('/<int:persona_id>/edit', methods=['GET', 'POST'])
def edit_persona(persona_id):
    return render_template('persona/edit.html', persona_id=persona_id) 
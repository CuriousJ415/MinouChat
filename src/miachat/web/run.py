"""
Script to run the MiaChat web application.
"""

import os
from .app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=8080) 
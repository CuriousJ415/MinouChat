#!/usr/bin/env python3
"""
MiaAI Web Application Entry Point
"""
import os
from dotenv import load_dotenv
from flask import jsonify, render_template
from app import create_app

# Load environment variables
load_dotenv()

# Create the application, explicitly set the template folder
app = create_app()
# app.template_folder = os.path.join(os.path.dirname(__file__), 'templates')

# Add health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint for Docker and monitoring"""
    return jsonify({
        "status": "ok",
        "version": os.environ.get("VERSION", "1.0.0"),
        "message": "MiaAI is running properly"
    })

@app.route('/config')
def config():
    return render_template('config.html')

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8080))
    
    # Get debug mode from environment or use default
    debug = os.environ.get("DEBUG", "False").lower() in ("true", "1", "t")
    
    # Run the application
    app.run(host="0.0.0.0", port=port, debug=debug)
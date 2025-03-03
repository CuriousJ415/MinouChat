#!/usr/bin/env python3
"""
MiaAI - A conversational AI assistant application with memory
Run this file to start the web application
"""
import os
from dotenv import load_dotenv

# Load environment variables before any other imports
load_dotenv()

from app import create_app

# Get configuration from environment
debug = os.getenv('DEBUG', 'False').lower() in ('true', 't', '1')
port = int(os.getenv('PORT', 8080))
host = '0.0.0.0'  # Allow external connections for Docker compatibility

# Create and run application
app = create_app()

if __name__ == '__main__':
    print(f"Starting MiaAI on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)

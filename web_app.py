#!/usr/bin/env python3
"""
MiaAI Web Application Entry Point
"""
import os
from dotenv import load_dotenv
from app import create_app

# Load environment variables
load_dotenv()

# Create the application
app = create_app()

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8080))
    
    # Get debug mode from environment or use default
    debug = os.environ.get("DEBUG", "False").lower() in ("true", "1", "t")
    
    # Run the application
    app.run(host="0.0.0.0", port=port, debug=debug)
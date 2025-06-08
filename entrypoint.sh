#!/bin/bash

# Create data directory if it doesn't exist
mkdir -p /app/data

# Run Flask application with gunicorn
exec gunicorn --bind 0.0.0.0:8080 --workers 1 --threads 8 --timeout 0 "web_app:app" 
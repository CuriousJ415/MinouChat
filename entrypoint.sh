#!/bin/bash

# Create data directory if it doesn't exist
mkdir -p /app/data

# Set PYTHONPATH for miachat module imports
export PYTHONPATH=/app/src:$PYTHONPATH

# Run FastAPI application with uvicorn
exec uvicorn miachat.api.main:app --host 0.0.0.0 --port 8080 --workers 1
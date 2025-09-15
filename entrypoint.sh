#!/bin/bash

# Create data directory if it doesn't exist
mkdir -p /app/data

# Run FastAPI application with uvicorn
exec uvicorn src.miachat.api.main:app --host 0.0.0.0 --port 8080 --workers 1 
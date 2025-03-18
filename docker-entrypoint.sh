#!/bin/bash
set -e

# Set up environment variables
export PYTHONPATH=/app:$PYTHONPATH

# Create necessary directories
mkdir -p /app/data
mkdir -p /app/documents
mkdir -p /app/output_documents

# Initialize the database before starting the application
echo "Initializing database..."
python /app/init_db.py

# Get the LLM provider from environment or config
LLM_PROVIDER=${LLM_PROVIDER:-ollama}
echo "Using LLM provider: ${LLM_PROVIDER}"

# If using Ollama, check if it's accessible
if [ "$LLM_PROVIDER" = "ollama" ]; then
    echo "Checking Ollama connection..."
    if curl -s -f "http://host.docker.internal:11434/api/version" > /dev/null; then
        echo "Successfully connected to Ollama at host.docker.internal"
        export OLLAMA_API_URL="http://host.docker.internal:11434/api"
    else
        echo "Warning: Could not connect to Ollama at host.docker.internal"
        echo "Make sure Ollama is running on your host machine"
    fi
fi

# Start the application
exec python /app/web_app.py 
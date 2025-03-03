#!/bin/bash

# Display ASCII art header
echo "====================================="
echo "     __  __ _        _    ___ "
echo "    |  \/  (_)__ _  /_\  |_ _|"
echo "    | |\/| | / _' |/ _ \  | | "
echo "    |_|  |_|_\__,_/_/ \_\|___|"
echo "                              "
echo "====================================="
echo "      Containerized Chatbot"
echo "====================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Make sure ngrok_setup.py is executable
chmod +x ngrok_setup.py

# Ensure the templates directory exists
mkdir -p templates

# Create directories for persistent storage
mkdir -p ./data
mkdir -p ./config
mkdir -p ./templates

# Check if .env file exists, create it if not
if [ ! -f .env ]; then
    echo "ℹ️ Creating default .env file..."
    cat > .env << EOL
# Ngrok configuration (if used)
NGROK_AUTH_TOKEN=your_ngrok_auth_token
NGROK_DOMAIN=your-reserved-domain.ngrok.io

# LLM configuration
LLM_PROVIDER=ollama
LLM_API_URL=http://ollama:11434/api
LLM_MODEL=mistral
LLM_API_KEY=

# MiaAI configuration
DATABASE_PATH=/data/memories.db
PORT=8080
DEBUG=False
SECRET_KEY=$(openssl rand -hex 16)
EOL
    echo "⚠️ Please edit the .env file to set your provider credentials if needed"
fi

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Pull the latest images and build services
echo "🔄 Building Docker images..."
docker-compose build

# Start the services
echo "🚀 Starting MiaAI services..."
docker-compose up -d

# Check if services started successfully
if [ $? -eq 0 ]; then
    echo "✅ Services started successfully!"
    echo ""
    echo "📱 Local access: http://localhost:8080"
    echo ""
    echo "🌐 To enable remote access via ngrok, run:"
    echo "    python ngrok_setup.py"
    echo ""
    echo "📊 To view logs:"
    echo "    docker-compose logs -f"
    echo ""
    echo "⏹️ To stop services:"
    echo "    ./stop.sh"
else
    echo "❌ Failed to start services. Check the logs with:"
    echo "    docker-compose logs"
fi
#!/bin/bash

echo "====================================="
echo "      Updating MiaAI services       "
echo "====================================="
echo ""

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "🔄 Stopping running services..."
    docker-compose down
fi

# Pull latest image for Ollama
echo "🔄 Pulling latest Ollama image..."
docker pull ollama/ollama:latest

# Rebuild the MiaAI image
echo "🔄 Rebuilding MiaAI image with latest code..."
docker-compose build --no-cache miaai

# Start services
echo "🚀 Starting updated services..."
docker-compose up -d

if [ $? -eq 0 ]; then
    echo "✅ Update completed successfully!"
    echo ""
    echo "📱 Local access: http://localhost:8080"
    echo ""
    echo "🌐 To enable remote access via ngrok, run:"
    echo "    python ngrok_setup.py"
else
    echo "❌ Update failed. Check the logs with:"
    echo "    docker-compose logs"
fi
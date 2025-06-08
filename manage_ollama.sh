#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${2}${1}${NC}"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_message "Docker is not running. Please start Docker first." "$RED"
        exit 1
    fi
}

# Function to check if Ollama is running
check_ollama() {
    if docker ps | grep -q ollama; then
        return 0
    else
        return 1
    fi
}

# Function to start Ollama
start_ollama() {
    print_message "Starting Ollama..." "$YELLOW"
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        print_message "Creating .env file..." "$YELLOW"
        echo "NGROK_AUTH_TOKEN=" > .env
        print_message "Please add your Ngrok auth token to the .env file" "$YELLOW"
        exit 1
    fi
    
    # Start Ollama with Docker Compose
    docker-compose -f docker-compose.ollama.yml up -d
    
    if [ $? -eq 0 ]; then
        print_message "Ollama started successfully!" "$GREEN"
        print_message "You can access Ollama at http://localhost:11434" "$GREEN"
        print_message "Ngrok tunnel status available at http://localhost:4040" "$GREEN"
    else
        print_message "Failed to start Ollama" "$RED"
        exit 1
    fi
}

# Function to stop Ollama
stop_ollama() {
    print_message "Stopping Ollama..." "$YELLOW"
    docker-compose -f docker-compose.ollama.yml down
    
    if [ $? -eq 0 ]; then
        print_message "Ollama stopped successfully!" "$GREEN"
    else
        print_message "Failed to stop Ollama" "$RED"
        exit 1
    fi
}

# Function to show Ollama status
status_ollama() {
    if check_ollama; then
        print_message "Ollama is running" "$GREEN"
        print_message "Local URL: http://localhost:11434" "$GREEN"
        print_message "Ngrok status: http://localhost:4040" "$GREEN"
    else
        print_message "Ollama is not running" "$RED"
    fi
}

# Function to pull a model
pull_model() {
    if [ -z "$1" ]; then
        print_message "Please specify a model name" "$RED"
        exit 1
    fi
    
    print_message "Pulling model: $1" "$YELLOW"
    docker exec ollama ollama pull "$1"
    
    if [ $? -eq 0 ]; then
        print_message "Model pulled successfully!" "$GREEN"
    else
        print_message "Failed to pull model" "$RED"
        exit 1
    fi
}

# Function to list available models
list_models() {
    print_message "Available models:" "$YELLOW"
    docker exec ollama ollama list
}

# Main script
case "$1" in
    start)
        check_docker
        start_ollama
        ;;
    stop)
        check_docker
        stop_ollama
        ;;
    restart)
        check_docker
        stop_ollama
        start_ollama
        ;;
    status)
        check_docker
        status_ollama
        ;;
    pull)
        check_docker
        pull_model "$2"
        ;;
    list)
        check_docker
        list_models
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|pull|list}"
        echo "  start   - Start Ollama"
        echo "  stop    - Stop Ollama"
        echo "  restart - Restart Ollama"
        echo "  status  - Show Ollama status"
        echo "  pull    - Pull a model (e.g., $0 pull mistral)"
        echo "  list    - List available models"
        exit 1
        ;;
esac

exit 0 
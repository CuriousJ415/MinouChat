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

# Function to check if Ollama is installed
check_ollama_installed() {
    if ! command -v ollama &> /dev/null; then
        print_message "Ollama is not installed. Please install it first:" "$RED"
        print_message "Visit https://ollama.ai/download for installation instructions" "$YELLOW"
        exit 1
    fi
}

# Function to check if Ollama is running
check_ollama_running() {
    if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
        return 1
    else
        return 0
    fi
}

# Function to start Ollama
start_ollama() {
    print_message "Starting Ollama..." "$YELLOW"
    
    # Check if Ollama is already running
    if check_ollama_running; then
        print_message "Ollama is already running" "$GREEN"
        return 0
    fi
    
    # Start Ollama in the background
    ollama serve &
    
    # Wait for Ollama to start
    for i in {1..30}; do
        if check_ollama_running; then
            print_message "Ollama started successfully!" "$GREEN"
            return 0
        fi
        sleep 1
    done
    
    print_message "Failed to start Ollama" "$RED"
    return 1
}

# Function to stop Ollama
stop_ollama() {
    print_message "Stopping Ollama..." "$YELLOW"
    
    # Find Ollama process
    OLLAMA_PID=$(pgrep -f "ollama serve")
    
    if [ -n "$OLLAMA_PID" ]; then
        kill $OLLAMA_PID
        print_message "Ollama stopped successfully!" "$GREEN"
    else
        print_message "Ollama is not running" "$YELLOW"
    fi
}

# Function to show Ollama status
status_ollama() {
    if check_ollama_running; then
        print_message "Ollama is running" "$GREEN"
        print_message "Local URL: http://localhost:11434" "$GREEN"
        
        # Show available models
        print_message "\nAvailable models:" "$YELLOW"
        curl -s http://localhost:11434/api/tags | jq -r '.models[].name'
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
    ollama pull "$1"
    
    if [ $? -eq 0 ]; then
        print_message "Model pulled successfully!" "$GREEN"
    else
        print_message "Failed to pull model" "$RED"
        exit 1
    fi
}

# Function to list available models
list_models() {
    if ! check_ollama_running; then
        print_message "Ollama is not running" "$RED"
        exit 1
    fi
    
    print_message "Available models:" "$YELLOW"
    curl -s http://localhost:11434/api/tags | jq -r '.models[].name'
}

# Main script
case "$1" in
    start)
        check_ollama_installed
        start_ollama
        ;;
    stop)
        check_ollama_installed
        stop_ollama
        ;;
    restart)
        check_ollama_installed
        stop_ollama
        start_ollama
        ;;
    status)
        check_ollama_installed
        status_ollama
        ;;
    pull)
        check_ollama_installed
        pull_model "$2"
        ;;
    list)
        check_ollama_installed
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
#!/bin/bash

# Display ASCII art header
echo "====================================="
echo "     __  __ _        _    ___ "
echo "    |  \/  (_)__ _  /_\  |_ _|"
echo "    | |\/| | / _' |/ _ \  | | "
echo "    |_|  |_|_\__,_/_/ \_\|___|"
echo "                              "
echo "====================================="
echo "      Starting MiaAI..."
echo "====================================="
echo ""

# Path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Kill any existing instances of the app
echo "🔄 Stopping existing instances..."
pkill -f 'python web_app.py' || true
sleep 1

# Activate the Python virtual environment
if [ -d ".venv/bin" ]; then
    echo "🐍 Activating virtual environment (.venv)..."
    source .venv/bin/activate
elif [ -d "venv/bin" ]; then
    echo "🐍 Activating virtual environment (venv)..."
    source venv/bin/activate
else
    echo "⚠️ No virtual environment found. Using system Python."
fi

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed or not in PATH."
    exit 1
fi

# Check if the database file exists, if not create a backup
if [ ! -f "memories.db" ]; then
    echo "⚠️ Database file not found. Creating a new one..."
fi

# Start the application
echo "🚀 Starting MiaAI web app..."
python web_app.py &
APP_PID=$!

# Wait for the app to start
echo "⏳ Waiting for the app to start..."
sleep 3

# Open the application in the browser
echo "🌐 Opening MiaAI in your browser..."
open http://localhost:8080

echo ""
echo "✅ MiaAI is now running!"
echo "📝 Access the app at: http://localhost:8080"
echo "⏹️ To stop, press Ctrl+C or run: pkill -f 'python web_app.py'"
echo ""

# Optional: wait for the user to press Ctrl+C
# trap "pkill -P $APP_PID; exit" INT TERM
# wait $APP_PID 
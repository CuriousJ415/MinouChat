#!/bin/bash

# Set the app name and paths
APP_NAME="MiaAI"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PATH="/Applications/$APP_NAME.app"

# Create an AppleScript that launches the app
cat > /tmp/miaai_launcher.applescript << EOF
on run
    tell application "Terminal"
        -- Get the current path
        set projectPath to "$PROJECT_DIR"
        
        -- More thoroughly kill any existing instances
        do script "cd '" & projectPath & "' && (pkill -f 'python web_app.py' || true) && (lsof -ti:8080 | xargs kill -9 || true); sleep 1"
        
        -- Activate the Python virtual environment and start the app
        do script "cd '" & projectPath & "' && if [ -d '.venv/bin' ]; then source .venv/bin/activate; elif [ -d 'venv/bin' ]; then source venv/bin/activate; fi && python web_app.py &" in front window
        
        -- Wait a moment before opening the browser
        delay 2
        
        -- Open the browser
        do shell script "open http://localhost:8080"
        
        -- Hide Terminal after launching (optional - uncomment to hide Terminal)
        -- delay 3
        -- set visible of front window to false
    end tell
end run
EOF

# Compile the AppleScript to an application
echo "🔄 Creating $APP_NAME.app in /Applications folder..."
osacompile -o "$APP_PATH" /tmp/miaai_launcher.applescript

# Clean up
rm /tmp/miaai_launcher.applescript

echo "✅ Created $APP_NAME app at: $APP_PATH"
echo "🚀 You can now launch MiaAI from your Applications folder!" 
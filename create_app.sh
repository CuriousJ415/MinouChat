#!/bin/bash

# Set the app name and paths
APP_NAME="MiaAI"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$PROJECT_DIR/MiaAI_launcher.sh"
APP_PATH="/Applications/$APP_NAME.app"

# Check if the launcher script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Launcher script not found at: $SCRIPT_PATH"
    exit 1
fi

# Ensure it's executable
chmod +x "$SCRIPT_PATH"

# Create the AppleScript that will launch our shell script
APPLESCRIPT=$(cat <<EOF
tell application "Terminal"
    do script "bash '$SCRIPT_PATH'"
end tell
EOF
)

# Create a temporary AppleScript file
TEMP_APPLESCRIPT="/tmp/miaai_launcher.scpt"
echo "$APPLESCRIPT" > "$TEMP_APPLESCRIPT"

# Compile the AppleScript into an application
echo "🔄 Creating $APP_NAME.app in /Applications folder..."
osacompile -o "$APP_PATH" "$TEMP_APPLESCRIPT"

# Clean up
rm "$TEMP_APPLESCRIPT"

echo "✅ Created $APP_NAME app at: $APP_PATH"
echo "🚀 You can now launch MiaAI from your Applications folder!" 
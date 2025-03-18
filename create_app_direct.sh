#!/bin/bash

# Set the app name and paths
APP_NAME="MiaAI"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PATH="/Applications/$APP_NAME.app"
CONTENTS_PATH="$APP_PATH/Contents"
MACOS_PATH="$CONTENTS_PATH/MacOS"
RESOURCES_PATH="$CONTENTS_PATH/Resources"

# Create app directory structure
echo "🔄 Creating $APP_NAME.app..."
mkdir -p "$MACOS_PATH" "$RESOURCES_PATH"

# Create the launcher script
LAUNCHER_SCRIPT="$MACOS_PATH/launcher"
cat > "$LAUNCHER_SCRIPT" << 'EOF'
#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
PROJECT_DIR="$(dirname "$APP_DIR/Contents/Resources/project_path.txt")"

# Change to the project directory
cd "$PROJECT_DIR"

# Kill any existing instances
pkill -f 'python web_app.py' || true
sleep 1

# Activate the Python virtual environment
if [ -d ".venv/bin" ]; then
    source .venv/bin/activate
elif [ -d "venv/bin" ]; then
    source venv/bin/activate
fi

# Start the application
python web_app.py &
PID=$!

# Wait for the app to start
sleep 2

# Open the browser
open http://localhost:8080

# Optional: keep the script running to manage the process
# trap "kill $PID; exit" INT TERM
# wait $PID
EOF

# Make the launcher script executable
chmod +x "$LAUNCHER_SCRIPT"

# Save the project path
echo "$PROJECT_DIR" > "$RESOURCES_PATH/project_path.txt"

# Create the Info.plist file
cat > "$CONTENTS_PATH/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.miaai.app</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>MiaAI</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Create a basic AppleScript runner for the launcher
APPLESCRIPT=$(cat <<EOF
do shell script quoted form of "$MACOS_PATH/launcher"
EOF
)

# Create and compile the AppleScript
TEMP_APPLESCRIPT="/tmp/miaai_direct.scpt"
echo "$APPLESCRIPT" > "$TEMP_APPLESCRIPT"
osacompile -o "$TEMP_APPLESCRIPT.app" "$TEMP_APPLESCRIPT"

# Copy the AppleScript app's applet
cp -f "$TEMP_APPLESCRIPT.app/Contents/MacOS/applet" "$MACOS_PATH/applet"
chmod +x "$MACOS_PATH/applet"

# Update the Info.plist to use applet instead of launcher
sed -i '' 's/<string>launcher<\/string>/<string>applet<\/string>/g' "$CONTENTS_PATH/Info.plist"

# Clean up
rm -rf "$TEMP_APPLESCRIPT" "$TEMP_APPLESCRIPT.app"

echo "✅ Created $APP_NAME app at: $APP_PATH"
echo "🚀 You can now launch MiaAI from your Applications folder!" 
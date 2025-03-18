-- MiaAI Launcher Creator Script
-- This script creates a clickable app that launches MiaAI

tell application "Finder"
    -- Get the path to the miaai-v1 project folder
    set projectPath to POSIX path of (container of (path to me)) as string
    
    -- Define the script content for the launcher
    set launcherScript to "#!/bin/bash
    
# Change to the MiaAI project directory
cd \"" & projectPath & "\"

# Kill any existing instances of the app
pkill -f 'python web_app.py' || true

# Activate the Python virtual environment (adjust the path if needed)
if [ -d \".venv/bin\" ]; then
    source .venv/bin/activate
elif [ -d \"venv/bin\" ]; then
    source venv/bin/activate
fi

# Start the application
python web_app.py &

# Open the application in the browser after a short delay
sleep 2
open http://localhost:8080
"
    
    -- Create a temporary script file
    set tempScript to projectPath & "temp_launcher.sh"
    do shell script "echo '" & launcherScript & "' > " & quoted form of tempScript & " && chmod +x " & quoted form of tempScript
    
    -- Save the launcher app to the Applications folder
    set appPath to "/Applications/MiaAI.app"
    do shell script "osacompile -o " & quoted form of appPath & " " & quoted form of tempScript
    
    -- Set the app icon (optional - you would need an icon file)
    -- do shell script "sips -i /path/to/icon.png && DeRez -only icns /path/to/icon.png > /tmp/icon.rsrc && Rez -append /tmp/icon.rsrc -o " & quoted form of appPath & "/Contents/Resources/applet.rsrc"
    
    -- Clean up
    do shell script "rm " & quoted form of tempScript
    
    -- Confirm completion
    display dialog "MiaAI Launcher has been created in your Applications folder." buttons {"OK"} default button 1
end tell 
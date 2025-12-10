#!/bin/bash

echo "====================================="
echo "     Stopping MiaAI services...     "
echo "====================================="
echo ""

# Stop the services
docker-compose down

if [ $? -eq 0 ]; then
    echo "✅ Services stopped successfully!"
    echo ""
    echo "💡 Your data is preserved in Docker volumes"
    echo "💡 Start services again with: ./start.sh"
else
    echo "❌ Failed to stop services properly. Try running:"
    echo "    docker-compose down --remove-orphans"
fi

# Kill any running ngrok processes
if pgrep -f "ngrok" > /dev/null; then
    echo "🔄 Stopping ngrok tunnel..."
    pkill -f "ngrok"
fi

# Remove ngrok URL file if it exists
if [ -f "ngrok_url.txt" ]; then
    rm ngrok_url.txt
fi

echo ""
echo "👋 Goodbye!"
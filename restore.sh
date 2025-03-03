#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: ./restore.sh <backup_file>"
    echo "Example: ./restore.sh ./backups/miaai_backup_20250218_120000.tar.gz"
    exit 1
fi

BACKUP_FILE=$1

echo "====================================="
echo "       Restoring MiaAI data          "
echo "====================================="
echo ""

# Check if backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    echo "❌ Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

# Create temporary directory for extraction
mkdir -p ./temp_restore

# Extract backup
echo "🔄 Extracting backup file..."
tar -xzf ${BACKUP_FILE} -C ./temp_restore

if [ $? -ne 0 ]; then
    echo "❌ Failed to extract backup file"
    rm -rf ./temp_restore
    exit 1
fi

# Check if container is running
if docker ps | grep -q "miaai-app"; then
    echo "🔄 Container is running, copying database file into container..."
    
    # Copy database to container
    docker cp ./temp_restore/memories.db miaai-app:/data/
    
    if [ $? -eq 0 ]; then
        echo "✅ Database restored successfully"
        # Restart the container to ensure it uses the new database
        docker-compose restart miaai
        echo "🔄 Restarted MiaAI container to apply changes"
    else
        echo "❌ Failed to copy database to container"
        rm -rf ./temp_restore
        exit 1
    fi
else
    echo "⚠️ Container is not running, attempting to restore volume data..."
    
    # For non-running containers, try to restore the volume directly
    # Start the container first to ensure volume is created
    docker-compose up -d miaai
    sleep 5
    
    # Now try to copy the database
    docker cp ./temp_restore/memories.db miaai-app:/data/
    
    if [ $? -eq 0 ]; then
        echo "✅ Database restored successfully"
        # Restart the container to ensure it uses the new database
        docker-compose restart miaai
        echo "🔄 Restarted MiaAI container to apply changes"
    else
        echo "❌ Failed to restore database. Please check container logs"
        docker-compose logs miaai
        rm -rf ./temp_restore
        exit 1
    fi
fi

# Clean up
rm -rf ./temp_restore

echo ""
echo "✅ Restore process completed"
echo "💡 Your MiaAI should now be using the restored data"
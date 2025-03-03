#!/bin/bash

# Create timestamp for backup filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="./backups"
BACKUP_FILE="${BACKUP_DIR}/miaai_backup_${TIMESTAMP}.tar.gz"

echo "====================================="
echo "        Backing up MiaAI data        "
echo "====================================="
echo ""

# Create backups directory if it doesn't exist
mkdir -p ${BACKUP_DIR}

# Check if container is running
if docker ps | grep -q "miaai-app"; then
    echo "🔄 Container is running, copying database file first..."
    # Create temporary directory
    mkdir -p ./temp_backup
    
    # Copy database from container
    docker cp miaai-app:/data/memories.db ./temp_backup/
    
    if [ $? -eq 0 ]; then
        echo "✅ Database file copied successfully"
        
        # Create tarball of the database
        tar -czf ${BACKUP_FILE} -C ./temp_backup memories.db
        
        if [ $? -eq 0 ]; then
            echo "✅ Backup created: ${BACKUP_FILE}"
            # Remove temporary files
            rm -rf ./temp_backup
        else
            echo "❌ Failed to create backup archive"
            exit 1
        fi
    else
        echo "❌ Failed to copy database from container"
        rm -rf ./temp_backup
        exit 1
    fi
else
    echo "⚠️ Container is not running, attempting to backup volume data..."
    
    # For non-running containers, try to backup the volume directly
    # This is less reliable but might work depending on volume configuration
    VOLUME_PATH=$(docker volume inspect miaai-data | grep "Mountpoint" | cut -d'"' -f4)
    
    if [ -n "$VOLUME_PATH" ] && [ -d "$VOLUME_PATH" ]; then
        echo "🔄 Found volume path: $VOLUME_PATH"
        # Create tarball of the volume
        sudo tar -czf ${BACKUP_FILE} -C ${VOLUME_PATH} .
        
        if [ $? -eq 0 ]; then
            echo "✅ Backup created: ${BACKUP_FILE}"
            sudo chown $(whoami) ${BACKUP_FILE}
        else
            echo "❌ Failed to create backup archive"
            exit 1
        fi
    else
        echo "❌ Could not locate volume data. Please start the container first."
        exit 1
    fi
fi

echo ""
echo "✅ Backup process completed"
echo "💡 To restore, use: ./restore.sh ${BACKUP_FILE}"
#!/bin/bash

# Meesho Order Scanner - Update Script
# Run this script to update the application on EC2

set -e

APP_DIR="/home/ubuntu/MeeshoScanner"
BACKUP_DIR="/home/ubuntu/backups"

echo "🔄 Updating Meesho Order Scanner..."

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Backup current uploads
if [ -d "$APP_DIR/uploads" ]; then
    echo "📁 Backing up uploads..."
    cp -r "$APP_DIR/uploads" "$BACKUP_DIR/uploads_$(date +%Y%m%d_%H%M%S)"
fi

# Navigate to app directory
cd "$APP_DIR"

# Pull latest changes
echo "📥 Pulling latest changes..."
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Update dependencies
echo "📦 Updating dependencies..."
pip install --upgrade -r requirements.txt

# Restart services
echo "🔄 Restarting services..."
sudo systemctl restart meesho-scanner.service
sudo systemctl restart nginx

# Wait for services to start
sleep 3

# Check if services are running
if sudo systemctl is-active --quiet meesho-scanner.service; then
    echo "✅ Application updated and running successfully!"
else
    echo "❌ Application failed to start. Check logs:"
    sudo journalctl -u meesho-scanner.service --no-pager -n 20
fi

echo "🎉 Update completed!"

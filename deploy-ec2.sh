#!/bin/bash

# Meesho Order Scanner - EC2 Deployment Script
# Run this script on your EC2 instance after connecting via SSH

set -e

echo "🚀 Starting Meesho Order Scanner EC2 deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Update system
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install system dependencies
print_status "Installing system dependencies..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libffi-dev \
    nginx \
    git \
    curl \
    wget \
    unzip \
    htop \
    ufw

# Create application directory
APP_DIR="/home/ubuntu/MeeshoScanner"
print_status "Setting up application directory..."

if [ -d "$APP_DIR" ]; then
    print_warning "Application directory already exists. Backing up..."
    mv "$APP_DIR" "${APP_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
fi

# Clone repository (replace with your actual repo URL)
print_status "Cloning repository..."
git clone https://github.com/VirajYR/MeeshoScanner.git "$APP_DIR"
cd "$APP_DIR"

# Create virtual environment
print_status "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Create necessary directories
print_status "Creating application directories..."
mkdir -p uploads logs static/uploads

# Set permissions
chmod 755 uploads logs
chmod 644 requirements.txt

# Create systemd service
print_status "Creating systemd service..."
sudo tee /etc/systemd/system/meesho-scanner.service > /dev/null <<EOF
[Unit]
Description=Meesho Order Scanner
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/gunicorn --config gunicorn.conf.py app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx
print_status "Configuring Nginx..."
sudo tee /etc/nginx/sites-available/meesho-scanner > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias $APP_DIR/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable Nginx site
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/meesho-scanner /etc/nginx/sites-enabled/
sudo nginx -t

# Configure firewall
print_status "Configuring firewall..."
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'

# Start services
print_status "Starting services..."
sudo systemctl enable meesho-scanner.service
sudo systemctl start meesho-scanner.service
sudo systemctl enable nginx
sudo systemctl restart nginx

# Wait a moment for services to start
sleep 5

# Check service status
print_status "Checking service status..."
if sudo systemctl is-active --quiet meesho-scanner.service; then
    print_status "✅ Meesho Scanner service is running"
else
    print_error "❌ Meesho Scanner service failed to start"
    sudo systemctl status meesho-scanner.service
fi

if sudo systemctl is-active --quiet nginx; then
    print_status "✅ Nginx is running"
else
    print_error "❌ Nginx failed to start"
    sudo systemctl status nginx
fi

# Get public IP
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

print_status "🎉 Deployment completed successfully!"
echo
echo "📱 Your Meesho Order Scanner is now accessible at:"
echo "   http://$PUBLIC_IP"
echo
echo "🔧 Useful commands:"
echo "   sudo systemctl status meesho-scanner.service  # Check app status"
echo "   sudo systemctl restart meesho-scanner.service # Restart app"
echo "   sudo journalctl -u meesho-scanner.service -f  # View app logs"
echo "   sudo nginx -t && sudo systemctl restart nginx # Restart nginx"
echo
echo "📁 Application directory: $APP_DIR"
echo "📋 Logs directory: $APP_DIR/logs"
echo "📤 Uploads directory: $APP_DIR/uploads"

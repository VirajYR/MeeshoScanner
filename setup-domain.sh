#!/bin/bash

# Meesho Scanner Domain Setup Script
# Usage: ./setup-domain.sh yourdomain.com

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if domain is provided
if [ $# -eq 0 ]; then
    print_error "Please provide your domain name"
    echo "Usage: $0 yourdomain.com"
    exit 1
fi

DOMAIN=$1
print_status "Setting up domain: $DOMAIN"

# Check if domain resolves to this server
print_status "Checking DNS resolution..."
SERVER_IP=$(curl -s http://checkip.amazonaws.com/)
DOMAIN_IP=$(nslookup $DOMAIN | grep -A1 "Name:" | tail -1 | awk '{print $2}' || echo "")

if [ "$DOMAIN_IP" != "$SERVER_IP" ]; then
    print_warning "Domain $DOMAIN does not resolve to this server ($SERVER_IP)"
    print_warning "Current resolution: $DOMAIN_IP"
    print_warning "Please update your DNS records first and wait for propagation"
    
    echo ""
    echo "Add these A records to your DNS:"
    echo "Host: @     Value: $SERVER_IP"
    echo "Host: www   Value: $SERVER_IP"
    echo ""
    
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Setup cancelled"
        exit 1
    fi
fi

# Update Nginx configuration
print_status "Updating Nginx configuration..."
sudo tee /etc/nginx/sites-available/meesho-scanner > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    client_max_body_size 50M;
}
EOF

# Test Nginx configuration
print_status "Testing Nginx configuration..."
if sudo nginx -t; then
    print_success "Nginx configuration is valid"
else
    print_error "Nginx configuration test failed"
    exit 1
fi

# Restart Nginx
print_status "Restarting Nginx..."
sudo systemctl restart nginx
print_success "Nginx restarted successfully"

# Check if Certbot is installed
if ! command -v certbot &> /dev/null; then
    print_status "Installing Certbot..."
    sudo apt update
    sudo apt install certbot python3-certbot-nginx -y
    print_success "Certbot installed"
fi

# Get SSL certificate
print_status "Setting up SSL certificate..."
print_warning "You will need to provide an email address and agree to terms"

if sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN --redirect; then
    print_success "SSL certificate installed successfully!"
else
    print_warning "SSL certificate installation failed. You can try manually:"
    echo "sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"
fi

# Test the setup
print_status "Testing the setup..."

# Test HTTP (should redirect to HTTPS)
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN || echo "000")
HTTPS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN || echo "000")

echo ""
echo "Setup Results:"
echo "=============="
echo "Domain: $DOMAIN"
echo "Server IP: $SERVER_IP"
echo "HTTP Status: $HTTP_STATUS"
echo "HTTPS Status: $HTTPS_STATUS"
echo ""

if [ "$HTTPS_STATUS" = "200" ]; then
    print_success "✅ Domain setup completed successfully!"
    print_success "Your app is now accessible at: https://$DOMAIN"
    print_success "WWW version: https://www.$DOMAIN"
    
    # Show SSL certificate info
    print_status "SSL Certificate Information:"
    sudo certbot certificates | grep -A5 $DOMAIN || echo "Certificate info not available"
    
else
    print_warning "⚠️  Domain setup completed but HTTPS may not be working properly"
    print_warning "Please check the SSL certificate setup manually"
fi

echo ""
print_status "Next steps:"
echo "1. Test your domain: https://$DOMAIN"
echo "2. Update any hardcoded URLs in your application"
echo "3. Remove port 5000 from your EC2 security group"
echo "4. Set up automatic SSL renewal (already configured)"

print_success "Domain setup script completed!"

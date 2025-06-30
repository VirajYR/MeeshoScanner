# Meesho Order Scanner - AWS EC2 Deployment Guide

## Prerequisites
- AWS Account with EC2 access
- Key pair for SSH access
- Basic knowledge of Linux commands

## Step 1: Launch EC2 Instance

### Recommended Instance Configuration:
- **Instance Type**: t3.micro (Free tier) or t3.small for better performance
- **AMI**: Ubuntu Server 22.04 LTS (Free tier eligible)
- **Storage**: 8-10 GB gp3 (general purpose SSD)
- **Security Group**: 
  - SSH (22) - Your IP only
  - HTTP (80) - 0.0.0.0/0
  - HTTPS (443) - 0.0.0.0/0
  - Custom TCP (5000) - 0.0.0.0/0 (for testing)

## Step 2: Connect to EC2 Instance

```bash
# Connect via SSH
ssh -i "your-key.pem" ubuntu@your-ec2-public-ip

# Update system
sudo apt update && sudo apt upgrade -y
```

## Step 3: Install Dependencies

```bash
# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install system dependencies for PyMuPDF
sudo apt install build-essential libffi-dev -y

# Install Nginx (for production)
sudo apt install nginx -y

# Install Git
sudo apt install git -y
```

## Step 4: Clone and Setup Application

```bash
# Clone your repository (replace with your repo URL)
git clone https://github.com/VirajYR/MeeshoScanner.git
cd MeeshoScanner

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Gunicorn for production
pip install gunicorn
```

## Step 5: Configure Application

```bash
# Create uploads directory
mkdir -p uploads

# Set permissions
chmod 755 uploads

# Test the application
python app.py
```

## Step 6: Configure Nginx (Production Setup)

Create Nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/meesho-scanner
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com your-ec2-public-ip;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Handle file uploads
    client_max_body_size 50M;
}
```

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/meesho-scanner /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

## Step 7: Create Systemd Service

```bash
sudo nano /etc/systemd/system/meesho-scanner.service
```

Add this content:
```ini
[Unit]
Description=Meesho Order Scanner
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/MeeshoScanner
Environment=PATH=/home/ubuntu/MeeshoScanner/venv/bin
ExecStart=/home/ubuntu/MeeshoScanner/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start the service
sudo systemctl enable meesho-scanner.service
sudo systemctl start meesho-scanner.service
sudo systemctl status meesho-scanner.service
```

## Step 8: Configure Firewall

```bash
# Configure UFW firewall
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw allow 5000  # For testing
sudo ufw enable
```

## Step 9: SSL Certificate (Optional but Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com
```

## Step 10: Access Your Application

- **Testing**: `http://your-ec2-public-ip:5000`
- **Production**: `http://your-ec2-public-ip` or `https://your-domain.com`

## Benefits of EC2 Deployment:

✅ **No Size Limitations** - Full PDF processing support
✅ **Persistent Storage** - Files remain between sessions  
✅ **Full Control** - Complete server customization
✅ **Scalability** - Easy to upgrade instance size
✅ **Security** - Configurable security groups
✅ **Domain Support** - Use custom domain names
✅ **SSL Support** - HTTPS encryption
✅ **Background Processing** - Long-running tasks supported

## Estimated Costs:

- **t3.micro**: ~$8.5/month (Free tier eligible for 1 year)
- **t3.small**: ~$17/month (better performance)
- **Storage**: ~$1/month for 10GB
- **Data Transfer**: Usually free for normal usage

## Monitoring and Maintenance:

```bash
# Check application status
sudo systemctl status meesho-scanner.service

# View logs
sudo journalctl -u meesho-scanner.service -f

# Restart application
sudo systemctl restart meesho-scanner.service

# Update application
cd /home/ubuntu/MeeshoScanner
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart meesho-scanner.service
```

This setup will give you a robust, production-ready deployment with full PDF processing capabilities!

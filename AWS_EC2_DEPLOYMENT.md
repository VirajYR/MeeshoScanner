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

## Step 11: Domain Setup with Namecheap

### Configure DNS Records

1. **Log into your Namecheap account**
2. **Go to Domain List** and click "Manage" next to your domain
3. **Navigate to Advanced DNS** tab
4. **Add/Edit DNS Records**:

   ```
   Type: A Record
   Host: @
   Value: YOUR-EC2-PUBLIC-IP
   TTL: 5 min (300)
   
   Type: A Record  
   Host: www
   Value: YOUR-EC2-PUBLIC-IP
   TTL: 5 min (300)
   ```

5. **Save changes** (DNS propagation takes 5-30 minutes)

### Update Nginx Configuration

Update your Nginx config to use your domain:

```bash
sudo nano /etc/nginx/sites-available/meesho-scanner
```

Replace the configuration with:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

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
# Test and restart Nginx
sudo nginx -t
sudo systemctl restart nginx
```

### Set up SSL Certificate (HTTPS)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate (replace with your actual domain)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Follow the prompts:
# - Enter email address
# - Agree to terms
# - Choose whether to share email with EFF
# - Select option 2 (Redirect HTTP to HTTPS)
```

### Verify Domain Setup

1. **Check DNS propagation**: Visit [whatsmydns.net](https://whatsmydns.net) and enter your domain
2. **Test HTTP**: `http://yourdomain.com`
3. **Test HTTPS**: `https://yourdomain.com`
4. **Test WWW**: `https://www.yourdomain.com`

### Auto-renewal for SSL

Certbot automatically sets up renewal. To test:
```bash
# Test renewal
sudo certbot renew --dry-run

# Check renewal timer
sudo systemctl status certbot.timer
```

## Step 12: Update Security Group (Important!)

Since you're using a custom domain, update your EC2 security group:

1. **Go to AWS Console** → EC2 → Security Groups
2. **Find your instance's security group**
3. **Edit Inbound Rules**:
   - **Remove** the temporary rule for port 5000 (if you added it)
   - **Keep** HTTP (80) and HTTPS (443) open to 0.0.0.0/0
   - **Keep** SSH (22) restricted to your IP

## Final URLs

After setup, your app will be accessible at:
- **Main site**: `https://yourdomain.com`
- **With www**: `https://www.yourdomain.com`
- **HTTP redirects**: `http://yourdomain.com` → `https://yourdomain.com`

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

## Troubleshooting Common Issues

### Issue 1: Service Failed to Start (Exit Code 1)

If you see `(code=exited, status=1/FAILURE)`, follow these steps:

```bash
# 1. Create logs directory (required by gunicorn.conf.py)
mkdir -p /home/ubuntu/MeeshoScanner/logs

# 2. Check detailed logs
sudo journalctl -u meesho-scanner.service -n 50

# 3. Test Gunicorn manually first
cd /home/ubuntu/MeeshoScanner
source venv/bin/activate
gunicorn --config gunicorn.conf.py app:app

# 4. If Gunicorn config fails, try simple command
gunicorn --workers 3 --bind 127.0.0.1:5000 app:app
```

### Issue 2: Import Errors

```bash
# Test if app can be imported
cd /home/ubuntu/MeeshoScanner
source venv/bin/activate
python -c "import app; print('App imported successfully')"
```

### Issue 3: Missing Dependencies

```bash
# Reinstall all dependencies
cd /home/ubuntu/MeeshoScanner
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### Issue 4: Alternative Service Configuration

If the config file approach fails, use this simpler systemd service:

```bash
sudo nano /etc/systemd/system/meesho-scanner.service
```

Replace with:
```ini
[Unit]
Description=Meesho Order Scanner
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/MeeshoScanner
Environment=PATH=/home/ubuntu/MeeshoScanner/venv/bin
ExecStart=/home/ubuntu/MeeshoScanner/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 --access-logfile /home/ubuntu/MeeshoScanner/logs/access.log --error-logfile /home/ubuntu/MeeshoScanner/logs/error.log app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl restart meesho-scanner.service
sudo systemctl status meesho-scanner.service
```

## Quick Fix Commands

Run these commands on your EC2 instance to fix the current issue:

```bash
# Navigate to app directory
cd /home/ubuntu/MeeshoScanner

# Create logs directory
mkdir -p logs

# Test the app manually first
source venv/bin/activate
python app.py &
# Press Ctrl+C to stop after confirming it works

# If app works, test Gunicorn without config
gunicorn --workers 2 --bind 127.0.0.1:5000 app:app &
# Press Ctrl+C to stop after confirming it works

# Update systemd service to simpler version
sudo tee /etc/systemd/system/meesho-scanner.service > /dev/null <<EOF
[Unit]
Description=Meesho Order Scanner
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/MeeshoScanner
Environment=PATH=/home/ubuntu/MeeshoScanner/venv/bin
ExecStart=/home/ubuntu/MeeshoScanner/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:5000 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Reload and restart service
sudo systemctl daemon-reload
sudo systemctl restart meesho-scanner.service
sudo systemctl status meesho-scanner.service
```

This setup will give you a robust, production-ready deployment with full PDF processing capabilities!

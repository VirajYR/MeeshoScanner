# 🚀 Quick AWS EC2 Deployment Guide

## Before You Start
1. **Launch EC2 Instance** with Ubuntu 22.04 LTS
2. **Security Group** should allow:
   - SSH (22) from your IP
   - HTTP (80) from anywhere (0.0.0.0/0)
   - HTTPS (443) from anywhere (0.0.0.0/0)
3. **Download** your key pair (.pem file)

## One-Command Deployment

### Step 1: Connect to EC2
```bash
# Replace with your actual key file and IP
ssh -i "your-key.pem" ubuntu@your-ec2-ip
```

### Step 2: Run Deployment Script
```bash
# Download and run the deployment script
curl -sSL https://raw.githubusercontent.com/VirajYR/MeeshoScanner/main/deploy-ec2.sh | bash
```

Or manually:
```bash
# Clone repository
git clone https://github.com/VirajYR/MeeshoScanner.git
cd MeeshoScanner

# Make script executable
chmod +x deploy-ec2.sh

# Run deployment
./deploy-ec2.sh
```

### Step 3: Access Your App
- Open browser: `http://your-ec2-public-ip`
- Your Meesho Order Scanner is ready! 🎉

## Benefits of EC2 vs Vercel:

| Feature | EC2 | Vercel |
|---------|-----|--------|
| **PDF Processing** | ✅ Full support | ❌ Size limitations |
| **File Storage** | ✅ Persistent | ❌ Temporary |
| **Processing Time** | ✅ Unlimited | ❌ 10s timeout |
| **Dependencies** | ✅ Any size | ❌ 250MB limit |
| **Custom Domain** | ✅ Easy setup | ✅ Supported |
| **Cost (small app)** | ~$10/month | Free/Paid |
| **Scalability** | ✅ Full control | ✅ Automatic |
| **Maintenance** | Manual | Automatic |

## Cost Estimate:
- **t3.micro**: ~$8.50/month (Free tier for 1 year)
- **t3.small**: ~$17/month (recommended for production)
- **Storage**: ~$1/month
- **Total**: ~$9-18/month

## Quick Commands:

### Check Status
```bash
sudo systemctl status meesho-scanner.service
```

### View Logs
```bash
sudo journalctl -u meesho-scanner.service -f
```

### Restart App
```bash
sudo systemctl restart meesho-scanner.service
```

### Update App
```bash
cd /home/ubuntu/MeeshoScanner
./update-app.sh
```

## Troubleshooting:

### App Not Starting?
```bash
# Check logs
sudo journalctl -u meesho-scanner.service --no-pager -n 50

# Check if port is in use
sudo netstat -tlnp | grep :5000

# Restart services
sudo systemctl restart meesho-scanner.service nginx
```

### Can't Access from Browser?
1. Check Security Group allows HTTP (80)
2. Check if services are running
3. Try direct port: `http://your-ip:5000`

### SSL Certificate (Optional):
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

Your Meesho Order Scanner will have **full PDF processing capabilities** on EC2! 🚀

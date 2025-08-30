# 🚀 EC2 Deployment Commands

## Connect to EC2
```bash
ssh -i your-key.pem ubuntu@13.203.91.181
```

## Update Application (Run these commands on EC2)
```bash
# Navigate to app directory
cd /home/ubuntu/MeeshoScanner

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Update dependencies (if needed)
pip install --upgrade -r requirements.txt

# Restart the application service
sudo systemctl restart meesho-scanner.service

# Restart Nginx
sudo systemctl restart nginx

# Check if services are running
sudo systemctl status meesho-scanner.service
sudo systemctl status nginx

# View recent logs if needed
sudo journalctl -u meesho-scanner.service --no-pager -n 20
```

## Quick Health Check
```bash
# Test if the app is responding
curl http://localhost:5000/test

# Check if the domain is working
curl -I https://divinedelight.me
```

## If you encounter any issues:
```bash
# Check application logs
sudo journalctl -u meesho-scanner.service -f

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log

# Restart services if needed
sudo systemctl restart meesho-scanner.service nginx
```

# Quick Domain Setup Guide for Meesho Scanner

## Prerequisites
- Namecheap domain purchased
- EC2 instance running
- Nginx and app already configured

## Step 1: Configure Namecheap DNS (5 minutes)

1. **Login to Namecheap** → Domain List → Manage your domain
2. **Go to Advanced DNS** tab
3. **Delete existing A records** (if any)
4. **Add these records**:

```
Type: A Record
Host: @
Value: YOUR-EC2-PUBLIC-IP
TTL: 5 min

Type: A Record  
Host: www
Value: YOUR-EC2-PUBLIC-IP
TTL: 5 min
```

5. **Save changes**

## Step 2: Update Nginx Configuration (2 minutes)

SSH into your EC2 instance and run:

```bash
# Replace yourdomain.com with your actual domain
sudo tee /etc/nginx/sites-available/meesho-scanner > /dev/null <<EOF
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

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

# Test and restart Nginx
sudo nginx -t
sudo systemctl restart nginx
```

## Step 3: Wait for DNS Propagation (5-30 minutes)

Check if DNS is working:
```bash
# Replace with your domain
nslookup yourdomain.com
```

Or visit: https://whatsmydns.net and enter your domain

## Step 4: Set up SSL Certificate (3 minutes)

Once DNS is working:

```bash
# Install Certbot (if not already installed)
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate - replace with your domain
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Follow the prompts:
- Enter email address
- Agree to terms of service
- Choose whether to share email (optional)
- **Select option 2** (Redirect HTTP to HTTPS)

## Step 5: Test Your Domain

Your app should now be accessible at:
- ✅ `https://yourdomain.com`
- ✅ `https://www.yourdomain.com`
- ✅ `http://yourdomain.com` (redirects to HTTPS)

## Troubleshooting

### DNS Not Working?
- Wait longer (up to 24 hours max)
- Check DNS records are correct
- Try different DNS checker tools

### SSL Certificate Failed?
- Make sure DNS is working first
- Check domain spelling
- Ensure ports 80 and 443 are open in security group

### Nginx Errors?
```bash
# Check Nginx status
sudo systemctl status nginx

# Check error logs
sudo tail -f /var/log/nginx/error.log
```

## Security Group Update

**Important**: Remove port 5000 from your security group rules after domain setup is complete.

Keep only:
- SSH (22) - Your IP only
- HTTP (80) - 0.0.0.0/0
- HTTPS (443) - 0.0.0.0/0

## Commands Reference

```bash
# Check certificate status
sudo certbot certificates

# Renew certificates manually
sudo certbot renew

# Check Nginx config
sudo nginx -t

# Restart services
sudo systemctl restart nginx
sudo systemctl restart meesho-scanner
```

## What's Next?

After domain setup, your Meesho Scanner will have:
- 🔒 **HTTPS encryption**
- 🌐 **Professional domain**
- 📱 **Mobile-friendly URLs**
- 🔄 **Automatic SSL renewal**
- ⚡ **Better performance**

Your users can now access your scanner at: **https://yourdomain.com**

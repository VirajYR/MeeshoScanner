# Meesho Order Scanner

A Flask-based web application for scanning and managing order manifests with barcode/QR code functionality.

## Features

- 📱 **QR/Barcode Scanner** - Continuous scanning without page reloads
- 📄 **PDF Processing** - Extract order data from PDF manifests
- 📊 **Real-time Dashboard** - Live statistics and order tracking
- 🎨 **Modern UI** - Beautiful, responsive design
- 📱 **Mobile Friendly** - Works perfectly on phones and tablets

## Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python app.py
   ```
4. Open http://localhost:5000

## Deployment Options

### Option 1: Vercel (Recommended)

1. Install Vercel CLI:
   ```bash
   npm i -g vercel
   ```

2. Deploy:
   ```bash
   vercel --prod
   ```

### Option 2: Heroku

1. Install Heroku CLI
2. Login and create app:
   ```bash
   heroku login
   heroku create your-app-name
   ```

3. Deploy:
   ```bash
   git push heroku main
   ```

### Option 3: Railway

1. Connect your GitHub repository to Railway
2. Deploy automatically from the dashboard

## Important Notes for Deployment

- **File Storage**: In serverless environments, uploaded files are temporary
- **Camera Access**: HTTPS is required for camera functionality in production
- **Environment Variables**: Set `FLASK_ENV=production` for production deployments

## Usage

1. Upload your manifest PDF file
2. Click "Start Barcode Scanner"
3. Scan QR codes/barcodes continuously
4. Monitor real-time statistics
5. Export results as CSV

## Technologies Used

- **Backend**: Flask, pandas, PyMuPDF
- **Frontend**: HTML5, CSS3, JavaScript
- **Scanner**: html5-qrcode
- **UI**: Font Awesome, DataTables

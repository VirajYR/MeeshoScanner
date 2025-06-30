from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import os
import csv
import json
from datetime import datetime
import pdfplumber  # Lighter alternative to PyMuPDF
from flask_cors import CORS
import re
import logging
import tempfile

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use temporary directory for uploads in serverless environments
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DATA_FILE = os.path.join(UPLOAD_FOLDER, 'orders.csv')

def read_csv_as_dict(file_path):
    """Read CSV file and return as list of dictionaries"""
    if not os.path.exists(file_path):
        return []
    
    with open(file_path, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        return list(reader)

def write_csv_from_dict(file_path, data, fieldnames):
    """Write list of dictionaries to CSV file"""
    with open(file_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def get_order_stats(orders):
    """Calculate order statistics"""
    total = len(orders)
    packed = len([o for o in orders if o.get('Status') == 'Packed'])
    in_transit = len([o for o in orders if o.get('Status') == 'In Transit'])
    delivered = len([o for o in orders if o.get('Status') == 'Delivered'])
    return {
        'total': total,
        'packed': packed,
        'in_transit': in_transit,
        'delivered': delivered
    }

@app.route('/')
def index():
    if not os.path.exists(DATA_FILE):
        return render_template('index.html', message="Please upload your manifest PDF file.")
    
    orders = read_csv_as_dict(DATA_FILE)
    packed_orders = [o for o in orders if o.get('Status') == 'Packed']
    
    return render_template('index.html', 
                         message=f"Ready to scan! {len(packed_orders)} orders pending.",
                         total_orders=len(orders))

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and (file.filename.endswith('.pdf') or file.filename.endswith('.csv')):
            # Save uploaded file temporarily
            temp_path = os.path.join(UPLOAD_FOLDER, 'temp_' + file.filename)
            file.save(temp_path)
            
            if file.filename.endswith('.pdf'):
                orders = extract_orders_from_pdf(temp_path)
            else:
                orders = read_csv_as_dict(temp_path)
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            if orders:
                # Ensure required columns exist
                fieldnames = ['Order ID', 'Product', 'Quantity', 'Customer', 'Address', 'Status', 'Tracking Number']
                for order in orders:
                    for field in fieldnames:
                        if field not in order:
                            order[field] = ''
                    if not order.get('Status'):
                        order['Status'] = 'Packed'
                
                write_csv_from_dict(DATA_FILE, orders, fieldnames)
                return jsonify({'success': True, 'message': f'Successfully processed {len(orders)} orders'})
            else:
                return jsonify({'error': 'No orders found in the file'}), 400
        else:
            return jsonify({'error': 'Invalid file type. Please upload PDF or CSV files only.'}), 400
    
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

def extract_orders_from_pdf(pdf_path):
    """Extract order information from PDF using pdfplumber"""
    orders = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                all_text += page.extract_text() or ""
        
        # Simple regex patterns for extracting order information
        order_patterns = [
            r'Order[:\s]*([A-Z0-9-]+)',
            r'AWB[:\s]*([A-Z0-9-]+)',
            r'Tracking[:\s]*([A-Z0-9-]+)'
        ]
        
        lines = all_text.split('\n')
        current_order = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for order IDs
            for pattern in order_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    if current_order:
                        orders.append(current_order)
                    current_order = {
                        'Order ID': match.group(1),
                        'Product': '',
                        'Quantity': '1',
                        'Customer': '',
                        'Address': '',
                        'Status': 'Packed',
                        'Tracking Number': match.group(1)
                    }
                    break
            
            # Extract product information (simple heuristics)
            if current_order and ('product' in line.lower() or 'item' in line.lower()):
                current_order['Product'] = line[:50]  # Limit length
            
            # Extract customer information
            if current_order and any(word in line.lower() for word in ['customer', 'name', 'buyer']):
                current_order['Customer'] = line[:50]
            
            # Extract address information
            if current_order and any(word in line.lower() for word in ['address', 'delivery', 'ship']):
                current_order['Address'] = line[:100]
        
        # Add the last order
        if current_order:
            orders.append(current_order)
    
    except Exception as e:
        logger.error(f"PDF extraction error: {str(e)}")
    
    return orders

@app.route('/dashboard')
def dashboard():
    orders = read_csv_as_dict(DATA_FILE)
    stats = get_order_stats(orders)
    return render_template('dashboard.html', stats=stats)

@app.route('/api/scan', methods=['POST'])
def scan_barcode():
    try:
        data = request.get_json()
        barcode = data.get('barcode', '').strip()
        
        if not barcode:
            return jsonify({'error': 'No barcode provided'}), 400
        
        orders = read_csv_as_dict(DATA_FILE)
        found = False
        
        for order in orders:
            if (order.get('Order ID', '').strip() == barcode or 
                order.get('Tracking Number', '').strip() == barcode):
                
                if order.get('Status') == 'Packed':
                    order['Status'] = 'In Transit'
                    order['Scanned At'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    found = True
                    break
                else:
                    return jsonify({
                        'error': f'Order {barcode} is already {order.get("Status", "processed")}'
                    }), 400
        
        if found:
            fieldnames = list(orders[0].keys()) if orders else []
            if 'Scanned At' not in fieldnames:
                fieldnames.append('Scanned At')
            
            write_csv_from_dict(DATA_FILE, orders, fieldnames)
            
            stats = get_order_stats(orders)
            return jsonify({
                'success': True,
                'message': f'Order {barcode} marked as In Transit',
                'stats': stats
            })
        else:
            return jsonify({'error': f'Order {barcode} not found'}), 404
    
    except Exception as e:
        logger.error(f"Scan error: {str(e)}")
        return jsonify({'error': f'Scan failed: {str(e)}'}), 500

@app.route('/api/stats')
def get_stats():
    try:
        orders = read_csv_as_dict(DATA_FILE)
        stats = get_order_stats(orders)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders')
def get_orders():
    try:
        orders = read_csv_as_dict(DATA_FILE)
        return jsonify(orders)
    except Exception as e:
        logger.error(f"Orders API error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download')
def download_csv():
    try:
        if os.path.exists(DATA_FILE):
            return send_file(DATA_FILE, as_attachment=True, download_name='updated_orders.csv')
        else:
            return jsonify({'error': 'No data file found'}), 404
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset_data():
    try:
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
        return jsonify({'success': True, 'message': 'Data reset successfully'})
    except Exception as e:
        logger.error(f"Reset error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)

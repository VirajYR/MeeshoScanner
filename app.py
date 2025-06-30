from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import os
import csv
import json
from datetime import datetime
from flask_cors import CORS
import re
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use /tmp directory for serverless environments (read-write accessible)
import tempfile
UPLOAD_FOLDER = '/tmp'  # Vercel allows writing to /tmp
DATA_FILE = os.path.join(UPLOAD_FOLDER, 'orders.csv')

# In-memory storage for serverless environments
_orders_data = []

def read_csv_as_dict(file_path=None):
    """Read CSV file and return as list of dictionaries"""
    global _orders_data
    
    # Try to read from file first, fallback to in-memory data
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                _orders_data = list(reader)
                return _orders_data
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
    
    # Return in-memory data or empty list
    return _orders_data

def write_csv_from_dict(file_path, data, fieldnames):
    """Write list of dictionaries to CSV file and update in-memory storage"""
    global _orders_data
    
    # Always update in-memory storage
    _orders_data = data
    
    # Try to write to file (may fail in serverless, but that's ok)
    try:
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    except Exception as e:
        logger.warning(f"Could not write to file (using in-memory storage): {e}")

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

def create_sample_data():
    """Create sample order data for testing"""
    sample_orders = [
        {
            'Order ID': 'MSO001',
            'Product': 'Samsung Galaxy Case',
            'Quantity': '1',
            'Customer': 'John Doe',
            'Address': '123 Main St, Mumbai',
            'Status': 'Packed',
            'Tracking Number': 'TRK001'
        },
        {
            'Order ID': 'MSO002',
            'Product': 'iPhone Charger',
            'Quantity': '2',
            'Customer': 'Jane Smith',
            'Address': '456 Park Ave, Delhi',
            'Status': 'Packed',
            'Tracking Number': 'TRK002'
        },
        {
            'Order ID': 'MSO003',
            'Product': 'Bluetooth Headphones',
            'Quantity': '1',
            'Customer': 'Mike Johnson',
            'Address': '789 Oak St, Bangalore',
            'Status': 'In Transit',
            'Tracking Number': 'TRK003'
        }
    ]
    
    fieldnames = ['Order ID', 'Product', 'Quantity', 'Customer', 'Address', 'Status', 'Tracking Number']
    write_csv_from_dict(DATA_FILE, sample_orders, fieldnames)
    return sample_orders

@app.route('/')
def index():
    orders = read_csv_as_dict()
    
    # Create sample data if no orders exist
    if not orders:
        orders = create_sample_data()
        return render_template('index.html', 
                             message="Demo data loaded! Upload your CSV file to replace it.",
                             total_orders=len(orders))
    
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
        
        if file and file.filename.endswith('.csv'):
            # Create temporary file in /tmp directory
            temp_path = os.path.join('/tmp', 'temp_' + file.filename)
            file.save(temp_path)
            
            orders = read_csv_as_dict(temp_path)
            
            # Clean up temp file
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as e:
                logger.warning(f"Could not remove temp file: {e}")
            
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
            return jsonify({'error': 'Invalid file type. Please upload CSV files only. PDF support temporarily disabled for deployment.'}), 400
    
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/dashboard')
def dashboard():
    orders = read_csv_as_dict()
    stats = get_order_stats(orders)
    return render_template('dashboard.html', stats=stats)

@app.route('/api/scan', methods=['POST'])
def scan_barcode():
    try:
        data = request.get_json()
        barcode = data.get('barcode', '').strip()
        
        if not barcode:
            return jsonify({'error': 'No barcode provided'}), 400
        
        orders = read_csv_as_dict()
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
        orders = read_csv_as_dict()
        stats = get_order_stats(orders)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders')
def get_orders():
    try:
        orders = read_csv_as_dict()
        return jsonify(orders)
    except Exception as e:
        logger.error(f"Orders API error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download')
def download_csv():
    try:
        orders = read_csv_as_dict()
        if orders:
            # Create temporary CSV file for download
            import io
            output = io.StringIO()
            fieldnames = list(orders[0].keys()) if orders else []
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(orders)
            
            # Create downloadable response
            from flask import Response
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={"Content-disposition": "attachment; filename=updated_orders.csv"}
            )
        else:
            return jsonify({'error': 'No data available'}), 404
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset_data():
    try:
        global _orders_data
        _orders_data = []  # Clear in-memory data
        # Try to remove file if it exists (may fail in serverless, but that's ok)
        try:
            if os.path.exists(DATA_FILE):
                os.remove(DATA_FILE)
        except Exception as e:
            logger.warning(f"Could not remove file: {e}")
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

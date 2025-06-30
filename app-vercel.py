from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import pandas as pd
import os
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

@app.route('/')
def index():
    if not os.path.exists(DATA_FILE):
        return render_template('index.html', message="Please upload your manifest PDF file.")
    df = pd.read_csv(DATA_FILE)
    packed = df[df['Status'] == 'Packed']
    pending = df[df['Status'] == 'Pending']
    cancelled = df[df['Status'] == 'Cancelled']
    return render_template('dashboard.html', packed=len(packed), pending=len(pending), cancelled=len(cancelled), table=df.to_dict(orient='records'))

@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'file' not in request.files:
            return render_template('index.html', message="No file selected. Please choose a file to upload.")
        
        file = request.files['file']
        if file.filename == '':
            return render_template('index.html', message="No file selected. Please choose a file to upload.")

        filename = file.filename.lower()
        logger.info(f"Processing file: {filename}")
        
        # Remove existing data file
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)

        try:
            if filename.endswith('.pdf'):
                logger.info("Processing PDF file...")
                pdf_text = extract_text_from_pdf_pdfplumber(file)
                df = parse_pdf_to_dataframe(pdf_text)
                logger.info(f"Extracted {len(df)} orders from PDF")
            elif filename.endswith('.csv'):
                logger.info("Processing CSV file...")
                df = pd.read_csv(file)
                # Ensure required columns exist
                required_columns = ['Order ID', 'AWB ID', 'Courier', 'SKU', 'Qty']
                for col in required_columns:
                    if col not in df.columns:
                        df[col] = 'Unknown'
                logger.info(f"Loaded {len(df)} orders from CSV")
            else:
                return render_template('index.html', message="Unsupported file format. Please upload a PDF or CSV file.")

            if df.empty:
                return render_template('index.html', message="No valid data found in the uploaded file. Please check the file format and content.")

            # Initialize status columns
            df['Status'] = 'Pending'
            df['Scanned Time'] = ''
            
            # Ensure correct data types
            df['Status'] = df['Status'].astype(str)
            df['Scanned Time'] = df['Scanned Time'].astype(str)
            df['AWB ID'] = df['AWB ID'].astype(str)
            df['Order ID'] = df['Order ID'].astype(str)
            
            # Clean and validate data
            df = df.dropna(subset=['AWB ID'])  # Remove rows without AWB ID
            df['AWB ID'] = df['AWB ID'].astype(str).str.strip()  # Clean AWB IDs
            df = df[df['AWB ID'] != '']  # Remove empty AWB IDs
            
            if df.empty:
                return render_template('index.html', message="No valid AWB IDs found in the uploaded file.")
            
            df.to_csv(DATA_FILE, index=False)
            logger.info(f"Successfully saved {len(df)} orders to {DATA_FILE}")
            
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            return render_template('index.html', message=f"Error processing file: {str(e)}. Please ensure the file is not corrupted and contains valid data.")

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return render_template('index.html', message=f"Upload failed: {str(e)}")

    return redirect(url_for('index'))

def extract_text_from_pdf_pdfplumber(file):
    """Extract text from PDF file using pdfplumber (lighter alternative)"""
    try:
        text = ""
        file.seek(0)  # Reset file pointer
        
        with pdfplumber.open(file) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    logger.info(f"Extracted text from page {page_num + 1}")
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num + 1}: {str(e)}")
                    continue
        
        logger.info(f"Successfully extracted {len(text)} characters from PDF")
        return text
    except Exception as e:
        logger.error(f"Error opening PDF: {str(e)}")
        raise Exception(f"Could not read PDF file: {str(e)}")

def parse_pdf_to_dataframe(text):
    """Parse PDF text to DataFrame with improved pattern matching"""
    rows = []
    lines = text.splitlines()
    
    # Improved patterns for different courier services
    awb_patterns = {
        'Valmo': r'VL\d+',
        'Xpress Bees': r'134\d+',
        'Delhivery': r'1490\d+',
        'Generic': r'[A-Z]{2,3}\d{8,}'
    }
    
    order_patterns = [
        r'16\d{10,}',  # 16 followed by digits
        r'17\d{10,}',  # 17 followed by digits
        r'\d{12,15}'   # 12-15 digit numbers
    ]
    
    sku_keywords = {
        'Together': ['Together'],
        'Divine Aura': ['Divine Aura', 'Aura'],
        'Mystic Aura': ['Mystic Aura'],
        'Vibrant': ['Vibrant']
    }
    
    logger.info(f"Processing {len(lines)} lines from PDF")
    
    for line_num, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        try:
            # Find AWB ID
            awb = None
            courier = "Unknown"
            
            for courier_name, pattern in awb_patterns.items():
                matches = re.findall(pattern, line, re.IGNORECASE)
                if matches:
                    awb = matches[0]
                    courier = courier_name
                    break
            
            if not awb:
                continue
            
            # Find Order ID
            order = None
            for pattern in order_patterns:
                matches = re.findall(pattern, line)
                if matches:
                    order = matches[0]
                    break
            
            if not order:
                order = "Unknown"
            
            # Determine SKU
            sku = "Unknown"
            for sku_name, keywords in sku_keywords.items():
                if any(keyword.lower() in line.lower() for keyword in keywords):
                    sku = sku_name
                    break
            
            rows.append([order, awb, courier, sku, 1])
            logger.debug(f"Line {line_num + 1}: Found order {order}, AWB {awb}, courier {courier}, SKU {sku}")
            
        except Exception as e:
            logger.warning(f"Error processing line {line_num + 1}: {str(e)}")
            continue
    
    df = pd.DataFrame(rows, columns=['Order ID', 'AWB ID', 'Courier', 'SKU', 'Qty'])
    logger.info(f"Successfully parsed {len(df)} orders from PDF")
    
    return df

@app.route('/scan', methods=['POST'])
def scan():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data received'})
        
        awb_id = data.get('awb_id', '').strip()
        if not awb_id:
            return jsonify({'success': False, 'message': 'No AWB ID provided'})

        logger.info(f"Scanning AWB ID: {awb_id}")
        
        if not os.path.exists(DATA_FILE):
            return jsonify({'success': False, 'message': 'No manifest data found. Please upload a file first.'})

        df = pd.read_csv(DATA_FILE)
        
        # Clean AWB ID for comparison
        awb_id_clean = str(awb_id).strip()
        df['AWB ID'] = df['AWB ID'].astype(str).str.strip()
        
        match = df['AWB ID'] == awb_id_clean

        if match.any():
            current_status = df.loc[match, 'Status'].values[0]
            logger.info(f"AWB {awb_id} found with status: {current_status}")
            
            if current_status == 'Packed':
                return jsonify({'success': False, 'message': 'Already Packed', 'status': 'Packed'})
            elif current_status == 'Cancelled':
                return jsonify({'success': False, 'message': 'This item was previously cancelled.', 'status': 'Cancelled'})
            else:
                # Mark as packed
                df.loc[match, 'Status'] = 'Packed'
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                df.loc[match, 'Scanned Time'] = current_time
                df.to_csv(DATA_FILE, index=False)
                logger.info(f"AWB {awb_id} marked as Packed")
                return jsonify({'success': True, 'status': 'Packed'})
        else:
            # AWB not found in manifest - add as cancelled
            logger.info(f"AWB {awb_id} not found in manifest, adding as cancelled")
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            new_row = pd.DataFrame([[
                "Unknown", 
                awb_id_clean, 
                "Unknown", 
                "Unknown", 
                1, 
                "Cancelled", 
                current_time
            ]], columns=['Order ID', 'AWB ID', 'Courier', 'SKU', 'Qty', 'Status', 'Scanned Time'])
            
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            return jsonify({'success': True, 'status': 'Cancelled', 'confirm': True})
            
    except Exception as e:
        logger.error(f"Error in scan endpoint: {str(e)}")
        return jsonify({'success': False, 'message': f'Error processing scan: {str(e)}'})

@app.route('/delete', methods=['POST'])
def delete_entry():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data received'})
        
        awb_id = data.get('awb_id', '').strip()
        if not awb_id:
            return jsonify({'success': False, 'message': 'No AWB ID provided'})

        logger.info(f"Deleting AWB ID: {awb_id}")
        
        if not os.path.exists(DATA_FILE):
            return jsonify({'success': False, 'message': 'No data file found'})

        df = pd.read_csv(DATA_FILE)
        initial_count = len(df)
        
        # Clean AWB ID for comparison
        awb_id_clean = str(awb_id).strip()
        df['AWB ID'] = df['AWB ID'].astype(str).str.strip()
        
        df = df[df['AWB ID'] != awb_id_clean]
        final_count = len(df)
        
        if initial_count == final_count:
            return jsonify({'success': False, 'message': f'AWB ID {awb_id} not found'})
        
        df.to_csv(DATA_FILE, index=False)
        logger.info(f"AWB {awb_id} deleted successfully")
        return jsonify({'success': True, 'message': f'AWB ID {awb_id} deleted successfully.'})
        
    except Exception as e:
        logger.error(f"Error in delete endpoint: {str(e)}")
        return jsonify({'success': False, 'message': f'Error deleting entry: {str(e)}'})

@app.route('/export')
def export():
    try:
        if not os.path.exists(DATA_FILE):
            return redirect(url_for('index'))
        
        return send_file(DATA_FILE, as_attachment=True, download_name='orders_export.csv')
    except Exception as e:
        logger.error(f"Error in export: {str(e)}")
        return redirect(url_for('index'))

@app.route('/test', methods=['GET'])
def test():
    """Test endpoint to check if server is working"""
    return jsonify({'status': 'OK', 'message': 'Server is working correctly'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)

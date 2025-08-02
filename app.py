import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import pandas as pd
from datetime import datetime
import fitz  # PyMuPDF
from flask_cors import CORS
import re
import logging
from logging.handlers import RotatingFileHandler

# Import configuration
try:
    from config import config
except ImportError:
    config = None

app = Flask(__name__)
CORS(app)

# Configure based on environment
if config:
    env = os.environ.get('FLASK_ENV', 'production')
    app.config.from_object(config.get(env, config['default']))
else:
    # Fallback configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret-key')
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Configure logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240000, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Meesho Order Scanner startup')

# Original logging setup for compatibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = 'uploads'
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
            # Check if this is a dashboard upload
            if os.path.exists(DATA_FILE):
                df = pd.read_csv(DATA_FILE)
                return render_template('dashboard.html', 
                                       packed=len(df[df['Status'] == 'Packed']),
                                       pending=len(df[df['Status'] == 'Pending']),
                                       cancelled=len(df[df['Status'] == 'Cancelled']),
                                       table=df.to_dict(orient='records'),
                                       message="No file selected. Please choose a file to upload.")
            else:
                return render_template('index.html', message="No file selected. Please choose a file to upload.")
        
        file = request.files['file']
        if file.filename == '':
            # Check if this is a dashboard upload
            if os.path.exists(DATA_FILE):
                df = pd.read_csv(DATA_FILE)
                return render_template('dashboard.html', 
                                       packed=len(df[df['Status'] == 'Packed']),
                                       pending=len(df[df['Status'] == 'Pending']),
                                       cancelled=len(df[df['Status'] == 'Cancelled']),
                                       table=df.to_dict(orient='records'),
                                       message="No file selected. Please choose a file to upload.")
            else:
                return render_template('index.html', message="No file selected. Please choose a file to upload.")

        filename = file.filename.lower()
        logger.info(f"Processing file: {filename}")
        
        # Check if we're replacing existing data
        is_replacement = os.path.exists(DATA_FILE)
        
        # Remove existing data file to prevent conflicts
        if os.path.exists(DATA_FILE):
            try:
                os.remove(DATA_FILE)
                logger.info("Previous data file removed successfully")
            except Exception as e:
                logger.error(f"Error removing previous data file: {str(e)}")

        try:
            if filename.endswith('.pdf'):
                logger.info("Processing PDF manifest file...")
                pdf_text = extract_text_from_pdf(file)
                df = parse_pdf_to_dataframe(pdf_text)
                logger.info(f"Extracted {len(df)} orders from PDF manifest")
                
                # Log extraction summary
                if not df.empty:
                    unique_couriers = df['Courier'].unique()
                    logger.info(f"Found couriers: {', '.join(unique_couriers)}")
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
                error_msg = "Unsupported file format. Please upload a PDF manifest or CSV file."
                if is_replacement:
                    df = pd.DataFrame()  # Empty dataframe for dashboard
                    return render_template('dashboard.html', 
                                           packed=0, pending=0, cancelled=0,
                                           table=[], message=error_msg)
                else:
                    return render_template('index.html', message=error_msg)

            if df.empty:
                error_msg = "No valid data found in the uploaded file. Please check the file format and content."
                if is_replacement:
                    return render_template('dashboard.html', 
                                           packed=0, pending=0, cancelled=0,
                                           table=[], message=error_msg)
                else:
                    return render_template('index.html', message=error_msg)

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
                error_msg = "No valid AWB IDs found in the uploaded file."
                if is_replacement:
                    return render_template('dashboard.html', 
                                           packed=0, pending=0, cancelled=0,
                                           table=[], message=error_msg)
                else:
                    return render_template('index.html', message=error_msg)
            
            df.to_csv(DATA_FILE, index=False)
            logger.info(f"Successfully saved {len(df)} orders to {DATA_FILE}")
            
            # Prepare success message
            action_word = "replaced" if is_replacement else "uploaded"
            success_msg = f"Successfully {action_word} {filename} with {len(df)} orders!"
            
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            error_msg = f"Error processing file: {str(e)}. Please ensure the file is not corrupted and contains valid data."
            if is_replacement:
                return render_template('dashboard.html', 
                                       packed=0, pending=0, cancelled=0,
                                       table=[], message=error_msg)
            else:
                return render_template('index.html', message=error_msg)

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        error_msg = f"Upload failed: {str(e)}"
        # Try to determine if we should show dashboard or index
        if os.path.exists(DATA_FILE):
            try:
                df = pd.read_csv(DATA_FILE)
                return render_template('dashboard.html', 
                                       packed=len(df[df['Status'] == 'Packed']),
                                       pending=len(df[df['Status'] == 'Pending']),
                                       cancelled=len(df[df['Status'] == 'Cancelled']),
                                       table=df.to_dict(orient='records'),
                                       message=error_msg)
            except:
                return render_template('index.html', message=error_msg)
        else:
            return render_template('index.html', message=error_msg)

    return redirect(url_for('index'))

def extract_text_from_pdf(file):
    """Extract text from PDF file with improved error handling"""
    try:
        text = ""
        file_content = file.read()
        doc = fitz.open(stream=file_content, filetype="pdf")
        
        for page_num, page in enumerate(doc):
            try:
                page_text = page.get_text()
                text += page_text + "\n"
                logger.info(f"Extracted text from page {page_num + 1}")
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num + 1}: {str(e)}")
                continue
        
        doc.close()
        logger.info(f"Successfully extracted {len(text)} characters from PDF")
        return text
    except Exception as e:
        logger.error(f"Error opening PDF: {str(e)}")
        raise Exception(f"Could not read PDF file: {str(e)}")

def parse_pdf_to_dataframe(text):
    """Parse PDF text to DataFrame with improved manifest parsing"""
    lines = text.split('\n')
    entries = []
    courier = None

    logger.info(f"Processing {len(lines)} lines from PDF manifest")
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect courier
        if line.startswith("Courier :"):
            courier = line.replace("Courier :", "").strip()
            logger.info(f"Found courier: {courier}")

        # Match Order ID (11 digits)
        match_order = re.match(r'^\d{11}$', line)
        if match_order:
            order_id = line
            
            try:
                # Check if we have enough lines ahead
                if i + 5 >= len(lines):
                    logger.warning(f"Not enough lines after order ID {order_id}")
                    i += 1
                    continue
                
                # Get AWB ID (2 lines after order ID)
                awb_candidate = lines[i + 2].strip() if i + 2 < len(lines) else ""
                
                # Get SKU (3 lines after order ID)
                sku_candidate = lines[i + 3].strip() if i + 3 < len(lines) else ""

                # Handle multi-line SKUs
                if ("Combo" in sku_candidate or "pcs" in sku_candidate) and i + 4 < len(lines):
                    sku = sku_candidate + " " + lines[i + 4].strip()
                    qty_line = lines[i + 5].strip() if i + 5 < len(lines) else "1"
                    skip_lines = 6
                else:
                    sku = sku_candidate
                    qty_line = lines[i + 4].strip() if i + 4 < len(lines) else "1"
                    skip_lines = 5

                # Clean AWB ID and SKU
                awb_id = awb_candidate.strip()
                sku_clean = sku.strip()

                # Validate AWB ID (should not be empty or just numbers like order ID)
                if awb_id and awb_id != order_id and not re.match(r'^\d{11}$', awb_id):
                    # Append cleaned row
                    entries.append({
                        "Order ID": order_id,
                        "AWB ID": awb_id,
                        "Courier": courier if courier else "Unknown",
                        "SKU": sku_clean if sku_clean else "Unknown",
                        "Qty": 1
                    })
                    
                    logger.debug(f"Extracted: Order {order_id}, AWB {awb_id}, SKU {sku_clean}")
                else:
                    logger.warning(f"Invalid AWB ID '{awb_id}' for order {order_id}")

                # Skip processed lines
                i += skip_lines
                
            except IndexError as e:
                logger.warning(f"Index error processing order {order_id}: {str(e)}")
                i += 1
            except Exception as e:
                logger.warning(f"Error processing order {order_id}: {str(e)}")
                i += 1
        else:
            i += 1

    # Create DataFrame
    df = pd.DataFrame(entries)
    logger.info(f"Successfully parsed {len(df)} orders from PDF manifest")
    
    # Log some statistics
    if not df.empty:
        unique_couriers = df['Courier'].unique()
        logger.info(f"Found couriers: {', '.join(unique_couriers)}")
        logger.info(f"Orders per courier: {df['Courier'].value_counts().to_dict()}")
    
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
                
                # Return updated stats for dashboard
                packed = len(df[df['Status'] == 'Packed'])
                pending = len(df[df['Status'] == 'Pending'])
                cancelled = len(df[df['Status'] == 'Cancelled'])
                
                return jsonify({
                    'success': True, 
                    'message': f'AWB {awb_id} marked as Packed',
                    'status': 'Packed',
                    'stats': {
                        'packed': packed,
                        'pending': pending,
                        'cancelled': cancelled,
                        'total': len(df)
                    }
                })
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
            
            # Return updated stats for dashboard
            packed = len(df[df['Status'] == 'Packed'])
            pending = len(df[df['Status'] == 'Pending'])
            cancelled = len(df[df['Status'] == 'Cancelled'])
            
            return jsonify({
                'success': True, 
                'message': f'AWB {awb_id} not found in manifest - marked as Cancelled',
                'status': 'Cancelled', 
                'confirm': True,
                'stats': {
                    'packed': packed,
                    'pending': pending,
                    'cancelled': cancelled,
                    'total': len(df)
                }
            })
            
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

@app.route('/api/stats')
def get_stats():
    try:
        if not os.path.exists(DATA_FILE):
            return jsonify({'packed': 0, 'pending': 0, 'cancelled': 0, 'total': 0})
        
        df = pd.read_csv(DATA_FILE)
        packed = len(df[df['Status'] == 'Packed'])
        pending = len(df[df['Status'] == 'Pending'])
        cancelled = len(df[df['Status'] == 'Cancelled'])
        
        return jsonify({
            'packed': packed,
            'pending': pending,
            'cancelled': cancelled,
            'total': len(df)
        })
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({'packed': 0, 'pending': 0, 'cancelled': 0, 'total': 0})

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

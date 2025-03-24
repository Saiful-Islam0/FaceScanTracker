import os
import logging
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
import json
import time
from datetime import datetime
import face_utils

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Ensure directories exist
UPLOAD_FOLDER = 'uploads'
ENROLLMENTS_FILE = 'enrollments.json'
ATTENDANCE_FILE = 'attendance.json'

# Create necessary directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize face enrollments if file doesn't exist
if not os.path.exists(ENROLLMENTS_FILE):
    with open(ENROLLMENTS_FILE, 'w') as f:
        json.dump([], f)
else:
    # Check if we need to update existing enrollments to the new format
    try:
        with open(ENROLLMENTS_FILE, 'r') as f:
            enrollments = json.load(f)
            
        updated = False
        
        # Check each enrollment for the new features format
        for enrollment in enrollments:
            if 'encoding' in enrollment and 'features' not in enrollment['encoding'] and 'image_path' in enrollment:
                # This enrollment needs to be updated to the new format
                logger.info(f"Updating enrollment for {enrollment['name']}")
                
                # Re-process the image to get the new encoding format
                if os.path.exists(enrollment['image_path']):
                    new_encoding = face_utils.extract_face_encoding(enrollment['image_path'])
                    if new_encoding:
                        enrollment['encoding'] = new_encoding
                        updated = True
        
        # Save updated enrollments if any were changed
        if updated:
            logger.info("Saving updated enrollments with new feature format")
            with open(ENROLLMENTS_FILE, 'w') as f:
                json.dump(enrollments, f)
                
    except Exception as e:
        logger.exception("Error updating enrollments to new format")

# Initialize attendance records if file doesn't exist
if not os.path.exists(ATTENDANCE_FILE):
    with open(ATTENDANCE_FILE, 'w') as f:
        json.dump({}, f)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/enrollment')
def enrollment():
    return render_template('enrollment.html')

@app.route('/attendance')
def attendance():
    return render_template('attendance.html')

@app.route('/records')
def records():
    # Load attendance records
    try:
        with open(ATTENDANCE_FILE, 'r') as f:
            attendance_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        attendance_data = {}
    
    # Load enrollment data to map IDs to names
    try:
        with open(ENROLLMENTS_FILE, 'r') as f:
            enrollments = json.load(f)
            # Create a dictionary mapping ID to name
            id_to_name = {entry['id']: entry['name'] for entry in enrollments}
    except (FileNotFoundError, json.JSONDecodeError):
        enrollments = []
        id_to_name = {}
    
    # Process attendance records for display
    formatted_records = []
    for date, records in attendance_data.items():
        for record in records:
            person_id = record['id']
            formatted_records.append({
                'name': id_to_name.get(person_id, f"Unknown ({person_id})"),
                'id': person_id,
                'date': date,
                'time': record['time']
            })
    
    # Sort records by date and time (newest first)
    formatted_records.sort(key=lambda x: (x['date'], x['time']), reverse=True)
    
    return render_template('records.html', records=formatted_records)

@app.route('/api/enroll', methods=['POST'])
def enroll_face():
    try:
        # Check if image data is in the request
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        image_file = request.files['image']
        name = request.form.get('name', '')
        
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        # Generate a unique ID using timestamp
        person_id = f"person_{int(time.time())}"
        
        # Save the image temporarily
        filename = secure_filename(f"{person_id}.jpg")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        image_file.save(filepath)
        
        # Extract face encoding
        face_encoding = face_utils.extract_face_encoding(filepath)
        
        if face_encoding is None:
            os.remove(filepath)  # Clean up the temporary file
            return jsonify({'success': False, 'error': 'No face detected in the image'}), 400
        
        # Load existing enrollments
        try:
            with open(ENROLLMENTS_FILE, 'r') as f:
                enrollments = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            enrollments = []
        
        # Add new enrollment
        enrollments.append({
            'id': person_id,
            'name': name,
            'encoding': face_encoding,
            'image_path': filepath,
            'enrolled_at': datetime.now().isoformat()
        })
        
        # Save updated enrollments
        with open(ENROLLMENTS_FILE, 'w') as f:
            json.dump(enrollments, f)
        
        return jsonify({'success': True, 'id': person_id, 'name': name})
    
    except Exception as e:
        logger.exception("Error in face enrollment")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recognize', methods=['POST'])
def recognize_face():
    try:
        # Check if image data is in the request
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        image_file = request.files['image']
        
        # Save the image temporarily
        filename = secure_filename(f"recognize_{int(time.time())}.jpg")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        image_file.save(filepath)
        
        # Extract face encoding
        face_encoding = face_utils.extract_face_encoding(filepath)
        
        if face_encoding is None:
            os.remove(filepath)  # Clean up the temporary file
            return jsonify({'success': False, 'error': 'No face detected in the image'}), 400
        
        # Load existing enrollments
        try:
            with open(ENROLLMENTS_FILE, 'r') as f:
                enrollments = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            enrollments = []
        
        # Find matching face
        match = face_utils.find_matching_face(face_encoding, enrollments)
        
        # Clean up the temporary file
        os.remove(filepath)
        
        if match:
            # Record attendance
            today = datetime.now().strftime('%Y-%m-%d')
            current_time = datetime.now().strftime('%H:%M:%S')
            
            try:
                with open(ATTENDANCE_FILE, 'r') as f:
                    attendance_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                attendance_data = {}
            
            # Initialize the date entry if it doesn't exist
            if today not in attendance_data:
                attendance_data[today] = []
            
            # Check if person has already been marked for today
            person_already_marked = any(
                record['id'] == match['id'] for record in attendance_data[today]
            )
            
            if not person_already_marked:
                # Add attendance record
                attendance_data[today].append({
                    'id': match['id'],
                    'time': current_time
                })
                
                # Save updated attendance data
                with open(ATTENDANCE_FILE, 'w') as f:
                    json.dump(attendance_data, f)
                
                return jsonify({
                    'success': True, 
                    'recognized': True,
                    'id': match['id'],
                    'name': match['name'],
                    'newAttendance': True
                })
            else:
                return jsonify({
                    'success': True, 
                    'recognized': True,
                    'id': match['id'],
                    'name': match['name'],
                    'newAttendance': False,
                    'message': 'Attendance already recorded for today'
                })
        else:
            return jsonify({'success': True, 'recognized': False})
    
    except Exception as e:
        logger.exception("Error in face recognition")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_enrollments', methods=['GET'])
def get_enrollments():
    try:
        with open(ENROLLMENTS_FILE, 'r') as f:
            enrollments = json.load(f)
        
        # Return only non-sensitive data
        simplified_enrollments = []
        for enrollment in enrollments:
            simplified_enrollments.append({
                'id': enrollment['id'],
                'name': enrollment['name'],
                'enrolled_at': enrollment['enrolled_at']
            })
        
        return jsonify({'success': True, 'enrollments': simplified_enrollments})
    
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'success': True, 'enrollments': []})
    except Exception as e:
        logger.exception("Error getting enrollments")
        return jsonify({'success': False, 'error': str(e)}), 500

import os
import logging
import io
import csv
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session, send_file, Response
from werkzeug.utils import secure_filename
import json
import time
import pandas as pd
from datetime import datetime
import face_utils
from fpdf import FPDF
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

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
CLASSES_FILE = 'classes.json'
CHARTS_FOLDER = 'static/charts'

# Create necessary directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CHARTS_FOLDER, exist_ok=True)

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

# Initialize classes if file doesn't exist
if not os.path.exists(CLASSES_FILE):
    with open(CLASSES_FILE, 'w') as f:
        # Create a default class
        json.dump([{"id": "default", "name": "Default Class", "created_at": datetime.now().isoformat()}], f)

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
    
    # Load enrollment data to map IDs to names and classes
    try:
        with open(ENROLLMENTS_FILE, 'r') as f:
            enrollments = json.load(f)
            # Create dictionaries mapping ID to name and class
            id_to_info = {entry['id']: {'name': entry['name'], 'class_id': entry.get('class_id', 'default')} 
                         for entry in enrollments}
    except (FileNotFoundError, json.JSONDecodeError):
        enrollments = []
        id_to_info = {}
    
    # Load classes for class name lookup
    try:
        with open(CLASSES_FILE, 'r') as f:
            classes = json.load(f)
            class_names = {c['id']: c['name'] for c in classes}
    except (FileNotFoundError, json.JSONDecodeError):
        class_names = {'default': 'Default Class'}
    
    # Process attendance records for display
    formatted_records = []
    for date, records in attendance_data.items():
        for record in records:
            person_id = record['id']
            person_info = id_to_info.get(person_id, {'name': f"Unknown ({person_id})", 'class_id': 'default'})
            class_id = record.get('class_id', person_info['class_id'])
            
            formatted_records.append({
                'name': person_info['name'],
                'id': person_id,
                'class_id': class_id,
                'class_name': class_names.get(class_id, 'Default Class'),
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
        class_id = request.form.get('class_id', 'default')
        
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
        
        # Validate class_id exists
        try:
            with open(CLASSES_FILE, 'r') as f:
                classes = json.load(f)
                class_exists = any(c['id'] == class_id for c in classes)
                
                if not class_exists:
                    class_id = 'default'  # Fallback to default if class doesn't exist
        except (FileNotFoundError, json.JSONDecodeError):
            class_id = 'default'  # Fallback to default
        
        # Add new enrollment
        enrollments.append({
            'id': person_id,
            'name': name,
            'class_id': class_id,
            'encoding': face_encoding,
            'image_path': filepath,
            'enrolled_at': datetime.now().isoformat()
        })
        
        # Save updated enrollments
        with open(ENROLLMENTS_FILE, 'w') as f:
            json.dump(enrollments, f)
        
        return jsonify({'success': True, 'id': person_id, 'name': name, 'class_id': class_id})
    
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
        class_id = request.form.get('class_id', None)  # Optional class filter
        
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
        
        # Filter enrollments by class_id if specified
        if class_id:
            filtered_enrollments = [e for e in enrollments if e.get('class_id', 'default') == class_id]
        else:
            filtered_enrollments = enrollments
        
        # Find matching face
        match = face_utils.find_matching_face(face_encoding, filtered_enrollments)
        
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
                # Add attendance record with class info
                attendance_data[today].append({
                    'id': match['id'],
                    'time': current_time,
                    'class_id': match.get('class_id', 'default')
                })
                
                # Save updated attendance data
                with open(ATTENDANCE_FILE, 'w') as f:
                    json.dump(attendance_data, f)
                
                return jsonify({
                    'success': True, 
                    'recognized': True,
                    'id': match['id'],
                    'name': match['name'],
                    'class_id': match.get('class_id', 'default'),
                    'newAttendance': True
                })
            else:
                return jsonify({
                    'success': True, 
                    'recognized': True,
                    'id': match['id'],
                    'name': match['name'],
                    'class_id': match.get('class_id', 'default'),
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
        
        # Optional class filter
        class_id = request.args.get('class_id', None)
        
        # Return only non-sensitive data
        simplified_enrollments = []
        for enrollment in enrollments:
            # Filter by class if requested
            if class_id and enrollment.get('class_id', 'default') != class_id:
                continue
                
            simplified_enrollments.append({
                'id': enrollment['id'],
                'name': enrollment['name'],
                'class_id': enrollment.get('class_id', 'default'),
                'enrolled_at': enrollment['enrolled_at']
            })
        
        return jsonify({'success': True, 'enrollments': simplified_enrollments})
    
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'success': True, 'enrollments': []})
    except Exception as e:
        logger.exception("Error getting enrollments")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/enrollments/<enrollment_id>', methods=['DELETE'])
def delete_enrollment(enrollment_id):
    try:
        # Load enrollments
        with open(ENROLLMENTS_FILE, 'r') as f:
            enrollments = json.load(f)
        
        # Find the enrollment to delete
        enrollment_index = None
        for i, enrollment in enumerate(enrollments):
            if enrollment['id'] == enrollment_id:
                enrollment_index = i
                break
        
        if enrollment_index is None:
            return jsonify({'success': False, 'error': 'Enrollment not found'}), 404
        
        # Remove the enrollment image if it exists
        deleted_enrollment = enrollments[enrollment_index]
        if 'image_path' in deleted_enrollment and os.path.exists(deleted_enrollment['image_path']):
            try:
                os.remove(deleted_enrollment['image_path'])
            except Exception as e:
                logger.warning(f"Could not delete enrollment image: {e}")
        
        # Remove the enrollment
        enrollments.pop(enrollment_index)
        
        # Save updated enrollments
        with open(ENROLLMENTS_FILE, 'w') as f:
            json.dump(enrollments, f)
        
        return jsonify({'success': True, 'message': 'Enrollment deleted successfully'})
    
    except Exception as e:
        logger.exception("Error deleting enrollment")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/classes')
def classes():
    return render_template('classes.html')

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

@app.route('/api/classes', methods=['GET'])
def get_classes():
    try:
        with open(CLASSES_FILE, 'r') as f:
            classes = json.load(f)
        return jsonify({'success': True, 'classes': classes})
    
    except (FileNotFoundError, json.JSONDecodeError):
        # Return default class if file doesn't exist
        default_class = [{"id": "default", "name": "Default Class", "created_at": datetime.now().isoformat()}]
        return jsonify({'success': True, 'classes': default_class})
    except Exception as e:
        logger.exception("Error getting classes")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/classes', methods=['POST'])
def create_class():
    try:
        name = request.form.get('name', '')
        
        if not name:
            return jsonify({'success': False, 'error': 'Class name is required'}), 400
        
        # Generate a unique ID for the class
        class_id = f"class_{int(time.time())}"
        
        # Load existing classes
        try:
            with open(CLASSES_FILE, 'r') as f:
                classes = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            classes = [{"id": "default", "name": "Default Class", "created_at": datetime.now().isoformat()}]
        
        # Add new class
        classes.append({
            'id': class_id,
            'name': name,
            'created_at': datetime.now().isoformat()
        })
        
        # Save updated classes
        with open(CLASSES_FILE, 'w') as f:
            json.dump(classes, f)
        
        return jsonify({'success': True, 'id': class_id, 'name': name})
    
    except Exception as e:
        logger.exception("Error creating class")
        return jsonify({'success': False, 'error': str(e)}), 500
        
@app.route('/api/classes/<class_id>', methods=['DELETE'])
def delete_class(class_id):
    try:
        # Don't allow deletion of the default class
        if class_id == 'default':
            return jsonify({'success': False, 'error': 'Cannot delete the default class'}), 400
        
        # Load classes
        with open(CLASSES_FILE, 'r') as f:
            classes = json.load(f)
        
        # Find the class to delete
        class_index = None
        for i, cls in enumerate(classes):
            if cls['id'] == class_id:
                class_index = i
                break
        
        if class_index is None:
            return jsonify({'success': False, 'error': 'Class not found'}), 404
        
        # Remove the class
        classes.pop(class_index)
        
        # Save updated classes
        with open(CLASSES_FILE, 'w') as f:
            json.dump(classes, f)
        
        # Update all enrollments that were in this class to be in the default class
        with open(ENROLLMENTS_FILE, 'r') as f:
            enrollments = json.load(f)
        
        # Count how many enrollments were updated
        updated_count = 0
        for enrollment in enrollments:
            if enrollment.get('class_id') == class_id:
                enrollment['class_id'] = 'default'
                updated_count += 1
        
        # Save updated enrollments
        with open(ENROLLMENTS_FILE, 'w') as f:
            json.dump(enrollments, f)
        
        return jsonify({
            'success': True, 
            'message': f'Class deleted successfully. {updated_count} enrollments moved to Default Class.'
        })
    
    except Exception as e:
        logger.exception("Error deleting class")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    try:
        # Optional filters
        date = request.args.get('date', None)
        class_id = request.args.get('class_id', None)
        
        # Load attendance data
        with open(ATTENDANCE_FILE, 'r') as f:
            attendance_data = json.load(f)
        
        # Load enrollments for name lookup
        with open(ENROLLMENTS_FILE, 'r') as f:
            enrollments = json.load(f)
            id_to_info = {e['id']: {'name': e['name'], 'class_id': e.get('class_id', 'default')} for e in enrollments}
        
        # Filter by date if specified
        if date and date in attendance_data:
            filtered_data = {date: attendance_data[date]}
        else:
            filtered_data = attendance_data
        
        # Process and format data
        formatted_records = []
        for curr_date, records in filtered_data.items():
            for record in records:
                person_id = record['id']
                person_info = id_to_info.get(person_id, {'name': f"Unknown ({person_id})", 'class_id': 'default'})
                
                # Filter by class if requested
                if class_id and person_info['class_id'] != class_id:
                    continue
                    
                formatted_records.append({
                    'id': person_id,
                    'name': person_info['name'],
                    'class_id': record.get('class_id', person_info['class_id']),  # Use record's class_id if available
                    'date': curr_date,
                    'time': record['time']
                })
        
        # Sort by date and time (newest first)
        formatted_records.sort(key=lambda x: (x['date'], x['time']), reverse=True)
        
        return jsonify({'success': True, 'records': formatted_records})
    
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'success': True, 'records': []})
    except Exception as e:
        logger.exception("Error getting attendance records")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    try:
        # Load attendance data
        with open(ATTENDANCE_FILE, 'r') as f:
            attendance_data = json.load(f)
        
        # Load enrollments for name lookup
        with open(ENROLLMENTS_FILE, 'r') as f:
            enrollments = json.load(f)
            
        # Load classes
        with open(CLASSES_FILE, 'r') as f:
            classes = json.load(f)
            class_names = {c['id']: c['name'] for c in classes}
        
        # Calculate statistics
        total_enrollments = len(enrollments)
        class_counts = {}
        
        # Count enrollments by class
        for enrollment in enrollments:
            class_id = enrollment.get('class_id', 'default')
            if class_id not in class_counts:
                class_counts[class_id] = 0
            class_counts[class_id] += 1
        
        # Count attendance by date
        attendance_by_date = {}
        for date, records in attendance_data.items():
            attendance_by_date[date] = len(records)
        
        # Calculate attendance by class
        attendance_by_class = {}
        for date, records in attendance_data.items():
            for record in records:
                person_id = record['id']
                # Find the person's class
                for enrollment in enrollments:
                    if enrollment['id'] == person_id:
                        class_id = enrollment.get('class_id', 'default')
                        if class_id not in attendance_by_class:
                            attendance_by_class[class_id] = {}
                        if date not in attendance_by_class[class_id]:
                            attendance_by_class[class_id][date] = 0
                        attendance_by_class[class_id][date] += 1
                        break
        
        # Format analytics data
        analytics = {
            'total_enrollments': total_enrollments,
            'classes': [{
                'id': class_id,
                'name': class_names.get(class_id, 'Unknown Class'),
                'enrollment_count': count
            } for class_id, count in class_counts.items()],
            'attendance_by_date': [{'date': date, 'count': count} for date, count in attendance_by_date.items()],
            'attendance_by_class': [{
                'class_id': class_id,
                'class_name': class_names.get(class_id, 'Unknown Class'),
                'attendance': [{'date': date, 'count': count} for date, count in dates.items()]
            } for class_id, dates in attendance_by_class.items()]
        }
        
        # Create and save charts
        # We'll generate analytics charts based on this data in separate endpoints
        
        return jsonify({'success': True, 'analytics': analytics})
    
    except Exception as e:
        logger.exception("Error generating analytics")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/export_attendance_csv')
def export_attendance_csv():
    try:
        # Optional filters
        date = request.args.get('date', None)
        class_id = request.args.get('class_id', None)
        
        # Load attendance data
        with open(ATTENDANCE_FILE, 'r') as f:
            attendance_data = json.load(f)
        
        # Load enrollments for name lookup
        with open(ENROLLMENTS_FILE, 'r') as f:
            enrollments = json.load(f)
            id_to_info = {e['id']: {'name': e['name'], 'class_id': e.get('class_id', 'default')} for e in enrollments}
        
        # Load classes for class name lookup
        with open(CLASSES_FILE, 'r') as f:
            classes = json.load(f)
            class_names = {c['id']: c['name'] for c in classes}
        
        # Filter by date if specified
        if date and date in attendance_data:
            filtered_data = {date: attendance_data[date]}
        else:
            filtered_data = attendance_data
        
        # Create a CSV string
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Name', 'ID', 'Class', 'Date', 'Time'])
        
        for curr_date, records in filtered_data.items():
            for record in records:
                person_id = record['id']
                person_info = id_to_info.get(person_id, {'name': f"Unknown ({person_id})", 'class_id': 'default'})
                
                # Filter by class if requested
                if class_id and person_info['class_id'] != class_id:
                    continue
                
                record_class_id = record.get('class_id', person_info['class_id'])
                class_name = class_names.get(record_class_id, 'Unknown Class')
                
                writer.writerow([
                    person_info['name'],
                    person_id,
                    class_name,
                    curr_date,
                    record['time']
                ])
        
        # Create response with CSV
        output.seek(0)
        filename = f"attendance_{datetime.now().strftime('%Y%m%d')}.csv"
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )
    
    except Exception as e:
        logger.exception("Error exporting attendance to CSV")
        flash('Error exporting data. Please try again.', 'error')
        return redirect(url_for('records'))

@app.route('/export_attendance_pdf')
@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/api/attendance/query', methods=['POST'])
def query_attendance():
    try:
        data = request.get_json()
        query = data.get('query', '').lower()
        class_id = data.get('class_id')

        # Load all necessary data
        with open(ATTENDANCE_FILE, 'r') as f:
            attendance_data = json.load(f)
        with open(ENROLLMENTS_FILE, 'r') as f:
            enrollments = json.load(f)
        with open(CLASSES_FILE, 'r') as f:
            classes = json.load(f)
            class_names = {c['id']: c['name'] for c in classes}

        today = datetime.now().strftime('%Y-%m-%d')

        # If asking about classes, return available options
        if 'which classes' in query or 'list classes' in query:
            class_list = [f"- {c['name']}" for c in classes]
            return jsonify({
                'success': True,
                'response': "Available classes:\n" + "\n".join(class_list),
                'requires_class': False
            })

        # Handle class-specific attendance queries
        if ('who was present' in query or 'who was absent' in query) and not class_id:
            return jsonify({
                'success': True,
                'response': "Please select a class:",
                'requires_class': True,
                'classes': [{'id': c['id'], 'name': c['name']} for c in classes]
            })

        # Total students query
        if 'total student' in query or 'how many student' in query:
            if class_id:
                class_students = [e for e in enrollments if e.get('class_id') == class_id]
                class_name = class_names.get(class_id, 'Unknown Class')
                return jsonify({
                    'success': True,
                    'response': f"Total students in {class_name}: {len(class_students)}"
                })
            total = len(enrollments)
            return jsonify({
                'success': True,
                'response': f"Total students enrolled: {total}"
            })

        # Student names query
        if 'student names' in query or 'list students' in query:
            if class_id:
                class_students = [e for e in enrollments if e.get('class_id') == class_id]
                class_name = class_names.get(class_id, 'Unknown Class')
                names = [f"- {e['name']}" for e in class_students]
                return jsonify({
                    'success': True,
                    'response': f"Students in {class_name}:\n" + "\n".join(names)
                })
            return jsonify({
                'success': True,
                'response': "Please select a class:",
                'requires_class': True,
                'classes': [{'id': c['id'], 'name': c['name']} for c in classes]
            })

        # Present/Absent queries with class filter
        if class_id and today in attendance_data:
            class_enrollments = [e for e in enrollments if e.get('class_id') == class_id]
            class_name = class_names.get(class_id, 'Unknown Class')
            
            if 'who was present' in query:
                present_ids = [r['id'] for r in attendance_data[today] if r.get('class_id') == class_id]
                names = [e['name'] for e in class_enrollments if e['id'] in present_ids]
                if names:
                    return jsonify({
                        'success': True,
                        'response': f"Present today in {class_name}:\n- " + "\n- ".join(names)
                    })
                return jsonify({
                    'success': True,
                    'response': f"No students present today in {class_name}"
                })
                
            elif 'who was absent' in query:
                present_ids = [r['id'] for r in attendance_data[today] if r.get('class_id') == class_id]
                names = [e['name'] for e in class_enrollments if e['id'] not in present_ids]
                if names:
                    return jsonify({
                        'success': True,
                        'response': f"Absent today in {class_name}:\n- " + "\n- ".join(names)
                    })
                return jsonify({
                    'success': True,
                    'response': f"No students absent today in {class_name}"
                })

        # Show help message for unknown queries
        return jsonify({
            'success': True,
            'response': "I can help you with:\n- Who was present today?\n- Who was absent today?\n- Show attendance trends\n- Total students\n- List students\n- List classes"
        })

    except Exception as e:
        logger.exception("Error processing chatbot query")
        return jsonify({'success': False, 'error': str(e)}), 500

    except Exception as e:
        logger.exception("Error processing chatbot query")
        return jsonify({'success': False, 'error': str(e)}), 500

def export_attendance_pdf():
    try:
        # Optional filters
        date = request.args.get('date', None)
        class_id = request.args.get('class_id', None)
        
        # Load attendance data
        with open(ATTENDANCE_FILE, 'r') as f:
            attendance_data = json.load(f)
        
        # Load enrollments for name lookup
        with open(ENROLLMENTS_FILE, 'r') as f:
            enrollments = json.load(f)
            id_to_info = {e['id']: {'name': e['name'], 'class_id': e.get('class_id', 'default')} for e in enrollments}
        
        # Load classes for class name lookup
        with open(CLASSES_FILE, 'r') as f:
            classes = json.load(f)
            class_names = {c['id']: c['name'] for c in classes}
            
        # Filter by date if specified
        if date and date in attendance_data:
            filtered_data = {date: attendance_data[date]}
        else:
            filtered_data = attendance_data
            
        # Create a PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Set up PDF styling
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Attendance Report", 0, 1, 'C')
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}", 0, 1, 'C')
        pdf.ln(10)
        
        if class_id:
            class_name = class_names.get(class_id, 'Unknown Class')
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"Class: {class_name}", 0, 1)
        
        # Set up the table headers
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(60, 10, "Name", 1, 0)
        pdf.cell(40, 10, "Class", 1, 0)
        pdf.cell(30, 10, "Date", 1, 0)
        pdf.cell(30, 10, "Time", 1, 1)
        
        # Add data rows
        pdf.set_font("Arial", '', 10)
        
        # Collect and sort all records
        all_records = []
        for curr_date, records in filtered_data.items():
            for record in records:
                person_id = record['id']
                person_info = id_to_info.get(person_id, {'name': f"Unknown ({person_id})", 'class_id': 'default'})
                
                # Filter by class if requested
                if class_id and person_info['class_id'] != class_id:
                    continue
                
                record_class_id = record.get('class_id', person_info['class_id'])
                class_name = class_names.get(record_class_id, 'Unknown Class')
                
                all_records.append({
                    'name': person_info['name'],
                    'class': class_name,
                    'date': curr_date,
                    'time': record['time']
                })
        
        # Sort by date and time
        all_records.sort(key=lambda x: (x['date'], x['time']), reverse=True)
        
        # Add records to PDF
        for record in all_records:
            # Check if we need to add a new page
            if pdf.get_y() > 250:
                pdf.add_page()
                # Re-add headers on new page
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(60, 10, "Name", 1, 0)
                pdf.cell(40, 10, "Class", 1, 0)
                pdf.cell(30, 10, "Date", 1, 0)
                pdf.cell(30, 10, "Time", 1, 1)
                pdf.set_font("Arial", '', 10)
            
            pdf.cell(60, 10, record['name'], 1, 0)
            pdf.cell(40, 10, record['class'], 1, 0)
            pdf.cell(30, 10, record['date'], 1, 0)
            pdf.cell(30, 10, record['time'], 1, 1)
        
        # Output the PDF
        pdf_output = pdf.output(dest='S').encode('latin-1')
        filename = f"attendance_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return Response(
            pdf_output,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )
    
    except Exception as e:
        logger.exception("Error exporting attendance to PDF")
        flash('Error exporting data. Please try again.', 'error')
        return redirect(url_for('records'))

@app.route('/attendance_by_date_chart')
def attendance_by_date_chart():
    try:
        # Load attendance data
        with open(ATTENDANCE_FILE, 'r') as f:
            attendance_data = json.load(f)
        
        # Count attendance by date
        dates = []
        counts = []
        
        # Get the last 14 days of data
        sorted_dates = sorted(attendance_data.keys(), reverse=True)[:14]
        sorted_dates.reverse()  # Put in chronological order for the chart
        
        for date in sorted_dates:
            dates.append(date)
            counts.append(len(attendance_data[date]))
        
        # Create the chart
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(dates, counts, color='skyblue')
        ax.set_xlabel('Date')
        ax.set_ylabel('Attendance Count')
        ax.set_title('Daily Attendance')
        
        # Rotate date labels for better readability
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save chart to memory
        output = io.BytesIO()
        FigureCanvas(fig).print_png(output)
        
        return Response(output.getvalue(), mimetype='image/png')
    
    except Exception as e:
        logger.exception("Error generating attendance chart")
        # Return a simple error image
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.text(0.5, 0.5, 'Error generating chart', ha='center', va='center')
        ax.set_axis_off()
        
        output = io.BytesIO()
        FigureCanvas(fig).print_png(output)
        
        return Response(output.getvalue(), mimetype='image/png')

@app.route('/enrollment_by_class_chart')
def enrollment_by_class_chart():
    try:
        # Load enrollments
        with open(ENROLLMENTS_FILE, 'r') as f:
            enrollments = json.load(f)
        
        # Load classes for name lookup
        with open(CLASSES_FILE, 'r') as f:
            classes = json.load(f)
            class_names = {c['id']: c['name'] for c in classes}
        
        # Count enrollments by class
        class_counts = {}
        for enrollment in enrollments:
            class_id = enrollment.get('class_id', 'default')
            if class_id not in class_counts:
                class_counts[class_id] = 0
            class_counts[class_id] += 1
        
        # Prepare data for chart
        class_labels = [class_names.get(cid, 'Unknown') for cid in class_counts.keys()]
        counts = list(class_counts.values())
        
        # Create the chart
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(class_labels, counts, color='lightgreen')
        ax.set_xlabel('Class')
        ax.set_ylabel('Number of Students')
        ax.set_title('Enrollments by Class')
        
        # Rotate labels if there are many classes
        if len(class_labels) > 3:
            plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save chart to memory
        output = io.BytesIO()
        FigureCanvas(fig).print_png(output)
        
        return Response(output.getvalue(), mimetype='image/png')
    
    except Exception as e:
        logger.exception("Error generating enrollment chart")
        # Return a simple error image
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.text(0.5, 0.5, 'Error generating chart', ha='center', va='center')
        ax.set_axis_off()
        
        output = io.BytesIO()
        FigureCanvas(fig).print_png(output)
        
        return Response(output.getvalue(), mimetype='image/png')

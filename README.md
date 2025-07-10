
# Face Recognition Attendance System.

A Flask-based attendance management system with face recognition capabilities and AI assistance.

## Features

- **Face Recognition Attendance**: Take attendance using facial recognition
- **Class Management**: Create and manage multiple classes
- **AI Assistant**: Natural language queries about attendance data
- **Analytics**: Visual reports and statistics
- **Export Options**: Export attendance data in PDF and CSV formats
- **Real-time Updates**: Instant attendance tracking and verification

## Tech Stack

- Python 3.11+
- Flask
- OpenCV
- face-recognition
- SQLAlchemy
- Matplotlib
- FPDF
- Bootstrap 5

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Saiful-Islam0/FaceScanTracker.git
cd face-recognition-attendance
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

The application will be available at `http://localhost:5000`

## Usage

1. **Enrollment**
   - Navigate to the Enrollment page
   - Enter student name and select class
   - Capture face image for recognition

2. **Taking Attendance**
   - Go to the Attendance page
   - System will automatically recognize enrolled faces
   - Attendance is recorded with timestamp

3. **Reports**
   - View attendance records
   - Generate PDF/CSV reports
   - Check analytics and trends

4. **AI Assistant**
   - Ask questions like:
     - "Who was present today?"
     - "Show attendance trends"
     - "Total students in Class A"

## Project Structure

```
├── app.py          # Main application logic
├── face_utils.py   # Face recognition utilities
├── models.py       # Data models
├── templates/      # HTML templates
├── static/         # Static files (CSS, JS)
└── uploads/        # Uploaded images storage
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

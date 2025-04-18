// Handle face enrollment functionality

let enrollmentVideo = document.getElementById('enrollmentVideo');
let enrollButton = document.getElementById('enrollButton');
let nameInput = document.getElementById('nameInput');
let enrollmentForm = document.getElementById('enrollmentForm');
let enrollmentResult = document.getElementById('enrollmentResult');
let enrollmentList = document.getElementById('enrollmentList');
let cameraStream = null;

// Initialize the camera when the page loads
document.addEventListener('DOMContentLoaded', () => {
    initCamera();
    loadEnrollments();
    loadClasses();
});

// Initialize camera
function initCamera() {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: 'user'
            }, 
            audio: false 
        })
        .then(function(stream) {
            cameraStream = stream;
            enrollmentVideo.srcObject = stream;
            enrollmentVideo.play();
            
            // Enable the enroll button once camera is working
            if (enrollButton) {
                enrollButton.disabled = false;
            }
        })
        .catch(function(error) {
            console.error("Camera error:", error);
            // Show user-friendly error message
            const videoContainer = document.querySelector('.video-container');
            const errorMessage = document.createElement('div');
            errorMessage.className = 'camera-error';
            errorMessage.innerHTML = `
                <p><strong>Camera access error:</strong> ${error.message}</p>
                <p>Please ensure you've granted camera permissions and that no other application is using your camera.</p>
            `;
            videoContainer.appendChild(errorMessage);
        });
    } else {
        console.error("getUserMedia not supported");
        alert("Your browser doesn't support camera access. Please try a different browser.");
    }
}

// Capture a frame from the video stream
function captureFrame() {
    return new Promise((resolve, reject) => {
        if (!enrollmentVideo || !cameraStream) {
            reject("Camera not initialized");
            return;
        }
        
        // Create a canvas element to capture the frame
        const canvas = document.createElement('canvas');
        canvas.width = enrollmentVideo.videoWidth;
        canvas.height = enrollmentVideo.videoHeight;
        
        // Draw the current video frame to the canvas
        const context = canvas.getContext('2d');
        context.drawImage(enrollmentVideo, 0, 0, canvas.width, canvas.height);
        
        // Convert the canvas to a blob
        canvas.toBlob((blob) => {
            resolve(blob);
        }, 'image/jpeg', 0.9);
    });
}

// Load existing enrollments
async function loadEnrollments() {
    try {
        const response = await fetch('/api/get_enrollments');
        const data = await response.json();
        
        if (data.success && enrollmentList) {
            // Clear existing list
            enrollmentList.innerHTML = '';
            
            if (data.enrollments.length === 0) {
                enrollmentList.innerHTML = '<div class="alert alert-info">No enrollments yet.</div>';
                return;
            }
            
            // Add each enrollment to the list
            data.enrollments.forEach(enrollment => {
                const enrollDate = new Date(enrollment.enrolled_at);
                const formattedDate = enrollDate.toLocaleDateString() + ' ' + enrollDate.toLocaleTimeString();
                
                const enrollItem = document.createElement('div');
                enrollItem.className = 'card mb-2';
                enrollItem.innerHTML = `
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h5 class="card-title">${enrollment.name}</h5>
                                <p class="card-text text-muted">Enrolled: ${formattedDate}</p>
                            </div>
                            <button class="btn btn-danger btn-sm delete-enrollment" data-id="${enrollment.id}">
                                <i class="bi bi-trash"></i> Delete
                            </button>
                        </div>
                    </div>
                `;
                
                enrollmentList.appendChild(enrollItem);
            });
        }
    } catch (error) {
        console.error("Error loading enrollments:", error);
    }
}

// Enrollment countdown and capture
function startEnrollCountdown() {
    return new Promise((resolve, reject) => {
        if (!enrollmentVideo || !cameraStream) {
            reject("Camera not initialized");
            return;
        }
        
        // Create overlay for countdown
        const overlay = document.createElement('div');
        overlay.className = 'capture-overlay';
        
        const countdownElement = document.createElement('div');
        countdownElement.className = 'capture-countdown';
        overlay.appendChild(countdownElement);
        
        // Add overlay to video container
        const videoContainer = enrollmentVideo.parentElement;
        videoContainer.appendChild(overlay);
        
        let count = 3;
        countdownElement.textContent = count;
        
        // Start countdown
        const interval = setInterval(() => {
            count--;
            
            if (count > 0) {
                countdownElement.textContent = count;
            } else {
                // Countdown complete, capture the image
                clearInterval(interval);
                countdownElement.textContent = '';
                countdownElement.className = 'capture-complete';
                countdownElement.textContent = 'Captured!';
                
                setTimeout(() => {
                    // Remove overlay after a short delay
                    videoContainer.removeChild(overlay);
                    
                    // Capture frame and resolve promise
                    captureFrame()
                        .then(resolve)
                        .catch(reject);
                }, 500);
            }
        }, 1000);
    });
}

// Load classes for dropdown
function loadClasses() {
    const classSelect = document.getElementById('classSelect');
    if (!classSelect) return;
    
    fetch('/api/classes')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Keep the first option (Default Class)
                const defaultOption = classSelect.options[0];
                classSelect.innerHTML = '';
                classSelect.appendChild(defaultOption);
                
                // Add class options
                data.classes.forEach(classItem => {
                    const option = document.createElement('option');
                    option.value = classItem.id;
                    option.textContent = classItem.name;
                    classSelect.appendChild(option);
                });
            } else {
                console.error('Error loading classes:', data.error);
            }
        })
        .catch(error => {
            console.error('Error fetching classes:', error);
        });
}

// Handle enrollment form submission
if (enrollmentForm) {
    enrollmentForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        
        const name = nameInput.value.trim();
        const classSelect = document.getElementById('classSelect');
        const classId = classSelect ? classSelect.value : 'default';
        
        if (!name) {
            alert("Please enter a name");
            return;
        }
        
        try {
            // Disable enroll button
            enrollButton.disabled = true;
            
            // Show loading state
            enrollmentResult.className = 'alert alert-info';
            enrollmentResult.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div> Processing enrollment...';
            
            // Start countdown and capture
            const imageBlob = await startEnrollCountdown();
            
            // Prepare form data for upload
            const formData = new FormData();
            formData.append('image', imageBlob, 'enrollment.jpg');
            formData.append('name', name);
            formData.append('class_id', classId);
            
            // Send to server for enrollment
            const response = await fetch('/api/enroll', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Enrollment successful
                enrollmentResult.className = 'alert alert-success';
                enrollmentResult.innerHTML = `
                    <strong>Success!</strong> ${result.name} has been enrolled.
                `;
                
                // Clear the name input
                nameInput.value = '';
                
                // Refresh the enrollment list
                loadEnrollments();
            } else {
                // Enrollment failed
                enrollmentResult.className = 'alert alert-danger';
                enrollmentResult.innerHTML = `
                    <strong>Error:</strong> ${result.error || 'Failed to enroll'}
                `;
            }
        } catch (error) {
            console.error("Error during enrollment:", error);
            enrollmentResult.className = 'alert alert-danger';
            enrollmentResult.innerHTML = `
                <strong>Error:</strong> ${error.message || 'Failed to capture or process image'}
            `;
        } finally {
            // Re-enable enroll button
            enrollButton.disabled = false;
        }
    });
}

// Delete enrollment function
async function deleteEnrollment(enrollmentId) {
    if (!confirm('Are you sure you want to delete this student? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/enrollments/${enrollmentId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Reload enrollments after deletion
            loadEnrollments();
            alert('Student deleted successfully');
        } else {
            alert(`Error deleting student: ${data.error}`);
        }
    } catch (error) {
        console.error('Error deleting enrollment:', error);
        alert('An error occurred while deleting the student. Please try again.');
    }
}

// Add event listener for delete buttons
if (enrollmentList) {
    enrollmentList.addEventListener('click', event => {
        const deleteBtn = event.target.closest('.delete-enrollment');
        if (deleteBtn) {
            const enrollmentId = deleteBtn.dataset.id;
            if (enrollmentId) {
                deleteEnrollment(enrollmentId);
            }
        }
    });
}

// Stop camera when leaving the page
window.addEventListener('beforeunload', () => {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => {
            track.stop();
        });
    }
});

// Camera handling for face recognition

let videoElement = document.getElementById('videoElement');
let captureButton = document.getElementById('captureButton');
let recognitionResult = document.getElementById('recognitionResult');
let cameraStream = null;

// Initialize the camera when the page loads
document.addEventListener('DOMContentLoaded', () => {
    initCamera();
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
            videoElement.srcObject = stream;
            videoElement.play();
            
            // Enable the capture button once camera is working
            if (captureButton) {
                captureButton.disabled = false;
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
        if (!videoElement || !cameraStream) {
            reject("Camera not initialized");
            return;
        }
        
        // Create a canvas element to capture the frame
        const canvas = document.createElement('canvas');
        canvas.width = videoElement.videoWidth;
        canvas.height = videoElement.videoHeight;
        
        // Draw the current video frame to the canvas
        const context = canvas.getContext('2d');
        context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
        
        // Convert the canvas to a blob
        canvas.toBlob((blob) => {
            resolve(blob);
        }, 'image/jpeg', 0.9);
    });
}

// Capture and recognize face
async function captureFace() {
    if (captureButton) {
        captureButton.disabled = true;
    }
    
    try {
        // Update UI to show we're processing
        if (recognitionResult) {
            recognitionResult.className = 'recognition-result recognition-warning';
            recognitionResult.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div> Processing...';
        }
        
        // Capture frame from video
        const imageBlob = await captureFrame();
        
        // Prepare form data for upload
        const formData = new FormData();
        formData.append('image', imageBlob, 'capture.jpg');
        
        // Send to server for recognition
        const response = await fetch('/api/recognize', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            if (result.recognized) {
                // Person recognized
                recognitionResult.className = 'recognition-result recognition-success';
                if (result.newAttendance) {
                    recognitionResult.innerHTML = `
                        <h4>Welcome, ${result.name}!</h4>
                        <p>Your attendance has been recorded.</p>
                    `;
                } else {
                    recognitionResult.innerHTML = `
                        <h4>Hello again, ${result.name}!</h4>
                        <p>${result.message}</p>
                    `;
                }
            } else {
                // No match found
                recognitionResult.className = 'recognition-result recognition-warning';
                recognitionResult.innerHTML = `
                    <h4>Face not recognized</h4>
                    <p>Please enroll in the system or try again.</p>
                `;
            }
        } else {
            // Error in processing
            recognitionResult.className = 'recognition-result recognition-error';
            recognitionResult.innerHTML = `
                <h4>Error</h4>
                <p>${result.error || 'Failed to process face recognition'}</p>
            `;
        }
    } catch (error) {
        console.error("Error during face capture:", error);
        if (recognitionResult) {
            recognitionResult.className = 'recognition-result recognition-error';
            recognitionResult.innerHTML = `
                <h4>Error</h4>
                <p>Failed to capture or process image: ${error.message}</p>
            `;
        }
    } finally {
        if (captureButton) {
            captureButton.disabled = false;
        }
    }
}

// Stop camera when leaving the page
window.addEventListener('beforeunload', () => {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => {
            track.stop();
        });
    }
});

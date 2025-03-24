document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    loadClasses();
    loadEnrollments();
    setupEventListeners();
});

// Load all classes
function loadClasses() {
    fetch('/api/classes')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayClasses(data.classes);
                populateClassDropdowns(data.classes);
            } else {
                console.error('Error loading classes:', data.error);
            }
        })
        .catch(error => {
            console.error('Error fetching classes:', error);
        });
}

// Display classes in the UI
function displayClasses(classes) {
    const container = document.getElementById('classesContainer');
    
    if (classes.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No classes have been created yet.</div>';
        return;
    }
    
    let html = '<div class="list-group">';
    
    classes.forEach(classItem => {
        const createDate = new Date(classItem.created_at).toLocaleDateString();
        const isDefault = classItem.id === 'default';
        
        html += `
            <div class="list-group-item">
                <div class="d-flex w-100 justify-content-between">
                    <h5 class="mb-1">${classItem.name}</h5>
                    <small class="text-muted">Created: ${createDate}</small>
                </div>
                <div class="d-flex justify-content-between align-items-center">
                    <p class="mb-1">Class ID: ${classItem.id}</p>
                    ${!isDefault ? `
                    <button class="btn btn-danger btn-sm delete-class" data-id="${classItem.id}">
                        <i class="bi bi-trash"></i> Delete
                    </button>
                    ` : ''}
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// Load all enrollments
function loadEnrollments() {
    fetch('/api/get_enrollments')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayEnrollments(data.enrollments);
            } else {
                console.error('Error loading enrollments:', data.error);
            }
        })
        .catch(error => {
            console.error('Error fetching enrollments:', error);
        });
}

// Display enrollments grouped by class
function displayEnrollments(enrollments) {
    const container = document.getElementById('enrollmentsContainer');
    
    if (enrollments.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No enrollments found.</div>';
        return;
    }
    
    // Group enrollments by class
    const classesList = {};
    
    enrollments.forEach(enrollment => {
        const classId = enrollment.class_id || 'default';
        
        if (!classesList[classId]) {
            classesList[classId] = {
                name: null,  // Will be set later
                students: []
            };
        }
        
        classesList[classId].students.push(enrollment);
    });
    
    // Get class names from class dropdown
    const classSelect = document.getElementById('classFilterEnrollments');
    const options = Array.from(classSelect.options);
    
    options.forEach(option => {
        if (option.value && classesList[option.value]) {
            classesList[option.value].name = option.text;
        }
    });
    
    // Generate HTML
    let html = '';
    const classFilter = document.getElementById('classFilterEnrollments').value;
    
    Object.keys(classesList).forEach(classId => {
        // Skip if we're filtering and this isn't the selected class
        if (classFilter && classFilter !== classId) {
            return;
        }
        
        const classData = classesList[classId];
        const className = classData.name || 'Unknown Class';
        
        html += `
            <div class="card mb-3 class-card" data-class-id="${classId}">
                <div class="card-header bg-primary bg-opacity-10">
                    <h5 class="mb-0">${className}</h5>
                </div>
                <div class="card-body">
                    <div class="row">
        `;
        
        classData.students.forEach(student => {
            const enrollDate = new Date(student.enrolled_at).toLocaleDateString();
            
            html += `
                <div class="col-md-4 mb-3">
                    <div class="card h-100">
                        <div class="card-body">
                            <h5 class="card-title">${student.name}</h5>
                            <p class="card-text text-muted small">
                                Enrolled: ${enrollDate}
                            </p>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += `
                    </div>
                </div>
                <div class="card-footer text-muted">
                    ${classData.students.length} student(s)
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html || '<div class="alert alert-info">No enrollments found for the selected class.</div>';
}

// Populate class dropdowns
function populateClassDropdowns(classes) {
    const dropdowns = [
        document.getElementById('classFilterEnrollments')
    ];
    
    dropdowns.forEach(dropdown => {
        if (!dropdown) return;
        
        // Keep the first option (All Classes)
        const firstOption = dropdown.options[0];
        dropdown.innerHTML = '';
        dropdown.appendChild(firstOption);
        
        // Add class options
        classes.forEach(classItem => {
            const option = document.createElement('option');
            option.value = classItem.id;
            option.textContent = classItem.name;
            dropdown.appendChild(option);
        });
    });
}

// Delete a class
async function deleteClass(classId) {
    if (!confirm('Are you sure you want to delete this class? All students in this class will be moved to the Default Class.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/classes/${classId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`Class deleted successfully. ${data.message}`);
            
            // Reload data
            loadClasses();
            loadEnrollments();
        } else {
            alert(`Error deleting class: ${data.error}`);
        }
    } catch (error) {
        console.error('Error deleting class:', error);
        alert('An error occurred while deleting the class. Please try again.');
    }
}

// Set up event listeners
function setupEventListeners() {
    // Class creation form
    const createClassForm = document.getElementById('createClassForm');
    if (createClassForm) {
        createClassForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const className = document.getElementById('className').value.trim();
            
            if (!className) {
                alert('Please enter a class name');
                return;
            }
            
            const formData = new FormData();
            formData.append('name', className);
            
            fetch('/api/classes', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Reset form
                    document.getElementById('className').value = '';
                    
                    // Show success message
                    const toast = new bootstrap.Toast(document.getElementById('classToast'));
                    toast.show();
                    
                    // Reload classes
                    loadClasses();
                } else {
                    alert('Error creating class: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error creating class:', error);
                alert('Error creating class. Please try again.');
            });
        });
    }
    
    // Class filter for enrollments
    const classFilter = document.getElementById('classFilterEnrollments');
    if (classFilter) {
        classFilter.addEventListener('change', function() {
            loadEnrollments();
        });
    }
    
    // Class deletion
    const classesContainer = document.getElementById('classesContainer');
    if (classesContainer) {
        classesContainer.addEventListener('click', function(e) {
            const deleteBtn = e.target.closest('.delete-class');
            if (deleteBtn) {
                const classId = deleteBtn.dataset.id;
                if (classId) {
                    deleteClass(classId);
                }
            }
        });
    }
}
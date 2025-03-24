document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    loadClasses();
    loadAnalytics();
    setupEventListeners();
});

// Load analytics data
function loadAnalytics() {
    fetch('/api/analytics')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayAnalytics(data.analytics);
            } else {
                console.error('Error loading analytics:', data.error);
                document.getElementById('analyticsStats').innerHTML = 
                    '<div class="alert alert-danger">Error loading analytics data.</div>';
            }
        })
        .catch(error => {
            console.error('Error fetching analytics:', error);
            document.getElementById('analyticsStats').innerHTML = 
                '<div class="alert alert-danger">Error connecting to server.</div>';
        });
}

// Display analytics in the UI
function displayAnalytics(analytics) {
    // Display summary stats
    const statsContainer = document.getElementById('analyticsStats');
    
    let statsHtml = `
        <div class="analytics-summary">
            <div class="analytics-stat">
                <div class="analytics-stat-value">${analytics.total_enrollments}</div>
                <div class="analytics-stat-label">Total Students</div>
            </div>
            <div class="analytics-stat">
                <div class="analytics-stat-value">${analytics.classes.length}</div>
                <div class="analytics-stat-label">Classes</div>
            </div>
            <div class="analytics-stat">
                <div class="analytics-stat-value">${analytics.attendance_by_date.length}</div>
                <div class="analytics-stat-label">Days Recorded</div>
            </div>
        </div>
    `;
    
    statsContainer.innerHTML = statsHtml;
    
    // Display class attendance
    displayClassAttendance(analytics.attendance_by_class);
}

// Display attendance by class
function displayClassAttendance(classData) {
    const container = document.getElementById('classAttendance');
    
    if (!classData || classData.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No attendance data available yet.</div>';
        return;
    }
    
    // Filter by selected class
    const selectedClass = document.getElementById('classFilter').value;
    let filteredData = classData;
    
    if (selectedClass) {
        filteredData = classData.filter(item => item.class_id === selectedClass);
    }
    
    if (filteredData.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No attendance data for the selected class.</div>';
        return;
    }
    
    let html = '';
    
    filteredData.forEach(classItem => {
        const attendanceCount = classItem.attendance.reduce((sum, item) => sum + item.count, 0);
        const latestDate = classItem.attendance.length > 0 ? 
            new Date(Math.max(...classItem.attendance.map(a => new Date(a.date)))).toLocaleDateString() : 
            'N/A';
        
        html += `
            <div class="card mb-3">
                <div class="card-header bg-primary bg-opacity-10">
                    <h5 class="mb-0">${classItem.class_name}</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4">
                            <div class="card mb-3">
                                <div class="card-body text-center">
                                    <h3>${attendanceCount}</h3>
                                    <p class="text-muted">Total Attendances</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="card mb-3">
                                <div class="card-body text-center">
                                    <h3>${classItem.attendance.length}</h3>
                                    <p class="text-muted">Days Recorded</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="card mb-3">
                                <div class="card-body text-center">
                                    <h3>${latestDate}</h3>
                                    <p class="text-muted">Latest Attendance</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <h6 class="mt-3">Attendance History</h6>
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Count</th>
                                </tr>
                            </thead>
                            <tbody>
        `;
        
        // Sort attendance by date (newest first)
        const sortedAttendance = [...classItem.attendance].sort((a, b) => 
            new Date(b.date) - new Date(a.date)
        );
        
        sortedAttendance.forEach(item => {
            html += `
                <tr>
                    <td>${item.date}</td>
                    <td>${item.count}</td>
                </tr>
            `;
        });
        
        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Load all classes
function loadClasses() {
    fetch('/api/classes')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                populateClassDropdowns(data.classes);
            } else {
                console.error('Error loading classes:', data.error);
            }
        })
        .catch(error => {
            console.error('Error fetching classes:', error);
        });
}

// Populate class dropdowns
function populateClassDropdowns(classes) {
    const dropdown = document.getElementById('classFilter');
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
}

// Set up event listeners
function setupEventListeners() {
    // Class filter
    const classFilter = document.getElementById('classFilter');
    if (classFilter) {
        classFilter.addEventListener('change', function() {
            loadAnalytics();
        });
    }
    
    // Export dropdown items
    const exportCsvLink = document.querySelector('a[href$="export_attendance_csv"]');
    const exportPdfLink = document.querySelector('a[href$="export_attendance_pdf"]');
    
    if (exportCsvLink) {
        exportCsvLink.addEventListener('click', function(e) {
            e.preventDefault();
            const classId = document.getElementById('classFilter').value;
            let url = this.getAttribute('href');
            
            if (classId) {
                url += `?class_id=${classId}`;
            }
            
            window.location.href = url;
        });
    }
    
    if (exportPdfLink) {
        exportPdfLink.addEventListener('click', function(e) {
            e.preventDefault();
            const classId = document.getElementById('classFilter').value;
            let url = this.getAttribute('href');
            
            if (classId) {
                url += `?class_id=${classId}`;
            }
            
            window.location.href = url;
        });
    }
}
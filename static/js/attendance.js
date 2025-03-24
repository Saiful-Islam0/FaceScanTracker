// Load attendance records when visiting the records page
document.addEventListener('DOMContentLoaded', () => {
    // Load classes for the class filter
    loadClasses();
    
    // Filter attendance records by date
    const dateFilter = document.getElementById('dateFilter');
    
    if (dateFilter) {
        // Set default date to today
        const today = new Date();
        const formattedDate = today.toISOString().split('T')[0];
        dateFilter.value = formattedDate;
        
        // Apply filter when date changes
        dateFilter.addEventListener('change', filterRecords);
    }
    
    // Apply filter when class changes
    const classFilter = document.getElementById('classFilter');
    if (classFilter) {
        classFilter.addEventListener('change', filterRecords);
    }
    
    // Set up export buttons
    setupExportButtons();
    
    // Initial filter
    filterRecords();
});

// Filter attendance records by date and class
function filterRecords() {
    const dateFilter = document.getElementById('dateFilter');
    const classFilter = document.getElementById('classFilter');
    const recordRows = document.querySelectorAll('.attendance-record');
    
    if (!recordRows) return;
    
    const selectedDate = dateFilter ? dateFilter.value : '';
    const selectedClass = classFilter ? classFilter.value : '';
    
    // Show/hide rows based on filters
    recordRows.forEach(row => {
        const recordDate = row.getAttribute('data-date');
        const recordClass = row.getAttribute('data-class-id');
        
        const dateMatch = !selectedDate || recordDate === selectedDate;
        const classMatch = !selectedClass || recordClass === selectedClass;
        
        if (dateMatch && classMatch) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
    
    // Show message if no records match the filter
    const visibleRows = document.querySelectorAll('.attendance-record:not([style*="display: none"])');
    const noRecordsMessage = document.getElementById('noRecordsMessage');
    
    if (noRecordsMessage) {
        if (visibleRows.length === 0) {
            noRecordsMessage.style.display = '';
        } else {
            noRecordsMessage.style.display = 'none';
        }
    }
    
    // Update export buttons with current filters
    updateExportUrls();
}

// Load classes for the dropdown
function loadClasses() {
    fetch('/api/classes')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                populateClassDropdown(data.classes);
            } else {
                console.error('Error loading classes:', data.error);
            }
        })
        .catch(error => {
            console.error('Error fetching classes:', error);
        });
}

// Populate class dropdown
function populateClassDropdown(classes) {
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

// Set up export buttons
function setupExportButtons() {
    const exportCsvBtn = document.getElementById('exportCsvBtn');
    const exportPdfBtn = document.getElementById('exportPdfBtn');
    
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const url = this.getAttribute('data-url');
            if (url) {
                window.location.href = url;
            }
        });
    }
    
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const url = this.getAttribute('data-url');
            if (url) {
                window.location.href = url;
            }
        });
    }
    
    // Initial update of export URLs
    updateExportUrls();
}

// Update export URLs based on current filters
function updateExportUrls() {
    const exportCsvBtn = document.getElementById('exportCsvBtn');
    const exportPdfBtn = document.getElementById('exportPdfBtn');
    const dateFilter = document.getElementById('dateFilter');
    const classFilter = document.getElementById('classFilter');
    
    if (!exportCsvBtn && !exportPdfBtn) return;
    
    const params = new URLSearchParams();
    
    if (dateFilter && dateFilter.value) {
        params.append('date', dateFilter.value);
    }
    
    if (classFilter && classFilter.value) {
        params.append('class_id', classFilter.value);
    }
    
    const queryString = params.toString() ? `?${params.toString()}` : '';
    
    if (exportCsvBtn) {
        const csvBaseUrl = exportCsvBtn.getAttribute('data-base-url') || '/export_attendance_csv';
        exportCsvBtn.setAttribute('data-url', `${csvBaseUrl}${queryString}`);
    }
    
    if (exportPdfBtn) {
        const pdfBaseUrl = exportPdfBtn.getAttribute('data-base-url') || '/export_attendance_pdf';
        exportPdfBtn.setAttribute('data-url', `${pdfBaseUrl}${queryString}`);
    }
}

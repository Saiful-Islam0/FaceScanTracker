// Load attendance records when visiting the records page
document.addEventListener('DOMContentLoaded', () => {
    // Filter attendance records by date
    const dateFilter = document.getElementById('dateFilter');
    
    if (dateFilter) {
        // Set default date to today
        const today = new Date();
        const formattedDate = today.toISOString().split('T')[0];
        dateFilter.value = formattedDate;
        
        // Apply filter when date changes
        dateFilter.addEventListener('change', filterRecordsByDate);
        
        // Initial filter
        filterRecordsByDate();
    }
});

// Filter attendance records by date
function filterRecordsByDate() {
    const dateFilter = document.getElementById('dateFilter');
    const recordRows = document.querySelectorAll('.attendance-record');
    
    if (!dateFilter || !recordRows) return;
    
    const selectedDate = dateFilter.value;
    
    // Show/hide rows based on date filter
    recordRows.forEach(row => {
        const recordDate = row.getAttribute('data-date');
        
        if (selectedDate === '' || recordDate === selectedDate) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
    
    // Show message if no records match the filter
    const visibleRows = document.querySelectorAll('.attendance-record[style=""]');
    const noRecordsMessage = document.getElementById('noRecordsMessage');
    
    if (noRecordsMessage) {
        if (visibleRows.length === 0) {
            noRecordsMessage.style.display = '';
        } else {
            noRecordsMessage.style.display = 'none';
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const availabilityForm = document.getElementById('availabilityForm');
    const saveButton = document.querySelector('button[type="submit"]');
    const resetButton = document.getElementById('resetFormBtn');
    const startTimeInput = document.getElementById('start_time');
    const endTimeInput = document.getElementById('end_time');
    const alertContainer = document.getElementById('alertContainer');

    // Set default time values
    if (!startTimeInput.value) startTimeInput.value = '09:00';
    if (!endTimeInput.value) endTimeInput.value = '17:00';

    // Function to show error message
    function showError(message) {
        alertContainer.innerHTML = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        // Scroll to error message
        alertContainer.scrollIntoView({ behavior: 'smooth' });
    }

    // Function to show success message
    function showSuccess(message) {
        alertContainer.innerHTML = `
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        // Scroll to success message
        alertContainer.scrollIntoView({ behavior: 'smooth' });
    }

    // Function to clear alerts
    function clearAlerts() {
        alertContainer.innerHTML = '';
    }

    // Function to update availability table
    function updateAvailabilityTable(workingHour) {
        const tableBody = document.getElementById('availabilityTableBody');
        const noAvailabilityRow = document.getElementById('noAvailabilityRow');
        
        if (noAvailabilityRow) {
            noAvailabilityRow.remove();
        }

        // Create new row
        const row = document.createElement('tr');
        const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        
        row.innerHTML = `
            <td>${days[parseInt(workingHour.day_of_week)]}</td>
            <td>${formatTime(workingHour.start_time)}</td>
            <td>${formatTime(workingHour.end_time)}</td>
            <td>${workingHour.appointment_duration} minutes</td>
            <td>
                <span class="badge bg-${workingHour.is_active ? 'success' : 'secondary'}">
                    ${workingHour.is_active ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td>
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-danger delete-slot" data-id="${workingHour.id}">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </td>
        `;

        tableBody.appendChild(row);
    }

    // Function to format time
    function formatTime(time) {
        return time;  // Return as is since it's already in HH:mm format
    }

    // Function to get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Handle form submission
    availabilityForm.addEventListener('submit', function(e) {
        e.preventDefault();
        clearAlerts();
        
        // Disable save button and show loading state
        saveButton.disabled = true;
        const originalButtonText = saveButton.innerHTML;
        saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        
        // Get form data
        const formData = new FormData(availabilityForm);
        formData.set('is_active', document.getElementById('is_active').checked);
        
        // Send request
        fetch('/working-hours/update/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showSuccess(data.message);
                updateAvailabilityTable(data.working_hour);
                resetForm();
            } else {
                showError(data.message || 'An error occurred while saving the availability');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('An error occurred while saving the availability');
        })
        .finally(() => {
            saveButton.disabled = false;
            saveButton.innerHTML = originalButtonText;
        });
    });

    // Handle form reset
    resetButton.addEventListener('click', function(e) {
        e.preventDefault();
        resetForm();
    });

    // Function to reset form
    function resetForm() {
        availabilityForm.reset();
        startTimeInput.value = '09:00';
        endTimeInput.value = '17:00';
        document.getElementById('is_active').checked = true;
        clearAlerts();
    }

    // Handle delete button clicks
    document.addEventListener('click', function(e) {
        const deleteButton = e.target.closest('.delete-slot');
        if (!deleteButton) return;

        e.preventDefault();
        const slotId = deleteButton.dataset.id;
        
        if (confirm('Are you sure you want to delete this availability slot?')) {
            // Disable the delete button
            deleteButton.disabled = true;
            const originalButtonText = deleteButton.innerHTML;
            deleteButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deleting...';

            const csrftoken = getCookie('csrftoken');
            fetch(`/working-hours/${slotId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    const row = deleteButton.closest('tr');
                    row.remove();
                    showSuccess('Availability slot deleted successfully');
                    
                    // Check if table is empty
                    const tableBody = document.getElementById('availabilityTableBody');
                    if (!tableBody.children.length) {
                        tableBody.innerHTML = `
                            <tr id="noAvailabilityRow">
                                <td colspan="6" class="text-center">No availability schedule set</td>
                            </tr>
                        `;
                    }
                } else {
                    throw new Error(data.message || 'Failed to delete availability slot');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showError(error.message || 'Failed to delete availability slot');
            })
            .finally(() => {
                // Re-enable the delete button
                deleteButton.disabled = false;
                deleteButton.innerHTML = originalButtonText;
            });
        }
    });
});
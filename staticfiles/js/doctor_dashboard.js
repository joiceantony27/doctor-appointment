document.addEventListener('DOMContentLoaded', function() {
    // Initialize date and time pickers
    initializeDateTimePickers();
    
    // Initialize charts
    initializeCharts();
    
    // Add event listeners
    setupEventListeners();
    
    // Load initial data
    loadDashboardData();
});

function initializeDateTimePickers() {
    flatpickr("#slot_date", {
        minDate: "today",
        dateFormat: "Y-m-d",
    });

    flatpickr("#start_time", {
        enableTime: true,
        noCalendar: true,
        dateFormat: "H:i",
        minTime: "08:00",
        maxTime: "20:00",
        time_24hr: true
    });

    flatpickr("#end_time", {
        enableTime: true,
        noCalendar: true,
        dateFormat: "H:i",
        minTime: "08:00",
        maxTime: "20:00",
        time_24hr: true
    });
}

function setupEventListeners() {
    // Time slot form submission
    document.getElementById('timeSlotForm').addEventListener('submit', handleTimeSlotSubmission);
    
    // Appointment actions
    document.querySelectorAll('.approve-appointment').forEach(btn => {
        btn.addEventListener('click', () => handleAppointmentAction(btn.dataset.id, 'approve'));
    });
    
    document.querySelectorAll('.reject-appointment').forEach(btn => {
        btn.addEventListener('click', () => handleAppointmentAction(btn.dataset.id, 'reject'));
    });
    
    // Profile form submission
    document.getElementById('profileForm')?.addEventListener('submit', handleProfileUpdate);
}

async function handleTimeSlotSubmission(e) {
    e.preventDefault();
    const form = e.target;
    const submitButton = form.querySelector('button[type="submit"]');
    
    try {
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border" role="status"></span> Saving...';
        
        const formData = new FormData(form);
        const response = await fetch('/doctor/save-time-slot/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Time slot saved successfully!', 'success');
            form.reset();
            loadTimeSlots();
        } else {
            showNotification(data.error || 'Failed to save time slot', 'error');
        }
    } catch (error) {
        showNotification('An error occurred while saving the time slot', 'error');
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = 'Save Time Slot';
    }
}

async function handleAppointmentAction(appointmentId, action) {
    try {
        const response = await fetch(`/doctor/appointment/${action}/${appointmentId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification(`Appointment ${action}ed successfully!`, 'success');
            loadDashboardData();
        } else {
            showNotification(data.error || `Failed to ${action} appointment`, 'error');
        }
    } catch (error) {
        showNotification(`An error occurred while ${action}ing the appointment`, 'error');
    }
}

async function handleProfileUpdate(e) {
    e.preventDefault();
    const form = e.target;
    const submitButton = form.querySelector('button[type="submit"]');
    
    try {
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border" role="status"></span> Updating...';
        
        const formData = new FormData(form);
        const response = await fetch('/doctor/update-profile/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Profile updated successfully!', 'success');
        } else {
            showNotification(data.error || 'Failed to update profile', 'error');
        }
    } catch (error) {
        showNotification('An error occurred while updating the profile', 'error');
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = 'Update Profile';
    }
}

async function loadDashboardData() {
    try {
        const response = await fetch('/doctor/dashboard-data/');
        const data = await response.json();
        
        updateStatistics(data.statistics);
        updateTimeSlots(data.time_slots);
        updateAppointmentsTable(data.appointments);
        updateChartData(data.chart_data);
    } catch (error) {
        showNotification('Failed to load dashboard data', 'error');
    }
}

function updateStatistics(statistics) {
    document.getElementById('total_appointments').textContent = statistics.total;
    document.getElementById('pending_appointments').textContent = statistics.pending;
    document.getElementById('approved_appointments').textContent = statistics.approved;
    document.getElementById('rejected_appointments').textContent = statistics.rejected;
}

function updateTimeSlots(slots) {
    const container = document.getElementById('timeSlotsContainer');
    container.innerHTML = slots.map(slot => `
        <div class="time-slot-card ${slot.is_booked ? 'booked' : ''}">
            <div class="slot-info">
                <span class="date">${formatDate(slot.date)}</span>
                <span class="time">${slot.start_time} - ${slot.end_time}</span>
            </div>
            <span class="status-badge ${slot.is_booked ? 'booked' : 'available'}">
                ${slot.is_booked ? 'Booked' : 'Available'}
            </span>
        </div>
    `).join('');
}

function updateAppointmentsTable(appointments) {
    const tbody = document.querySelector('#appointmentsTable tbody');
    tbody.innerHTML = appointments.map(apt => `
        <tr>
            <td>
                <div class="d-flex align-items-center">
                    <div class="avatar me-3">
                        ${apt.patient_photo ? 
                            `<img src="${apt.patient_photo}" alt="${apt.patient_name}">` :
                            `<span class="avatar-initial">${apt.patient_name[0]}</span>`
                        }
                    </div>
                    ${apt.patient_name}
                </div>
            </td>
            <td>${formatDate(apt.date)}</td>
            <td>${apt.time}</td>
            <td>
                <span class="badge bg-${getStatusColor(apt.status)}">${apt.status}</span>
            </td>
            <td>
                ${apt.status === 'pending' ? `
                    <button class="btn btn-sm btn-success approve-appointment" data-id="${apt.id}">
                        Approve
                    </button>
                    <button class="btn btn-sm btn-danger reject-appointment" data-id="${apt.id}">
                        Reject
                    </button>
                ` : ''}
            </td>
        </tr>
    `).join('');
}

function initializeCharts() {
    const appointmentsCtx = document.getElementById('appointmentsChart').getContext('2d');
    const timeDistributionCtx = document.getElementById('timeDistributionChart').getContext('2d');
    
    window.appointmentsChart = new Chart(appointmentsCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Appointments',
                data: [],
                borderColor: '#5e72e4',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
    
    window.timeDistributionChart = new Chart(timeDistributionCtx, {
        type: 'doughnut',
        data: {
            labels: ['Morning', 'Afternoon', 'Evening'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: ['#2dce89', '#fb6340', '#5e72e4']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

function updateChartData(data) {
    if (window.appointmentsChart) {
        window.appointmentsChart.data.labels = data.appointments.labels;
        window.appointmentsChart.data.datasets[0].data = data.appointments.values;
        window.appointmentsChart.update();
    }
    
    if (window.timeDistributionChart) {
        window.timeDistributionChart.data.datasets[0].data = [
            data.time_distribution.morning,
            data.time_distribution.afternoon,
            data.time_distribution.evening
        ];
        window.timeDistributionChart.update();
    }
}

function showNotification(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.querySelector('.notifications-container').appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function getStatusColor(status) {
    const colors = {
        'pending': 'warning',
        'approved': 'success',
        'rejected': 'danger'
    };
    return colors[status] || 'secondary';
}

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